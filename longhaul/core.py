"""Core daemon engine: wrap any callable into a self-healing long-running job."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger("longhaul")


class DaemonError(Exception):
    """Raised when a daemon permanently gives up (exceeded max_restarts)."""


@dataclass
class DaemonConfig:
    name: str = "daemon"
    max_restarts: int = 0          # 0 = unlimited
    backoff_base: float = 2.0      # initial retry delay (seconds)
    backoff_max: float = 300.0     # cap on retry delay (seconds)
    backoff_factor: float = 2.0    # exponential growth between retries
    health_timeout: float = 0.0    # 0 = heartbeat check disabled
    stop_on_return: bool = False   # if True, a clean return ends the loop


class Daemon:
    """Supervise a single long-running target with auto-restart + health."""

    def __init__(self, target: Callable[[], None], config: Optional[DaemonConfig] = None):
        self.target = target
        self.config = config or DaemonConfig()
        self._stop = threading.Event()
        self._heartbeat = time.time()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self.restarts = 0
        self.last_error: Optional[str] = None
        self.started_at = time.time()

    # ---- public API ----
    def heartbeat(self) -> None:
        """Call this from inside your target to prove it is still alive."""
        with self._lock:
            self._heartbeat = time.time()

    def run(self) -> None:
        """Blocking supervisor loop. Returns only on stop() or permanent failure."""
        logger.info("[%s] starting", self.config.name)
        backoff = self.config.backoff_base
        while not self._stop.is_set():
            try:
                self.heartbeat()
                self.target()
                if self.config.stop_on_return:
                    logger.info("[%s] returned cleanly; stop_on_return set", self.config.name)
                    break
                self.heartbeat()
            except Exception as exc:  # noqa: BLE001 — we intentionally catch everything
                self.restarts += 1
                self.last_error = f"{type(exc).__name__}: {exc}"
                logger.warning("[%s] crashed (attempt %d): %s", self.config.name, self.restarts, exc)
                if self.config.max_restarts and self.restarts >= self.config.max_restarts:
                    logger.error("[%s] exceeded max_restarts=%d; giving up", self.config.name, self.config.max_restarts)
                    raise DaemonError(f"[{self.config.name}] exceeded max_restarts") from exc
                self._wait(backoff)
                backoff = min(backoff * self.config.backoff_factor, self.config.backoff_max)
        logger.info("[%s] stopped", self.config.name)

    def start(self) -> threading.Thread:
        """Launch the supervisor loop in a background daemon thread."""
        self._thread = threading.Thread(target=self.run, name=self.config.name, daemon=True)
        self._thread.start()
        return self._thread

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def stop(self) -> None:
        """Ask the loop to stop. Targets should be cooperative (see README)."""
        self._stop.set()

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def is_healthy(self) -> bool:
        if self.config.health_timeout <= 0:
            return True
        with self._lock:
            return (time.time() - self._heartbeat) <= self.config.health_timeout

    def uptime(self) -> float:
        return time.time() - self.started_at

    # ---- helpers ----
    def _wait(self, seconds: float) -> None:
        self._stop.wait(seconds)

    @classmethod
    def from_module(cls, spec: str, config: Optional[DaemonConfig] = None) -> "Daemon":
        """Resolve a target from 'module.path:callable_attr'."""
        if ":" not in spec:
            raise ValueError(f"bad spec {spec!r}; expected 'module:attr'")
        mod_path, attr = spec.split(":", 1)
        attr = attr.strip()
        module = __import__(mod_path, fromlist=[attr])
        obj = getattr(module, attr)
        if not callable(obj):
            raise TypeError(f"{spec} attribute is not callable")
        return cls(obj, config)
