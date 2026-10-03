"""python3 -m scripts.train_churn

Trains the B7 churn model on the agent_weekly table and saves it to artifacts/.
Run scripts.build_agent_weekly first.
"""
from app.core.config import get_settings
from app.db.pool import run_with_conn
from app.db.queries import fetch_df
from app.ml.agent_features import build_feature_table
from app.ml.agent_weekly import load_weekly_table
from app.ml.churn import (add_churn_labels, evaluate, explain_rows, save_churn_model,
                          split_by_time, train_churn_model)


async def load_inputs(db):
    weekly = await load_weekly_table(db)
    agents = await fetch_df(db, "SELECT agent_id, archetype, area_type FROM agents ORDER BY agent_id")
    return weekly, agents


def main():
    settings = get_settings()
    weekly, agents = run_with_conn(load_inputs)
    if len(weekly) == 0:
        raise SystemExit("agent_weekly is empty. Run: python3 -m scripts.build_agent_weekly")

    print("Building features and labels ...")
    features = build_feature_table(weekly, agents)
    labelled = add_churn_labels(features)
    train_rows, test_rows, train_last_week, test_first_week = split_by_time(labelled)
    print("  train weeks <=", train_last_week, "| test weeks >=", test_first_week)
    print("  train rows:", len(train_rows), "positives:", int(train_rows["churn_label"].sum()))
    print("  test rows :", len(test_rows), "positives:", int(test_rows["churn_label"].sum()))

    print("Training LightGBM ...")
    model = train_churn_model(train_rows)

    print("Evaluating on the held-out recent weeks ...")
    metrics = evaluate(model, test_rows)
    metrics["train_last_week_index"] = int(train_last_week)
    metrics["test_first_week_index"] = int(test_first_week)
    metrics["note"] = ("Synthetic data: churn episodes were injected by the generator, "
                       "so these numbers show the method works, not real-world accuracy.")
    for name, value in metrics.items():
        print("  ", name, "=", value)

    save_churn_model(model, metrics, settings.artifact_dir)
    print("Saved artifacts/churn_model.joblib and artifacts/churn_metrics.json")


if __name__ == "__main__":
    main()
