"""python3 -m scripts.smoke_test_coverage_copilot
Calls every new C1 (coverage) and C5 (copilot) endpoint, follows EVERY drill-down link in the brief,
and re-checks that the older endpoints still work.
"""
from fastapi.testclient import TestClient

from app.main import app
from scripts._auth_helper import login


def call(client, path):
    response = client.get(path)
    print(response.status_code, path)
    if response.status_code != 200:
        print("   ERROR:", response.text[:300])
        raise SystemExit(1)
    return response.json()


with TestClient(app) as client:
    login(client)
    print("--- C1 coverage map")
    summary = call(client, "/coverage/summary")
    print("   hexagons by type:", summary["hexagons_by_gap_type"])
    gaps = call(client, "/coverage/gaps?limit=3")
    print("   biggest gap:", gaps["gaps"][0]["nearest_town"], gaps["gaps"][0]["gap_type"])
    capacity = call(client, "/coverage/gaps?gap_type=CAPACITY_GAP&limit=3")
    print("   capacity gaps:", len(capacity["gaps"]))
    geojson = call(client, "/coverage/map")
    print("   map features:", len(geojson["features"]), "| type:", geojson["type"])
    call(client, "/coverage/map?gap_type=NO_COVERAGE")
    call(client, "/coverage/cells/" + gaps["gaps"][0]["h3"])
    print("   unknown hexagon ->", client.get("/coverage/cells/not-a-cell").status_code)
    print("   date outside data ->", client.get("/coverage/summary?as_of=2020-01-01").status_code)

    print("--- C5 copilot brief")
    brief = call(client, "/copilot/brief")
    print("   written by:", brief["generated_by"], "| sections:", len(brief["sections"]), "| warnings:", brief["warnings"])
    print("   headline:", brief["headline"])

    links = []
    for section in brief["sections"]:
        for item in section["items"]:
            links.append(item["drill_down"])
        for list_link in section["drill_down_lists"]:
            links.append(list_link)
    print("   following", len(links), "drill-down links ...")
    broken = []
    for link in links:
        status = client.get(link).status_code
        if status != 200:
            broken.append((link, status))
    print("   broken drill-down links:", broken)
    if len(broken) > 0:
        raise SystemExit(1)

    print("--- C5 copilot ask")
    questions = ["Which agents will run out of cash?", "Who might leave soon?", "Where should we recruit agents?",
                 "Any suspicious alerts?", "Which agents are declining?", "Tell me about AG0235"]
    for question in questions:
        response = client.post("/copilot/ask", json={"question": question})
        data = response.json()
        print("  ", response.status_code, question, "->", data["tools_used"][0]["tool"])
        if response.status_code != 200:
            raise SystemExit(1)
    print("   question too short ->", client.post("/copilot/ask", json={"question": "hi"}).status_code)

    print("--- older endpoints still work")
    call(client, "/health")
    call(client, "/risk?limit=2")
    call(client, "/intel/performance/summary")
print("ALL OK")
