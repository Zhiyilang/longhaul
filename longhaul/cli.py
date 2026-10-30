"""Command-line entry point for longhaul."""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time

from .core import Daemon, DaemonConfig
from .supervisor import Supervisor


def _build_config(ns) -> DaemonConfig:
    return DaemonConfig(
        name=ns.name or "job",
        max_restarts=ns.max_restarts,
        backoff_base=ns.backoff,
        health_timeout=ns.health,
    )


def cmd_run(ns) -> int:
    d = Daemon.from_module(ns.target, _build_config(ns))
    d.start()
    try:
        while d.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        logging.info("interrupt received; stopping %s", d.config.name)
        d.stop()
    d.join(timeout=5)
    return 0


def cmd_supervise(ns) -> int:
    with open(ns.config) as f:
        cfg = json.load(f)
    daemons = []
    for item in cfg.get("daemons", []):
        dc = DaemonConfig(
            name=item.get("name", "job"),
            max_restarts=item.get("max_restarts", 0),
            backoff_base=item.get("backoff", 2.0),
            health_timeout=item.get("health", 0.0),
        )
        daemons.append(Daemon.from_module(item["target"], dc))
    sup = Supervisor(daemons)
    sup.start_all()
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("interrupt received; stopping all daemons")
        sup.stop_all()
    sup.join_all(timeout=5)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="longhaul",
        description="Self-healing daemons for your bots, scrapers, and AI agents.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run a single job: module:callable")
    r.add_argument("target", help="e.g. mybot:main")
    r.add_argument("-n", "--name")
    r.add_argument("--max-restarts", type=int, default=0, help="0 = unlimited")
    r.add_argument("--backoff", type=float, default=2.0, help="initial retry delay (s)")
    r.add_argument("--health", type=float, default=0.0, help="heartbeat timeout (s); 0 disables")
    r.set_defaults(func=cmd_run)

    s = sub.add_parser("supervise", help="run many jobs from a JSON config")
    s.add_argument("config", help="path to config.json")
    s.set_defaults(func=cmd_supervise)

    ns = p.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return ns.func(ns)


if __name__ == "__main__":
    sys.exit(main())
