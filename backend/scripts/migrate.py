"""Database migrations.
  python3 -m scripts.migrate status
  python3 -m scripts.migrate up [--to 2]
  python3 -m scripts.migrate down [--steps 1 | --to 1]
  python3 -m scripts.migrate new add_something
  python3 -m scripts.migrate reset --yes        (down everything, then up - dev only)
"""
import argparse
import asyncio
import sys

from app.db import migrate as m


async def main(a) -> None:
    if a.cmd == "status":
        for r in await m.status():
            when = r["applied_at"].strftime("%Y-%m-%d %H:%M") if r["applied_at"] else "-"
            print(f"  {r['version']:04d}  {r['name']:<28} {r['state']:<12} {when}")
    elif a.cmd == "up":
        await m.up(to=a.to)
    elif a.cmd == "down":
        await m.down(steps=a.steps, to=a.to)
    elif a.cmd == "new":
        print("created", m.new_migration(" ".join(a.name)))
    elif a.cmd == "reset":
        if not a.yes:
            sys.exit("reset drops ALL data. Re-run with --yes")
        await m.down(to=0)
        await m.up()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="PostgreSQL migrations")
    p.add_argument("cmd", choices=["status", "up", "down", "new", "reset"])
    p.add_argument("name", nargs="*")
    p.add_argument("--to", type=int)
    p.add_argument("--steps", type=int, default=1)
    p.add_argument("--yes", action="store_true")
    args = p.parse_args()
    try:
        asyncio.run(main(args))
    except m.MigrationError as e:
        sys.exit(f"migration error: {e}")
