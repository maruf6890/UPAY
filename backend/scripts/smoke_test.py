"""python -m scripts.smoke_test  - hits every endpoint once."""
from fastapi.testclient import TestClient

from app.main import app

with TestClient(app) as c:
    def show(path, **kw):
        r = c.request(kw.pop("method", "GET"), path, **kw)
        print(f"{r.status_code}  {path}")
        assert r.status_code == 200, r.text[:400]
        return r.json()

    h = show("/health"); print("   ", h); assert h["database"] == "up";  show("/meta"); show("/metrics")
    risk = show("/risk?limit=5"); print("   risk summary:", risk["summary"])
    code = risk["agents"][0]["agent_code"]
    f = show(f"/agents/{code}/forecast"); print("   advice:", f["recommendation"]["advice"]["en"])
    print("   drivers:", [d["text_en"] for d in f["drivers"]])
    show("/rebalance?max_stops=5")
    a = show("/alerts"); print("   alerts:", len(a["alerts"]))
    if a["alerts"]:
        aid = a["alerts"][0]["alert_id"]
        show(f"/alerts/{aid}/review", method="POST", json={"decision": "confirmed", "reviewer": "demo", "note": "checked"})
        conf = show("/alerts?status=confirmed")["alerts"]
        assert any(x["alert_id"] == aid for x in conf), "review not persisted"
        print("   review persisted in PostgreSQL, confirmed alerts:", len(conf))
        print("   narrative:", show(f"/alerts/{aid}/narrative")["narrative"][:160])
    b = show("/brief"); print("   brief by:", b["brief"]["generated_by"], "|", b["brief"]["headline"])
print("ALL OK")
