"""Supervise many daemons: health watchdog, auto-restart of dead threads, alerts."""
from __future__ import annotations

import logging
import threading
import time
from typing import Iterable, List, Optional

from .core import Daemon

logger = logging.getLogger("longhaul")


class Supervisor:
    """Run and guard a fleet of Daemons from one place."""

    def __init__(self, daemons: Iterable[Daemon], alerts=None, watchdog_interval: float = 30.0):
        self.daemons: List[Daemon] = list(daemons)
        self.alerts = list(alerts or [])
        self.watchdog_interval = watchdog_interval
        self._stop = threading.Event()
        self._watchdog_thread: Optional[threading.Thread] = None

    # ---- alerts ----
    def add_alert(self, alert) -> None:
        self.alerts.append(alert)

    def alert(self, message: str) -> None:
        for a in self.alerts:
            try:
                a.send(message)
            except Exception:  # noqa: BLE001
                logger.exception("alert %r failed", a)

    # ---- lifecycle ----
    def start_all(self) -> None:
        for d in self.daemons:
            d.start()
        self._watchdog_thread = threading.Thread(target=self._watchdog, daemon=True)
        self._watchdog_thread.start()
        logger.info("supervisor started %d daemons", len(self.daemons))

    def _watchdog(self) -> None:
        while not self._stop.is_set():
            for i, d in enumerate(self.daemons):
                if not d.is_alive():
                    logger.warning("[%s] thread dead; restarting", d.config.name)
                    self.alert(f"[{d.config.name}] crashed & restarted (attempt {d.restarts + 1})")
                    self.daemons[i] = Daemon(d.target, d.config)
                    self.daemons[i].start()
                elif not d.is_healthy():
                    self.alert(f"[{d.config.name}] unhealthy (no heartbeat {d.config.health_timeout}s)")
            self._stop.wait(self.watchdog_interval)

    def stop_all(self) -> None:
        self._stop.set()
        for d in self.daemons:
            d.stop()

    def join_all(self, timeout: Optional[float] = None) -> None:
        for d in self.daemons:
            d.join(timeout)

    def status(self) -> dict:
        return {
            "daemons": [
                {
                    "name": d.config.name,
                    "alive": d.is_alive(),
                    "healthy": d.is_healthy(),
                    "restarts": d.restarts,
                    "uptime_s": round(d.uptime(), 1),
                    "last_error": d.last_error,
                }
                for d in self.daemons
            ]
        }
