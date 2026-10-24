"""Manage only a new loopback PostgreSQL cluster for Phase 4.2 verification.

Never reads DATABASE_URL, touches the workspace's managed database, or deletes data.
The database is disposable but retained until explicitly cleaned up by its owner.
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "data/local/phase42-e2e"
CLUSTER = CASE / "postgres-cluster"
SOCKET = CASE / "postgres-socket"
PORT = 55445
ROLE = "shiftos_phase42_e2e"
NAME = "shiftos_phase42_e2e"
URL = f"postgresql+psycopg://{ROLE}@127.0.0.1:{PORT}/{NAME}"


def command(args, label):
    env = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
    with (CASE / f"{label}.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(args, env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Isolated database operation failed: {label}; inspect local log")


def prepare():
    assert CLUSTER.resolve().is_relative_to((ROOT / "data/local").resolve())
    CASE.mkdir(parents=True, exist_ok=True, mode=0o700)
    for executable in ("initdb", "pg_ctl", "createdb"):
        if not shutil.which(executable):
            raise RuntimeError(f"PostgreSQL tool unavailable: {executable}")
    marker = CASE / "database-owner.json"
    identity = {"cluster": str(CLUSTER), "database": NAME, "port": PORT, "role": ROLE}
    if marker.exists():
        assert json.loads(marker.read_text()) == identity, "Unexpected database identity"
    else:
        assert not CLUSTER.exists(), "Existing unowned cluster must not be changed"
        with marker.open("x") as file:
            json.dump(identity, file)
    if not CLUSTER.exists():
        command(
            [
                "initdb",
                "-D",
                str(CLUSTER),
                "-U",
                ROLE,
                "-A",
                "trust",
                "--encoding=UTF8",
                "--no-locale",
            ],
            "initdb",
        )
    status = subprocess.run(["pg_ctl", "-D", str(CLUSTER), "status"], capture_output=True)
    if status.returncode:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", PORT))
        SOCKET.mkdir(exist_ok=True, mode=0o700)
        command(
            [
                "pg_ctl",
                "-D",
                str(CLUSTER),
                "-l",
                str(CASE / "postgres.log"),
                "-o",
                f"-h 127.0.0.1 -p {PORT} -k {SOCKET}",
                "-w",
                "start",
            ],
            "postgres_start",
        )
    import psycopg

    with psycopg.connect(host="127.0.0.1", port=PORT, user=ROLE, dbname="postgres") as conn:
        assert conn.execute("SHOW data_directory").fetchone()[0] == str(CLUSTER)
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (NAME,)).fetchone()
    if not exists:
        command(["createdb", "-h", "127.0.0.1", "-p", str(PORT), "-U", ROLE, NAME], "createdb")
    with psycopg.connect(host="127.0.0.1", port=PORT, user=ROLE, dbname=NAME) as conn:
        assert conn.execute("SELECT current_database()").fetchone()[0] == NAME
        version = conn.execute("SHOW server_version").fetchone()[0]
    return {
        "status": "isolated_postgresql_ready",
        "server_version": version,
        "loopback_only": True,
        "ambient_database_used": False,
        "model_requests": 0,
    }


def stop():
    identity = json.loads((CASE / "database-owner.json").read_text())
    assert identity["cluster"] == str(CLUSTER) and identity["database"] == NAME
    command(["pg_ctl", "-D", str(CLUSTER), "-m", "fast", "-w", "stop"], "postgres_stop")
    return {"status": "isolated_postgresql_stopped", "data_retained": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "stop"])
    action = parser.parse_args().action
    print(json.dumps(prepare() if action == "prepare" else stop(), indent=2))
