"""python3 -m scripts.smoke_test_auth

Tests login, tokens, refresh, logout, lockout, disabled users, password change, the role dashboards,
and tries the usual attacks (tampered / expired / wrong-type / 'none' algorithm tokens).
Needs the demo accounts:  python3 -m scripts.create_user demo
"""
import base64
import json
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.auth import repository
from app.auth.security import hash_password
from app.core.config import get_settings
from app.db.pool import run_with_conn
from app.main import app

PASSWORD = "Pulse@2026"
TEST_USER = "tmp_smoke_user"
failures = []


def check(label, condition, detail=""):
    if condition:
        print("  ok   ", label)
    else:
        print("  FAIL ", label, detail)
        failures.append(label)


def login(client, username, password=PASSWORD):
    return client.post("/auth/login", json={"username": username, "password": password})


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def widget_keys(dashboard_json):
    keys = []
    for item in dashboard_json["widgets"]:
        keys.append(item["key"])
    return keys


async def create_test_user(db):
    existing = await repository.get_user_by_username(db, TEST_USER)
    if existing is not None:
        await db.execute("DELETE FROM users WHERE id = $1", existing["id"])
    await repository.create_user(db, TEST_USER, hash_password(PASSWORD), "Temporary Test User", "analyst", None, None)


async def delete_test_user(db):
    await db.execute("DELETE FROM users WHERE lower(username) = lower($1)", TEST_USER)


async def unlock_demo_accounts(db):
    await db.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL")


def main():
    settings = get_settings()
    run_with_conn(create_test_user)
    try:
        run_tests(settings)
    finally:
        run_with_conn(delete_test_user)

    print()
    if len(failures) > 0:
        print("FAILED:", failures)
        raise SystemExit(1)
    print("ALL OK")


def run_tests(settings):
    with TestClient(app) as client:
        print("1) public and protected routes")
        check("/health is public", client.get("/health").status_code == 200)
        check("/docs is reachable", client.get("/docs").status_code == 200)
        no_token = client.get("/risk")
        check("/risk without a token -> 401", no_token.status_code == 401)
        check("401 carries WWW-Authenticate", "bearer" in no_token.headers.get("www-authenticate", "").lower())
        for path in ["/agents", "/meta", "/metrics", "/rebalance", "/alerts", "/brief", "/dashboard", "/auth/me"]:
            check(f"{path} without a token -> 401", client.get(path).status_code == 401)
        scheme_found = "OAuth2PasswordBearer" in json.dumps(client.get("/openapi.json").json()["components"]["securitySchemes"])
        check("OpenAPI shows the Authorize button scheme", scheme_found)

        print("2) logging in")
        wrong = login(client, "manager", "wrong-password")
        unknown = login(client, "nobody_here", "whatever1")
        check("wrong password -> 401", wrong.status_code == 401)
        check("unknown user -> 401 with the SAME message (no user enumeration)",
              unknown.status_code == 401 and unknown.json()["detail"] == wrong.json()["detail"])
        good = login(client, "manager")
        check("correct login -> 200", good.status_code == 200)
        tokens = good.json()
        check("response has access + refresh token and expiry",
              "access_token" in tokens and "refresh_token" in tokens and tokens["expires_in"] == settings.access_token_minutes * 60)
        check("the password hash is never returned", "password" not in json.dumps(tokens).lower())
        access = tokens["access_token"]
        me = client.get("/auth/me", headers=auth_header(access))
        check("/auth/me works and shows the role", me.status_code == 200 and me.json()["role"] == "manager")
        check("/risk works with the token", client.get("/risk", params={"limit": 1}, headers=auth_header(access)).status_code == 200)
        form = client.post("/auth/token", data={"username": "manager", "password": PASSWORD})
        check("form login (the /docs Authorize button) works", form.status_code == 200 and "access_token" in form.json())
        check("username is case-insensitive", login(client, "MANAGER").status_code == 200)

        print("3) token attacks")
        header_part, payload_part, signature_part = access.split(".")
        padded = payload_part + "=" * (-len(payload_part) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded))
        claims["role"] = "analyst"
        forged_payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
        forged = ".".join([header_part, forged_payload, signature_part])
        check("tampered payload is rejected", client.get("/auth/me", headers=auth_header(forged)).status_code == 401)

        row = {"id": 1, "username": "manager", "role": "manager"}
        expired = jwt.encode({"sub": "1", "username": "manager", "role": "manager", "type": "access", "jti": "x",
                              "iat": datetime.now(timezone.utc) - timedelta(hours=3),
                              "exp": datetime.now(timezone.utc) - timedelta(hours=2)},
                             settings.jwt_secret, algorithm=settings.jwt_algorithm)
        expired_response = client.get("/auth/me", headers=auth_header(expired))
        check("expired token -> 401 'expired'", expired_response.status_code == 401 and "expired" in expired_response.json()["detail"].lower())

        none_token = jwt.encode({"sub": "1", "type": "access", "jti": "x", "iat": 1, "exp": 9999999999}, None, algorithm="none")
        check("'alg: none' token is rejected", client.get("/auth/me", headers=auth_header(none_token)).status_code == 401)
        wrong_secret = jwt.encode({"sub": "1", "type": "access", "jti": "x", "iat": 1, "exp": 9999999999}, "another-secret-another-secret-123456", algorithm="HS256")
        check("token signed with another secret is rejected", client.get("/auth/me", headers=auth_header(wrong_secret)).status_code == 401)
        check("garbage token is rejected", client.get("/auth/me", headers=auth_header("abc.def.ghi")).status_code == 401)
        check("refresh token cannot be used as an access token",
              client.get("/auth/me", headers=auth_header(tokens["refresh_token"])).status_code == 401)
        check("access token cannot be used as a refresh token",
              client.post("/auth/refresh", json={"refresh_token": access}).status_code == 401)

        print("4) refresh, rotation and logout")
        first = login(client, "manager").json()
        second = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
        check("refresh -> new token pair", second.status_code == 200 and second.json()["refresh_token"] != first["refresh_token"])
        reuse = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
        check("re-using an old refresh token -> 401", reuse.status_code == 401)
        after_reuse = client.post("/auth/refresh", json={"refresh_token": second.json()["refresh_token"]})
        check("...and it ends ALL sessions of that user (theft protection)", after_reuse.status_code == 401)
        third = login(client, "manager").json()
        check("logout -> 200", client.post("/auth/logout", json={"refresh_token": third["refresh_token"]}).status_code == 200)
        check("refresh after logout -> 401", client.post("/auth/refresh", json={"refresh_token": third["refresh_token"]}).status_code == 401)
        check("logout with garbage still answers 200 (nothing to leak)", client.post("/auth/logout", json={"refresh_token": "x" * 30}).status_code == 200)

        print("5) lockout after repeated wrong passwords")
        for attempt in range(settings.max_failed_logins):
            login(client, TEST_USER, "wrong-password")
        blocked = login(client, TEST_USER)
        check("account locked: even the CORRECT password -> 429", blocked.status_code == 429)
        run_with_conn(unlock_demo_accounts)
        check("after unlock the correct password works", login(client, TEST_USER).status_code == 200)

        print("6) disabled user is blocked immediately")
        temp_token = login(client, TEST_USER).json()["access_token"]
        check("token works before disabling", client.get("/auth/me", headers=auth_header(temp_token)).status_code == 200)
        run_with_conn(disable_test_user)
        check("same token fails right after disabling", client.get("/auth/me", headers=auth_header(temp_token)).status_code == 401)
        check("disabled user cannot log in", login(client, TEST_USER).status_code == 401)
        run_with_conn(enable_test_user)

        print("7) change password")
        token = login(client, TEST_USER).json()
        wrong_current = client.post("/auth/change-password", headers=auth_header(token["access_token"]),
                                    json={"current_password": "nope-nope", "new_password": "BrandNew#2026"})
        check("wrong current password -> 400", wrong_current.status_code == 400)
        too_short = client.post("/auth/change-password", headers=auth_header(token["access_token"]),
                                json={"current_password": PASSWORD, "new_password": "short"})
        check("password shorter than 8 -> 422", too_short.status_code == 422)
        too_long = client.post("/auth/change-password", headers=auth_header(token["access_token"]),
                               json={"current_password": PASSWORD, "new_password": "x" * 80})
        check("password longer than 72 -> 422", too_long.status_code == 422)
        changed = client.post("/auth/change-password", headers=auth_header(token["access_token"]),
                              json={"current_password": PASSWORD, "new_password": "BrandNew#2026"})
        check("change password -> 200", changed.status_code == 200)
        check("old password no longer works", login(client, TEST_USER, PASSWORD).status_code == 401)
        check("new password works", login(client, TEST_USER, "BrandNew#2026").status_code == 200)
        check("old refresh token was revoked", client.post("/auth/refresh", json={"refresh_token": token["refresh_token"]}).status_code == 401)

        print("8) the single dashboard, one view per role")
        manager_token = login(client, "manager").json()["access_token"]
        sylhet_token = login(client, "dso_sylhet").json()["access_token"]
        agent_token = login(client, "agent_ag0142").json()["access_token"]
        analyst_token = login(client, "analyst").json()["access_token"]

        manager_view = client.get("/dashboard", headers=auth_header(manager_token)).json()
        check("manager sees liquidity, route, retention ...", "liquidity_overview" in widget_keys(manager_view) and "delivery_route" in widget_keys(manager_view))
        print("       manager widgets:", widget_keys(manager_view), "| warnings:", manager_view["warnings"])
        check("manager scope = all districts", manager_view["scope"] == "all districts")

        sylhet_view = client.get("/dashboard", headers=auth_header(sylhet_token)).json()
        sylhet_overview = sylhet_view["widgets"][0]["data"]
        direct = client.get("/risk", params={"district": "Sylhet", "limit": 1}, headers=auth_header(manager_token)).json()["summary"]
        check("district manager is limited to Sylhet", sylhet_view["scope"] == "district Sylhet" and sylhet_overview["counts"] == direct,
              f"{sylhet_overview['counts']} vs {direct}")
        sylhet_agents = sylhet_view["widgets"][1]["data"]["rows"]
        check("...and the riskiest-agents table only has Sylhet agents", all_equal(sylhet_agents, "district", "Sylhet"))

        agent_view = client.get("/dashboard", headers=auth_header(agent_token)).json()
        print("       agent widgets:  ", widget_keys(agent_view), "| warnings:", agent_view["warnings"])
        status = agent_view["widgets"][0]["data"]
        check("agent sees ONLY their own agent", status["agent_code"] == "AG0142" and agent_view["scope"] == "agent AG0142")
        check("agent dashboard has no fleet-wide widgets", "riskiest_agents" not in widget_keys(agent_view) and "delivery_route" not in widget_keys(agent_view))
        check("agent sees advice in English and Bangla", len(status["advice_en"]) > 5 and len(status["advice_bn"]) > 5)
        check("agent chart has 16 hourly points", len(agent_view["widgets"][1]["data"]["points"]) == 16)

        analyst_view = client.get("/dashboard", headers=auth_header(analyst_token)).json()
        print("       analyst widgets:", widget_keys(analyst_view), "| warnings:", analyst_view["warnings"])
        check("analyst sees alerts and model quality", "pending_alerts" in widget_keys(analyst_view) and "model_quality" in widget_keys(analyst_view))
        check("analyst does not get the delivery route", "delivery_route" not in widget_keys(analyst_view))
        check("dashboard accepts as_of", client.get("/dashboard", params={"as_of": "2026-05-18 08:00"}, headers=auth_header(manager_token)).status_code == 200)
        check("bad as_of -> 400", client.get("/dashboard", params={"as_of": "banana"}, headers=auth_header(manager_token)).status_code == 400)

        print("9) alert review is tied to the logged-in user")
        alerts = client.get("/alerts", headers=auth_header(analyst_token)).json()["alerts"]
        if len(alerts) > 0:
            alert_id = alerts[0]["alert_id"]
            reviewed = client.post(f"/alerts/{alert_id}/review", headers=auth_header(analyst_token),
                                   json={"decision": "dismissed", "reviewer": "someone_else", "note": "smoke test"})
            check("review accepted", reviewed.status_code == 200)
            check("recorded reviewer = logged-in user, NOT the name typed in the body", reviewed.json()["reviewer"] == "analyst",
                  reviewed.text[:120])
        else:
            print("  (no pending alerts on the default date, skipped)")

        print("10) audit trail")
        audit = run_with_conn(read_audit)
        check("login_success is logged", audit.get("login_success", 0) > 0)
        check("login_failed is logged", audit.get("login_failed", 0) > 0)
        check("login_blocked (lockout) is logged", audit.get("login_blocked", 0) > 0)
        check("password_changed is logged", audit.get("password_changed", 0) > 0)
        check("refresh_token_reuse is logged", audit.get("refresh_token_reuse", 0) > 0)

        print("11) what is NOT restricted (by design: roles only shape the dashboard)")
        agent_can_see_fleet = client.get("/risk", params={"limit": 1}, headers=auth_header(agent_token)).status_code
        print(f"       an AGENT token can still call /risk -> {agent_can_see_fleet}  (this is the consequence of not locking routes by role)")

        print("12) the old smoke tests still need a login, health stays open")
        check("/health still open", client.get("/health").status_code == 200)


async def disable_test_user(db):
    await db.execute("UPDATE users SET is_active = FALSE WHERE lower(username) = lower($1)", TEST_USER)


async def enable_test_user(db):
    await db.execute("UPDATE users SET is_active = TRUE WHERE lower(username) = lower($1)", TEST_USER)


async def read_audit(db):
    rows = await db.fetch("SELECT action, count(*) AS total FROM audit_log GROUP BY action")
    counts = {}
    for record in rows:
        counts[record["action"]] = int(record["total"])
    return counts


def all_equal(rows, key, expected):
    for row in rows:
        if row[key] != expected:
            return False
    return len(rows) > 0


if __name__ == "__main__":
    main()
