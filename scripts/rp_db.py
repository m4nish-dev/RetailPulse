"""
RetailPulse - configuration and MySQL connection helper (Phase 5).

Every script and notebook that talks to MySQL connects through this module, so
connection settings live in ONE place and no credential is ever written in code.

Configuration comes from environment variables. A local, git-ignored `.env`
file at the project root is loaded automatically (python-dotenv); variables
already set in the shell take precedence over the file.

    MYSQL_HOST       default 127.0.0.1
    MYSQL_PORT       default 3306
    MYSQL_DATABASE   required
    MYSQL_USER       required - the dedicated application account, never root
    MYSQL_PASSWORD   required

Copy `.env.example` to `.env` and fill in the values. See README "Setup".

Usage
-----
    from rp_db import get_connection
    conn = get_connection()            # read-only session by default
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
REQUIRED = ("MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD")
FORBIDDEN_USERS = {"root"}


class ConfigError(RuntimeError):
    """Raised when database configuration is missing or unsafe."""


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    database: str
    user: str
    password: str

    def __repr__(self) -> str:                      # never print the password
        return (f"DBConfig(host={self.host!r}, port={self.port}, "
                f"database={self.database!r}, user={self.user!r}, password='***')")


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:                              # documented dependency
        if ENV_FILE.exists():
            raise ConfigError("python-dotenv is not installed, so .env cannot be read. "
                              "Run: pip install -r requirements.txt")
        return
    load_dotenv(ENV_FILE, override=False)


def load_config() -> DBConfig:
    """Read and check the MySQL settings. Raises ConfigError with a clear message."""
    _load_dotenv()
    missing = [k for k in REQUIRED if not os.environ.get(k, "").strip()]
    if missing:
        hint = ("Create it from the template:  cp .env.example .env  then fill in the values."
                if not ENV_FILE.exists() else f"Add them to {ENV_FILE.name} or export them in the shell.")
        raise ConfigError(f"Missing required MySQL setting(s): {', '.join(missing)}. {hint}")
    user = os.environ["MYSQL_USER"].strip()
    if user.lower() in FORBIDDEN_USERS:
        raise ConfigError("MYSQL_USER is 'root'. Application scripts must use the dedicated "
                          "read-only RetailPulse account (see sql/10_app_user.sql).")
    port_raw = os.environ.get("MYSQL_PORT", "3306").strip() or "3306"
    try:
        port = int(port_raw)
    except ValueError:
        raise ConfigError(f"MYSQL_PORT must be a number, got {port_raw!r}") from None
    return DBConfig(host=os.environ.get("MYSQL_HOST", "127.0.0.1").strip() or "127.0.0.1",
                    port=port,
                    database=os.environ["MYSQL_DATABASE"].strip(),
                    user=user,
                    password=os.environ["MYSQL_PASSWORD"])


def get_connection(read_only: bool = True):
    """Open a MySQL connection using the configured application account.

    read_only=True (the default) also marks the session READ ONLY, so even a
    mistaken write is refused by the server, on top of the account's grants.
    Errors are re-raised without the password.
    """
    cfg = load_config()
    try:
        import mysql.connector
    except ImportError:
        raise ConfigError("mysql-connector-python is not installed. "
                          "Run: pip install -r requirements.txt") from None
    try:
        conn = mysql.connector.connect(host=cfg.host, port=cfg.port, user=cfg.user,
                                       password=cfg.password, database=cfg.database)
    except mysql.connector.Error as e:
        raise ConfigError(f"Cannot connect to MySQL as {cfg.user!r} at {cfg.host}:{cfg.port}/"
                          f"{cfg.database} (MySQL error {e.errno}: {e.msg}). Is the server running "
                          f"(brew services start mysql@8.4) and are the .env values correct?") from None
    if read_only:
        cur = conn.cursor()
        cur.execute("SET SESSION TRANSACTION READ ONLY")
        cur.close()
    return conn


if __name__ == "__main__":                           # quick self-test: python scripts/rp_db.py
    import sys
    try:
        c = get_connection()
        cur = c.cursor()
        cur.execute("SELECT CURRENT_USER(), DATABASE(), COUNT(*) FROM orders")
        u, db, n = cur.fetchone()
        print(f"OK  connected as {u} to {db}; orders = {n:,}  ({load_config()!r})")
        c.close()
    except ConfigError as e:
        sys.exit(f"CONFIG ERROR: {e}")
