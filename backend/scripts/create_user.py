"""Manage login accounts.

  python3 -m scripts.create_user demo                      create 4 demo accounts (development only)
  python3 -m scripts.create_user add --username maria --role manager --full-name "Maria Akter" [--district Sylhet]
  python3 -m scripts.create_user add --username rahim --role agent --full-name "Rahim" --agent-code AG0142
  python3 -m scripts.create_user list
  python3 -m scripts.create_user set-password --username maria
  python3 -m scripts.create_user disable --username maria
  python3 -m scripts.create_user enable  --username maria
  python3 -m scripts.create_user unlock  --username maria

Roles: manager, agent, analyst. The password is asked for (hidden) unless you pass --password.
"""
import argparse
import getpass
import sys

from app.auth import repository
from app.auth.schemas import ROLES
from app.auth.security import hash_password
from app.core.config import get_settings
from app.db.pool import run_with_conn

DEMO_PASSWORD = "Pulse@2026"
DEMO_USERS = [
    {"username": "manager", "role": "manager", "full_name": "Area Manager (all districts)", "district": None, "agent_code": None},
    {"username": "dso_sylhet", "role": "manager", "full_name": "DSO Sylhet", "district": "Sylhet", "agent_code": None},
    {"username": "agent_ag0142", "role": "agent", "full_name": "Agent AG0142", "district": None, "agent_code": "AG0142"},
    {"username": "analyst", "role": "analyst", "full_name": "Risk Analyst", "district": None, "agent_code": None},
]


def ask_password(given):
    if given is not None:
        return given
    first = getpass.getpass("Password (min 8 characters): ")
    second = getpass.getpass("Repeat password: ")
    if first != second:
        raise SystemExit("Passwords do not match")
    return first


def check_password_rules(password):
    if len(password) < 8:
        raise SystemExit("Password must have at least 8 characters")
    if len(password.encode("utf-8")) > 72:
        raise SystemExit("Password is too long (maximum 72 bytes)")


async def find_canonical_district(db, district):
    """Returns the district name as stored in the agents table, or stops the script if it does not exist."""
    row = await db.fetchrow("SELECT district FROM agents WHERE lower(district) = lower($1) LIMIT 1", district)
    if row is None:
        raise SystemExit(f"District '{district}' not found. Check: GET /agents for the real district names")
    return row["district"]


async def check_agent_exists(db, agent_code):
    row = await db.fetchrow("SELECT agent_code FROM agents WHERE agent_code = $1", agent_code.upper())
    if row is None:
        raise SystemExit(f"Agent '{agent_code}' not found")
    return row["agent_code"]


async def add_user(db, username, password, full_name, role, district, agent_code):
    if role not in ROLES:
        raise SystemExit(f"Role must be one of {ROLES}")
    if role == "agent" and agent_code is None:
        raise SystemExit("An agent account needs --agent-code")
    if role != "agent":
        agent_code = None
    if role != "manager":
        district = None
    if district is not None:
        district = await find_canonical_district(db, district)
    if agent_code is not None:
        agent_code = await check_agent_exists(db, agent_code)

    existing = await repository.get_user_by_username(db, username)
    if existing is not None:
        raise SystemExit(f"Username '{username}' already exists")
    row = await repository.create_user(db, username, hash_password(password), full_name, role, district, agent_code)
    print(f"created user '{row['username']}' (id {row['id']}, role {row['role']})")


async def run(db, args):
    if args.command == "add":
        password = ask_password(args.password)
        check_password_rules(password)
        await add_user(db, args.username, password, args.full_name, args.role, args.district, args.agent_code)

    elif args.command == "demo":
        if get_settings().app_env == "production":
            raise SystemExit("Refusing to create demo accounts with a public password in production")
        for demo in DEMO_USERS:
            existing = await repository.get_user_by_username(db, demo["username"])
            if existing is not None:
                print(f"skipped '{demo['username']}' (already exists)")
                continue
            await add_user(db, demo["username"], DEMO_PASSWORD, demo["full_name"], demo["role"],
                           demo["district"], demo["agent_code"])
        print(f"\nDemo password for all four accounts: {DEMO_PASSWORD}   (development only, change it later)")

    elif args.command == "list":
        users = await repository.list_users(db)
        print(f"{'id':>3}  {'username':<16} {'role':<8} {'district':<12} {'agent':<8} {'active':<6} locked")
        for user in users:
            locked = ""
            if user["locked_until"] is not None:
                locked = "until " + user["locked_until"].strftime("%H:%M")
            print(f"{user['id']:>3}  {user['username']:<16} {user['role']:<8} {str(user['district'] or '-'):<12} "
                  f"{str(user['agent_code'] or '-'):<8} {str(user['is_active']):<6} {locked}")

    else:
        user = await repository.get_user_by_username(db, args.username)
        if user is None:
            raise SystemExit(f"User '{args.username}' not found")
        if args.command == "set-password":
            password = ask_password(args.password)
            check_password_rules(password)
            await repository.set_password(db, user["id"], hash_password(password))
            await repository.revoke_all_refresh_tokens(db, user["id"])
            print("password updated, all sessions ended")
        elif args.command == "disable":
            await repository.set_active(db, user["id"], False)
            await repository.revoke_all_refresh_tokens(db, user["id"])
            print("user disabled")
        elif args.command == "enable":
            await repository.set_active(db, user["id"], True)
            print("user enabled")
        elif args.command == "unlock":
            await repository.unlock(db, user["id"])
            print("user unlocked")


def main():
    parser = argparse.ArgumentParser(description="Manage login accounts")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="create one account")
    add.add_argument("--username", required=True)
    add.add_argument("--role", required=True, choices=ROLES)
    add.add_argument("--full-name", required=True)
    add.add_argument("--district")
    add.add_argument("--agent-code")
    add.add_argument("--password")

    commands.add_parser("demo", help="create four demo accounts (development only)")
    commands.add_parser("list", help="show all accounts")
    for name in ["set-password", "disable", "enable", "unlock"]:
        sub = commands.add_parser(name)
        sub.add_argument("--username", required=True)
        if name == "set-password":
            sub.add_argument("--password")

    args = parser.parse_args()

    async def work(db):
        await run(db, args)

    try:
        run_with_conn(work)
    except Exception as error:
        if "relation \"users\" does not exist" in str(error):
            sys.exit("The users table is missing. Run: python3 -m scripts.migrate up")
        raise


if __name__ == "__main__":
    main()
