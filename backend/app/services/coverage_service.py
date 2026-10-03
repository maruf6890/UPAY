"""C1 service: builds the coverage model for a date and serves the map and the gap list.

Supply  = each agent's handled volume over the 28 days before `as_of` (from the daily table, already in memory).
Unserved = demand lost to stockouts over the same window (one SQL query on the hourly table).
Results are cached per date, because the same page is requested many times.
"""
import statistics

import pandas as pd

from app.data.bd_towns import TOWNS
from app.ml import coverage

WINDOW_DAYS = 28
GAP_TYPES = ["CAPACITY_GAP", "NO_COVERAGE", "UNDER_SERVED", "OVER_SUPPLIED", "LOW_DEMAND", "BALANCED"]
PROBLEM_TYPES = ["CAPACITY_GAP", "NO_COVERAGE", "UNDER_SERVED"]

UNSERVED_SQL = """
SELECT agent_id,
       SUM(unserved_amt) AS unserved_bdt
FROM hourly
WHERE "timestamp" >= $1 AND "timestamp" < $2
GROUP BY agent_id
"""


class CoverageService:
    def __init__(self, pool, store, default_as_of, commission_rate):
        self.pool = pool
        self.store = store
        self.default_as_of = pd.Timestamp(default_as_of)
        self.commission_rate = commission_rate
        self._cache = {}

    # ------------------------------------------------------------ dates
    def resolve_window(self, as_of_text=None):
        if as_of_text is None:
            as_of = self.default_as_of
        else:
            as_of = pd.Timestamp(as_of_text)

        window_end = as_of.normalize()
        window_start = window_end - pd.Timedelta(days=WINDOW_DAYS)
        earliest = self.store.data_start.normalize()
        latest = self.store.data_end.normalize() + pd.Timedelta(days=1)
        if window_start < earliest or window_end > latest:
            first_ok = earliest + pd.Timedelta(days=WINDOW_DAYS)
            raise ValueError(f"as_of must be between {first_ok.date()} and {latest.date()}")
        return window_start, window_end

    # ------------------------------------------------------------ model
    async def get_model(self, as_of_text=None):
        window_start, window_end = self.resolve_window(as_of_text)
        cache_key = str(window_end.date())
        if cache_key in self._cache:
            return self._cache[cache_key]

        agent_rows = await self.collect_agent_rows(window_start, window_end)

        agent_cells = set()
        for agent in agent_rows:
            agent_cells.add(coverage.agent_cell_id(agent["lat"], agent["lon"]))

        cells = coverage.build_cells(TOWNS, agent_cells)
        cells = coverage.add_supply(cells, agent_rows)
        scale = coverage.calibrate_scale(cells)
        cells = coverage.classify_cells(cells, scale)

        volumes = []
        for agent in agent_rows:
            volumes.append(agent["monthly_volume_bdt"])
        typical_agent_volume = statistics.median(volumes)

        for cell in cells.values():
            cell["recommendation"] = coverage.recommend(cell, typical_agent_volume, self.commission_rate)

        model = {
            "window_start": window_start,
            "window_end": window_end,
            "scale_bdt_per_index": scale,
            "typical_agent_monthly_volume_bdt": typical_agent_volume,
            "cells": cells,
        }
        self._cache[cache_key] = model
        return model

    async def collect_agent_rows(self, window_start, window_end):
        daily = self.store.daily
        in_window = daily[(daily["date"] >= window_start) & (daily["date"] < window_end)]
        in_window = in_window.copy()
        in_window["volume"] = in_window["out_amt"] + in_window["in_amt"]
        volume_by_agent = in_window.groupby("agent_id")["volume"].sum()

        records = await self.pool.fetch(UNSERVED_SQL, window_start.to_pydatetime(), window_end.to_pydatetime())
        unserved_by_agent = {}
        for record in records:
            unserved_by_agent[int(record["agent_id"])] = float(record["unserved_bdt"])

        agent_rows = []
        agents = self.store.agents
        for row_number in range(len(agents)):
            agent = agents.iloc[row_number]
            agent_id = int(agent["agent_id"])
            if agent_id not in volume_by_agent.index:
                continue
            agent_rows.append({
                "agent_code": agent["agent_code"],
                "lat": float(agent["lat"]),
                "lon": float(agent["lon"]),
                "monthly_volume_bdt": float(volume_by_agent.loc[agent_id]),
                "unserved_bdt": unserved_by_agent.get(agent_id, 0.0),
            })
        return agent_rows

    # ------------------------------------------------------------ views
    def cell_properties(self, cell):
        return {
            "h3": cell["h3"],
            "gap_type": cell["gap_type"],
            "nearest_town": cell["nearest_town"],
            "demand_bdt": round(cell["demand_bdt"]),
            "supply_bdt": round(cell["supply_bdt"]),
            "coverage_ratio": round(cell["coverage_ratio"], 2),
            "untapped_bdt": round(cell["untapped_bdt"]),
            "unserved_bdt": round(cell["unserved_bdt"]),
            "agents_in_cell": len(cell["agents_in_cell"]),
            "agents_nearby": len(cell["agents_nearby"]),
            "agents_needed": cell["agents_needed"],
            "opportunity_commission_bdt": round(cell["opportunity_commission_bdt"]),
            "recommendation": cell["recommendation"],
        }

    async def map_geojson(self, as_of_text=None, gap_type=None):
        model = await self.get_model(as_of_text)
        features = []
        for cell in model["cells"].values():
            if gap_type is not None and cell["gap_type"] != gap_type:
                continue
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [coverage.cell_polygon(cell["h3"])]},
                "properties": self.cell_properties(cell),
            })
        return {"type": "FeatureCollection", "features": features}

    async def top_gaps(self, as_of_text=None, gap_type=None, limit=10):
        model = await self.get_model(as_of_text)
        candidates = []
        for cell in model["cells"].values():
            if cell["gap_type"] not in PROBLEM_TYPES:
                continue
            if gap_type is not None and cell["gap_type"] != gap_type:
                continue
            candidates.append(cell)

        # biggest opportunity first: lost demand for capacity gaps, untapped demand for coverage gaps
        def opportunity(cell):
            if cell["gap_type"] == "CAPACITY_GAP":
                return cell["unserved_bdt"]
            return cell["untapped_bdt"]

        candidates.sort(key=opportunity, reverse=True)
        gaps = []
        for cell in candidates[0:limit]:
            properties = self.cell_properties(cell)
            properties["lat"] = round(cell["lat"], 4)
            properties["lon"] = round(cell["lon"], 4)
            properties["opportunity_bdt_per_month"] = round(opportunity(cell))
            gaps.append(properties)
        return gaps

    async def summary(self, as_of_text=None):
        model = await self.get_model(as_of_text)
        counts = {}
        for gap_type in GAP_TYPES:
            counts[gap_type] = 0
        total_untapped = 0.0
        unserved_everywhere = 0.0
        unserved_in_capacity_gaps = 0.0
        covered_demand = 0.0
        total_demand = 0.0
        for cell in model["cells"].values():
            counts[cell["gap_type"]] = counts[cell["gap_type"]] + 1
            total_demand = total_demand + cell["demand_bdt"]
            covered_demand = covered_demand + min(cell["supply_bdt"], cell["demand_bdt"])
            if cell["gap_type"] in ("NO_COVERAGE", "UNDER_SERVED"):
                total_untapped = total_untapped + cell["untapped_bdt"]
            unserved_everywhere = unserved_everywhere + cell["unserved_bdt"]
            if cell["gap_type"] == "CAPACITY_GAP":
                unserved_in_capacity_gaps = unserved_in_capacity_gaps + cell["unserved_bdt"]

        share_covered = 0.0
        if total_demand > 0:
            share_covered = covered_demand / total_demand
        return {
            "window": f"{model['window_start'].date()} to {model['window_end'].date()} (28 days)",
            "hexagons": len(model["cells"]),
            "hexagons_by_gap_type": counts,
            "estimated_demand_covered_share": round(share_covered, 3),
            "untapped_monthly_volume_bdt": round(total_untapped),
            "monthly_volume_lost_to_stockouts_bdt": round(unserved_everywhere),
            "of_which_in_capacity_gap_hexagons_bdt": round(unserved_in_capacity_gaps),
            "typical_agent_monthly_volume_bdt": round(model["typical_agent_monthly_volume_bdt"]),
            "note": ("Demand is a synthetic potential surface scaled so that areas with agents are balanced on average. "
                     "Capacity gaps come from real (synthetic-simulation) stockout data."),
        }

    async def cell_detail(self, h3_id, as_of_text=None):
        model = await self.get_model(as_of_text)
        if h3_id not in model["cells"]:
            return None
        cell = model["cells"][h3_id]
        detail = self.cell_properties(cell)
        detail["lat"] = round(cell["lat"], 4)
        detail["lon"] = round(cell["lon"], 4)
        detail["agent_codes_in_cell"] = sorted(cell["agents_in_cell"])
        detail["agent_codes_nearby"] = sorted(set(cell["agents_nearby"]))
        return detail
