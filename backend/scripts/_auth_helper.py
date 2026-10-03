"""Used by the smoke tests: log in once and send the token with every request."""


def login(client, username="manager", password="Pulse@2026"):
    response = client.post("/auth/login", json={"username": username, "password": password})
    if response.status_code != 200:
        raise SystemExit(f"Login failed ({response.status_code}). Run: python3 -m scripts.create_user demo")
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return response.json()["user"]
