"""Local user administration (single organisation). Passwords are typed at a hidden prompt, never passed as arguments.

  .\\.venv\\Scripts\\python.exe -m cryptoshift.api.admin create-user <username> <viewer|analyst|approver>
  .\\.venv\\Scripts\\python.exe -m cryptoshift.api.admin list-users
  .\\.venv\\Scripts\\python.exe -m cryptoshift.api.admin export-openapi web/openapi.json
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from cryptoshift.api.config import Settings
from cryptoshift.api.db import make_engine, migrate, users
from cryptoshift.api.security import ROLES, hash_password


def create_user(settings: Settings, username: str, role: str, password: str) -> None:
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    if len(password) < 12:
        raise ValueError("password must be at least 12 characters")
    migrate(settings.db_path)
    eng = make_engine(settings.db_path)
    with eng.begin() as conn:
        if conn.execute(select(users.c.id).where(users.c.username == username)).first():
            raise ValueError("user exists")
        conn.execute(users.insert().values(username=username, password_hash=hash_password(password), role=role,
                                           created_at=datetime.now(UTC), disabled=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create-user")
    c.add_argument("username")
    c.add_argument("role", choices=ROLES)
    sub.add_parser("list-users")
    o = sub.add_parser("export-openapi")
    o.add_argument("out")
    a = ap.parse_args()
    st = Settings()
    if a.cmd == "create-user":
        pw = getpass.getpass("Password (min 12 chars): ")
        if pw != getpass.getpass("Repeat: "):
            print("passwords differ")
            return 1
        create_user(st, a.username, a.role, pw)
        print(f"created {a.username} ({a.role})")
    elif a.cmd == "list-users":
        migrate(st.db_path)
        with make_engine(st.db_path).connect() as conn:
            for u in conn.execute(select(users.c.username, users.c.role, users.c.disabled)):
                print(f"{u.username}\t{u.role}\t{'disabled' if u.disabled else 'active'}")
    else:
        from cryptoshift.api.main import create_app

        Path(a.out).write_text(json.dumps(create_app(st).openapi(), indent=2), encoding="utf-8")
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
