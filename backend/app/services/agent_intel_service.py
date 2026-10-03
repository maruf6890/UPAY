"""Serves B4 (performance intelligence) and B7 (churn prediction).

It is loaded ONCE at API start-up:
  * reads the agent_weekly table from PostgreSQL (small: about 18,000 rows),
  * builds the feature table in memory,
  * loads the trained churn model from artifacts/.
After that every request is a quick in-memory lookup, so the methods below are plain (non-async) functions.
"""
import pandas as pd

from app.db.queries import fetch_df
from app.ml import churn
from app.ml.agent_features import BASELINE_WEEKS, build_feature_table
from app.ml.agent_weekly import load_weekly_table
from app.ml.performance import score_performance


class AgentIntelService:
    def __init__(self, features, agents, churn_model, churn_metrics, default_as_of):
        # add the agent code and district, so every table we return can show them
        agent_names = agents[["agent_id", "agent_code", "district", "division"]]
        features = features.merge(agent_names, on="agent_id", how="left")
        self.features = churn.add_churn_labels(features)
        self.agents = agents
        self.churn_model = churn_model
        self.churn_metrics = churn_metrics
        self.default_as_of = default_as_of

        # week_index -> week start date
        self.week_dates = {}
        week_table = self.features[["week_index", "week_start"]].drop_duplicates()
        for row_number in range(len(week_table)):
            week_index = int(week_table.iloc[row_number]["week_index"])
            self.week_dates[week_index] = week_table.iloc[row_number]["week_start"]

        self._performance_cache = {}
        self._churn_cache = {}

    # ------------------------------------------------------------ start-up
    @classmethod
    async def create(cls, pool, agents, settings):
        weekly = await load_weekly_table(pool)
        if len(weekly) == 0:
            raise RuntimeError("agent_weekly is empty. Run: python3 -m scripts.build_agent_weekly")

        agent_info = agents[["agent_id", "agent_code", "district", "division", "archetype", "area_type"]]
        features = build_feature_table(weekly, agent_info)

        churn_model = None
        churn_metrics = {}
        try:
            churn_model, churn_metrics = churn.load_churn_model(settings.artifact_dir)
        except FileNotFoundError:
            print("WARNING: churn model not found, /intel/churn endpoints are disabled. Run: python3 -m scripts.train_churn")

        default_as_of = pd.Timestamp(settings.demo_as_of)
        return cls(features, agent_info, churn_model, churn_metrics, default_as_of)

    # ------------------------------------------------------------ weeks
    def resolve_week(self, as_of_text=None):
        """as_of -> the latest COMPLETE week that ended before that date."""
        if as_of_text is None:
            as_of = self.default_as_of
        else:
            as_of = pd.Timestamp(as_of_text)

        chosen_week = None
        for week_index in sorted(self.week_dates.keys()):
            week_end = self.week_dates[week_index] + pd.Timedelta(days=7)
            if week_end <= as_of.normalize():
                chosen_week = week_index
        if chosen_week is None:
            first_possible = self.week_dates[min(self.week_dates.keys())] + pd.Timedelta(days=7)
            raise ValueError(f"as_of is too early. Use a date on or after {first_possible.date()}")
        return chosen_week

    def available_weeks(self):
        weeks = []
        for week_index in sorted(self.week_dates.keys()):
            weeks.append({"week_index": week_index, "week_start": str(self.week_dates[week_index].date())})
        return {
            "first_week": weeks[0],
            "last_week": weeks[-1],
            "default_week": self.resolve_week(None),
            "baseline_weeks": BASELINE_WEEKS,
            "churn_model_loaded": self.churn_model is not None,
        }

    def has_agent(self, agent_id):
        return int(agent_id) in set(self.agents["agent_id"].tolist())

    def week_rows(self, week_index):
        return self.features[self.features["week_index"] == week_index].reset_index(drop=True)

    # ------------------------------------------------------------ B4: performance
    def performance_table(self, as_of_text=None, district=None, segment=None):
        week_index = self.resolve_week(as_of_text)
        if week_index not in self._performance_cache:
            rows = self.week_rows(week_index)
            scored = score_performance(rows)
            agent_names = self.agents[["agent_id", "agent_code", "district", "division"]]
            scored = scored.merge(agent_names, on="agent_id")
            self._performance_cache[week_index] = scored

        table = self._performance_cache[week_index]
        if district is not None:
            table = table[table["district"].str.lower() == district.lower()]
        if segment is not None:
            table = table[table["segment"] == segment]
        return week_index, table.sort_values("performance_score", ascending=False)

    def performance_summary(self, as_of_text=None, district=None):
        week_index, table = self.performance_table(as_of_text, district)
        segment_counts = table["segment"].value_counts().to_dict()
        cluster_counts = table["cluster_name"].value_counts().to_dict()

        flag_counts = {}
        for flag_list in table["flags"]:
            for flag in flag_list:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1

        lost_volume_at_service_gap_agents = 0.0
        for row_number in range(len(table)):
            row = table.iloc[row_number]
            if "SERVICE_GAP" in row["flags"]:
                lost_volume_at_service_gap_agents = lost_volume_at_service_gap_agents + float(row["lost_volume_4w_bdt"])

        return {
            "week_start": str(self.week_dates[week_index].date()),
            "agents": int(len(table)),
            "segments": segment_counts,
            "flags": flag_counts,
            "clusters": cluster_counts,
            "lost_volume_4w_at_service_gap_agents_bdt": lost_volume_at_service_gap_agents,
        }

    def performance_agent(self, agent_id, as_of_text=None):
        week_index, table = self.performance_table(as_of_text)
        row = table[table["agent_id"] == agent_id]
        if len(row) == 0:
            return None
        row = row.iloc[0]

        same_type = table[table["archetype"] == row["archetype"]]
        detail = row.to_dict()
        detail["week_start"] = str(self.week_dates[week_index].date())
        detail["peer_group_size"] = int(len(same_type))
        detail["peer_median_weekly_volume_bdt"] = float(same_type["avg_weekly_volume_bdt"].median())
        detail["weekly_series"] = self.weekly_series(agent_id, week_index)
        return detail

    # ------------------------------------------------------------ B7: churn
    def churn_table(self, as_of_text=None):
        if self.churn_model is None:
            raise RuntimeError("churn model not trained. Run: python3 -m scripts.train_churn")

        week_index = self.resolve_week(as_of_text)
        if week_index in self._churn_cache:
            return week_index, self._churn_cache[week_index]

        rows = self.week_rows(week_index)
        probabilities = churn.predict_churn(self.churn_model, rows)
        explanations = churn.explain_rows(self.churn_model, rows)

        records = []
        for row_number in range(len(rows)):
            row = rows.iloc[row_number]
            probability = float(probabilities[row_number])
            drivers = explanations[row_number]

            driver_names = []
            for driver in drivers:
                driver_names.append(driver["feature"])

            if bool(row["inactive"]):
                status = "ALREADY_INACTIVE"
                level = "INACTIVE"
                action = "Agent is already inactive. Win-back visit or deactivate."
            else:
                status = "ACTIVE"
                level = churn.risk_level(probability)
                action = churn.recommend_action(probability, driver_names, float(row["stockout_hours_4w"]))

            records.append({
                "agent_id": int(row["agent_id"]),
                "agent_code": row["agent_code"],
                "district": row["district"],
                "archetype": row["archetype"],
                "status": status,
                "churn_probability": round(probability, 3),
                "risk_level": level,
                "txn_ratio_4w": round(float(row["txn_ratio_4w"]), 2),
                "stockout_hours_4w": float(row["stockout_hours_4w"]),
                "drivers": drivers,
                "recommended_action": action,
            })

        table = pd.DataFrame(records)
        # agents that are still active come first (highest risk on top); agents that already left go last
        table["sort_group"] = 0
        table.loc[table["status"] == "ALREADY_INACTIVE", "sort_group"] = 1
        table = table.sort_values(["sort_group", "churn_probability"], ascending=[True, False])
        table = table.drop(columns=["sort_group"]).reset_index(drop=True)
        self._churn_cache[week_index] = table
        return week_index, table

    def churn_agent(self, agent_id, as_of_text=None):
        week_index, table = self.churn_table(as_of_text)
        row = table[table["agent_id"] == agent_id]
        if len(row) == 0:
            return None
        detail = row.iloc[0].to_dict()
        detail["week_start"] = str(self.week_dates[week_index].date())
        detail["horizon_weeks"] = churn.HORIZON_WEEKS
        detail["weekly_series"] = self.weekly_series(agent_id, week_index)
        return detail

    # ------------------------------------------------------------ shared helpers
    def weekly_series(self, agent_id, week_index, weeks=12):
        """Last `weeks` weeks of activity for charts."""
        rows = self.features[(self.features["agent_id"] == agent_id) & (self.features["week_index"] <= week_index)]
        rows = rows.sort_values("week_index").tail(weeks)
        series = []
        for row_number in range(len(rows)):
            row = rows.iloc[row_number]
            series.append({
                "week_start": str(row["week_start"].date()),
                "transactions": round(float(row["txn_count"]), 0),
                "volume_bdt": round(float(row["volume_bdt"]), 0),
                "baseline_transactions": round(float(row["baseline_txn"]), 0),
                "stockout_hours": int(row["stockout_hours"]),
            })
        return series

    def brief_facts(self, as_of_text=None):
        """Small summary the daily brief can include (optional integration)."""
        week_index, performance = self.performance_table(as_of_text)
        facts = {
            "week_start": str(self.week_dates[week_index].date()),
            "declining_agents": int((performance["segment"] == "DECLINING").sum()),
            "service_gap_agents": int((performance["segment"] == "SERVICE_GAP").sum()),
            "emerging_high_performers": int((performance["segment"] == "EMERGING_HIGH_PERFORMER").sum()),
        }
        if self.churn_model is not None:
            week_index, churn_rows = self.churn_table(as_of_text)
            facts["high_churn_risk_agents"] = int((churn_rows["risk_level"] == "HIGH").sum())
            top_rows = churn_rows[churn_rows["risk_level"] == "HIGH"].head(3)
            top_agents = []
            for row_number in range(len(top_rows)):
                top_agents.append(top_rows.iloc[row_number]["agent_code"])
            facts["top_churn_risk_agents"] = top_agents
        return facts
