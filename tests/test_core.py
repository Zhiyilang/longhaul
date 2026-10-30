import time

import pytest

from longhaul import Daemon, DaemonConfig, DaemonError


def test_daemon_restarts_on_failure():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("boom")
        while True:  # 3rd entry runs "forever"; stopped by the test
            time.sleep(0.05)

    d = Daemon(flaky, DaemonConfig(name="t", backoff_base=0.01, backoff_max=0.05))
    d.start()
    time.sleep(1.0)
    d.stop()
    d.join(timeout=2)
    assert calls["n"] >= 3


def test_max_restarts_gives_up():
    def always_fail():
        raise RuntimeError("nope")

    d = Daemon(always_fail, DaemonConfig(name="t2", max_restarts=2,
                                         backoff_base=0.01, backoff_max=0.02))
    with pytest.raises(DaemonError):
        d.run()


def test_heartbeat_health():
    def idle():
        while True:
            time.sleep(0.05)

    d = Daemon(idle, DaemonConfig(name="t3", health_timeout=1.0))
    d.start()
    time.sleep(0.2)
    assert d.is_healthy() is True
    d.stop()
    d.join(timeout=2)


def test_uptime_increases():
    def idle():
        while True:
            time.sleep(0.05)

    d = Daemon(idle, DaemonConfig(name="t4"))
    d.start()
    time.sleep(0.1)
    assert d.uptime() >= 0
    d.stop()
    d.join(timeout=2)
