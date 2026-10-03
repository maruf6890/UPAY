"""python3 -m scripts.smoke_test_agent_intel   (hits every new /intel endpoint once)"""
from fastapi.testclient import TestClient

from app.main import app


def call(client, path):
    response = client.get(path)
    print(response.status_code, path)
    if response.status_code != 200:
        print("   ERROR:", response.text[:300])
        raise SystemExit(1)
    return response.json()


with TestClient(app) as client:
    weeks = call(client, "/intel/weeks")
    print("   default week:", weeks["last_week"], "| default index:", weeks["default_week"])

    summary = call(client, "/intel/performance/summary")
    print("   segments:", summary["segments"])
    print("   clusters:", summary["clusters"])

    agents = call(client, "/intel/performance/agents?limit=3")
    print("   top agent:", agents["agents"][0]["agent_code"], agents["agents"][0]["performance_score"])
    declining = call(client, "/intel/performance/agents?segment=DECLINING&limit=2")
    print("   declining agents shown:", len(declining["agents"]), "of", declining["total"])
    detail = call(client, "/intel/performance/agents/" + agents["agents"][0]["agent_code"])
    print("   detail keys:", sorted(detail.keys())[:6], "...")

    risk = call(client, "/intel/churn/risk?limit=3")
    print("   churn levels:", risk["level_counts"])
    top = risk["agents"][0]
    print("   riskiest:", top["agent_code"], top["churn_probability"], top["risk_level"])
    print("   why:")
    for driver in top["drivers"]:
        print("      -", driver["text_en"])
    print("   action:", top["recommended_action"])

    call(client, "/intel/churn/agents/" + top["agent_code"])
    call(client, "/intel/churn/metrics")

    overview = call(client, "/intel/agents/" + top["agent_code"] + "/overview")
    print("   overview priority:", overview["combined_priority"], "|", overview["combined_message"])
    print("   liquidity:", overview["liquidity"]["risk_level"], "| churn:", overview["churn"]["risk_level"])

    print("   bad agent code ->", client.get("/intel/churn/agents/AG9999").status_code)
    print("   bad date       ->", client.get("/intel/performance/summary?as_of=2020-01-01").status_code)

    # the old endpoints must still work
    call(client, "/health")
    call(client, "/risk?limit=2")
print("ALL OK")
