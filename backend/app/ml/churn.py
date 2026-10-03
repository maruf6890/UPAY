"""B7 - Agent churn prediction.

Question the model answers:
    "Will this agent go inactive within the next 4 weeks?"

Definitions (all from OBSERVED weekly activity, never from the injected labels):
    inactive week      : weekly transactions < 25% of the agent's own baseline
    churn event week   : first week that is inactive AND followed by another inactive week
    label for week t   : 1 if the churn event week is in t+1 ... t+4, otherwise 0
    training rows      : agents that are still active in week t and not yet churned

Model: LightGBM binary classifier. Explanations: LightGBM's built-in SHAP values
(pred_contrib=True), so no extra library is needed.
"""
import json

import joblib
import lightgbm as lgb
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from app.ml.agent_features import CHURN_FEATURES

HORIZON_WEEKS = 4
INACTIVE_FRACTION = 0.25
TEST_WEEKS = 12

HIGH_THRESHOLD = 0.50
MEDIUM_THRESHOLD = 0.20

LGB_PARAMS = {
    "objective": "binary",
    "learning_rate": 0.05,
    "num_leaves": 15,
    "min_data_in_leaf": 20,
    "feature_fraction": 0.9,
    "lambda_l2": 1.0,
    "verbose": -1,
    "seed": 42,
}
NUMBER_OF_TREES = 200


# ---------------------------------------------------------------- labels
def find_churn_event_week(week_indexes, inactive_flags):
    """First week that is inactive and followed by another inactive week. None if it never happens."""
    last_position = len(week_indexes) - 1
    position = 0
    while position < last_position:
        if inactive_flags[position] and inactive_flags[position + 1]:
            return week_indexes[position]
        position = position + 1
    return None


def add_churn_labels(features):
    """Adds: inactive, churn_label, label_known, trainable."""
    features = features.copy()
    features["inactive"] = features["txn_count"] < INACTIVE_FRACTION * features["baseline_txn"]
    features["churn_label"] = 0
    features["label_known"] = False
    features["trainable"] = False

    last_week_index = int(features["week_index"].max())

    for agent_id, group in features.groupby("agent_id"):
        group = group.sort_values("week_index")
        week_indexes = list(group["week_index"])
        inactive_flags = list(group["inactive"])
        event_week = find_churn_event_week(week_indexes, inactive_flags)

        labels = []
        known_flags = []
        trainable_flags = []
        for position in range(len(week_indexes)):
            week_index = week_indexes[position]
            is_inactive = inactive_flags[position]

            label = 0
            if event_week is not None:
                if week_index < event_week and event_week <= week_index + HORIZON_WEEKS:
                    label = 1

            # the label is only known when the whole 4-week window exists in the data
            label_is_known = week_index + HORIZON_WEEKS <= last_week_index

            # only agents that are still active and have not churned yet are "at risk"
            has_churned_already = False
            if event_week is not None:
                if week_index >= event_week:
                    has_churned_already = True
            is_trainable = label_is_known and (not is_inactive) and (not has_churned_already)

            labels.append(label)
            known_flags.append(label_is_known)
            trainable_flags.append(is_trainable)

        features.loc[group.index, "churn_label"] = labels
        features.loc[group.index, "label_known"] = known_flags
        features.loc[group.index, "trainable"] = trainable_flags

    return features


def split_by_time(labelled):
    """Train on the past, test on the most recent weeks.
    A gap of HORIZON_WEEKS keeps training labels from looking into the test period."""
    last_label_week = int(labelled.loc[labelled["label_known"], "week_index"].max())
    test_first_week = last_label_week - TEST_WEEKS + 1
    train_last_week = test_first_week - HORIZON_WEEKS - 1

    trainable = labelled[labelled["trainable"]]
    train_rows = trainable[trainable["week_index"] <= train_last_week]
    test_rows = trainable[trainable["week_index"] >= test_first_week]
    return train_rows, test_rows, train_last_week, test_first_week


# ---------------------------------------------------------------- model
def train_churn_model(train_rows):
    train_data = lgb.Dataset(train_rows[CHURN_FEATURES], label=train_rows["churn_label"])
    model = lgb.train(LGB_PARAMS, train_data, num_boost_round=NUMBER_OF_TREES)
    return model


def predict_churn(model, rows):
    return model.predict(rows[CHURN_FEATURES])


def risk_level(probability):
    if probability >= HIGH_THRESHOLD:
        return "HIGH"
    if probability >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------- explanations
def describe_driver(feature_name, value):
    """Turns one feature value into a plain sentence (English and Bangla)."""
    if feature_name == "txn_ratio_1w_vs_peers":
        percent = round(abs(value - 1.0) * 100)
        if value < 1.0:
            return (f"Last week's transactions are {percent}% below similar agents (holiday-adjusted)",
                    f"গত সপ্তাহের লেনদেন সমপর্যায়ের এজেন্টদের তুলনায় {percent}% কম (ছুটির প্রভাব বাদ দিয়ে)")
        return (f"Last week's transactions are {percent}% above similar agents (holiday-adjusted)",
                f"গত সপ্তাহের লেনদেন সমপর্যায়ের এজেন্টদের তুলনায় {percent}% বেশি (ছুটির প্রভাব বাদ দিয়ে)")

    if feature_name == "txn_ratio_4w_vs_peers":
        percent = round(abs(value - 1.0) * 100)
        if value < 1.0:
            return (f"The 4-week average is {percent}% below similar agents",
                    f"গত ৪ সপ্তাহের গড় লেনদেন সমপর্যায়ের এজেন্টদের চেয়ে {percent}% কম")
        return (f"The 4-week average is {percent}% above similar agents",
                f"গত ৪ সপ্তাহের গড় লেনদেন সমপর্যায়ের এজেন্টদের চেয়ে {percent}% বেশি")

    if feature_name == "txn_trend_vs_peers":
        percent = round(abs(value) * 100)
        if value < 0:
            return (f"Activity is falling {percent}% of normal faster than similar agents over the last 2 weeks",
                    f"গত ২ সপ্তাহে সমপর্যায়ের এজেন্টদের চেয়ে লেনদেন {percent}% দ্রুত কমছে")
        return (f"Activity is rising {percent}% of normal faster than similar agents over the last 2 weeks",
                f"গত ২ সপ্তাহে সমপর্যায়ের এজেন্টদের চেয়ে লেনদেন {percent}% দ্রুত বাড়ছে")

    if feature_name == "volume_ratio_4w":
        percent = round(abs(value - 1.0) * 100)
        if value < 1.0:
            return (f"Transaction value is {percent}% below normal",
                    f"লেনদেনের মোট টাকা স্বাভাবিকের চেয়ে {percent}% কম")
        return (f"Transaction value is {percent}% above normal",
                f"লেনদেনের মোট টাকা স্বাভাবিকের চেয়ে {percent}% বেশি")

    if feature_name == "ticket_ratio_4w":
        percent = round(abs(value - 1.0) * 100)
        return (f"Average ticket size changed by {percent}% versus normal",
                f"গড় লেনদেনের পরিমাণ স্বাভাবিকের তুলনায় {percent}% বদলেছে")

    if feature_name == "active_days_1w":
        days = round(value)
        return (f"Only active on {days} of 7 days last week",
                f"গত সপ্তাহে ৭ দিনের মধ্যে মাত্র {days} দিন সক্রিয় ছিল")

    if feature_name == "active_days_4w":
        days = round(value, 1)
        return (f"Active on {days} days per week on average over the last 4 weeks",
                f"গত ৪ সপ্তাহে গড়ে সপ্তাহে {days} দিন সক্রিয়")

    if feature_name == "stockout_hours_4w":
        hours = round(value)
        return (f"Ran out of cash or e-float for {hours} hours in the last 4 weeks",
                f"গত ৪ সপ্তাহে {hours} ঘণ্টা ক্যাশ বা ই-ফ্লোট শেষ ছিল")

    if feature_name == "stockout_rate_4w":
        percent = round(value * 100, 1)
        return (f"{percent}% of open hours had a stockout in the last 4 weeks",
                f"গত ৪ সপ্তাহে খোলা সময়ের {percent}% ক্যাশ/ফ্লোট সংকট ছিল")

    if feature_name == "txn_volatility_4w":
        return ("Weekly activity has been unstable lately",
                "সাম্প্রতিক সপ্তাহগুলোতে লেনদেন অস্থিতিশীল")

    return ("Agent type and area", "এজেন্টের ধরন ও এলাকা")


def explain_rows(model, rows, top_n=3):
    """For each row: the top_n features that PUSH THE CHURN RISK UP (positive SHAP values)."""
    contributions = model.predict(rows[CHURN_FEATURES], pred_contrib=True)
    feature_count = len(CHURN_FEATURES)

    explanations = []
    for row_number in range(len(rows)):
        pairs = []
        for feature_number in range(feature_count):
            contribution = float(contributions[row_number][feature_number])
            pairs.append((contribution, CHURN_FEATURES[feature_number]))

        pairs.sort(reverse=True)         # biggest contribution first

        drivers = []
        for contribution, feature_name in pairs[0:top_n]:
            if contribution <= 0:
                continue
            value = float(rows.iloc[row_number][feature_name])
            text_en, text_bn = describe_driver(feature_name, value)
            drivers.append({
                "feature": feature_name,
                "shap_value": round(contribution, 3),
                "value": round(value, 3),
                "text_en": text_en,
                "text_bn": text_bn,
            })
        explanations.append(drivers)
    return explanations


# ---------------------------------------------------------------- business rule (kept separate from the model)
def recommend_action(probability, driver_names, stockout_hours_4w):
    if probability < MEDIUM_THRESHOLD:
        return "No action needed. Keep monitoring."

    service_problem = False
    if "stockout_hours_4w" in driver_names or "stockout_rate_4w" in driver_names:
        service_problem = True
    if stockout_hours_4w >= 8:
        service_problem = True

    if service_problem:
        return ("Fix service first: give this agent priority for cash / e-float top-ups, "
                "then follow up with a call. Running out of money is likely driving the drop.")

    if probability >= HIGH_THRESHOLD:
        return "Retention visit this week: ask what changed, check for competing agents, consider a short-term incentive."
    return "Retention call this week and keep watching the weekly trend."


# ---------------------------------------------------------------- evaluation
def precision_at_k_per_week(test_rows, score_column, k=10):
    """For every test week take the k highest scores and measure how many really churned. Average over weeks."""
    precisions = []
    for week_index, week_rows in test_rows.groupby("week_index"):
        if week_rows["churn_label"].sum() == 0:
            continue
        top_rows = week_rows.sort_values(score_column, ascending=False).head(k)
        precisions.append(float(top_rows["churn_label"].mean()))
    if len(precisions) == 0:
        return None
    return float(np.mean(precisions))


def evaluate(model, test_rows):
    test_rows = test_rows.copy()
    test_rows["model_score"] = predict_churn(model, test_rows)
    # simple rule everybody could build: "the sharper the recent drop, the higher the risk"
    test_rows["rule_score"] = -test_rows["txn_trend_4w"]   # raw trend, NOT holiday-adjusted

    labels = test_rows["churn_label"]
    metrics = {
        "test_rows": int(len(test_rows)),
        "test_positive_rate": float(labels.mean()),
        "auc_model": float(roc_auc_score(labels, test_rows["model_score"])),
        "auc_simple_rule": float(roc_auc_score(labels, test_rows["rule_score"])),
        "average_precision_model": float(average_precision_score(labels, test_rows["model_score"])),
        "average_precision_simple_rule": float(average_precision_score(labels, test_rows["rule_score"])),
        "precision_at_10_per_week_model": precision_at_k_per_week(test_rows, "model_score", 10),
        "precision_at_10_per_week_simple_rule": precision_at_k_per_week(test_rows, "rule_score", 10),
    }

    flagged = test_rows[test_rows["model_score"] >= MEDIUM_THRESHOLD]
    if len(flagged) > 0:
        metrics["precision_at_medium_threshold"] = float(flagged["churn_label"].mean())
    else:
        metrics["precision_at_medium_threshold"] = None
    total_positive = int(labels.sum())
    if total_positive > 0:
        metrics["recall_at_medium_threshold"] = float(flagged["churn_label"].sum() / total_positive)
    else:
        metrics["recall_at_medium_threshold"] = None
    return metrics


# ---------------------------------------------------------------- save / load
def save_churn_model(model, metrics, artifact_dir):
    joblib.dump({"model_text": model.model_to_string()}, artifact_dir / "churn_model.joblib")
    (artifact_dir / "churn_metrics.json").write_text(json.dumps(metrics, indent=2))


def load_churn_model(artifact_dir):
    """Returns (model, metrics). Raises FileNotFoundError when the model has not been trained yet."""
    model_path = artifact_dir / "churn_model.joblib"
    if not model_path.exists():
        raise FileNotFoundError("churn model not found. Run: python3 -m scripts.train_churn")
    saved = joblib.load(model_path)
    model = lgb.Booster(model_str=saved["model_text"])

    metrics = {}
    metrics_path = artifact_dir / "churn_metrics.json"
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text())
    return model, metrics
