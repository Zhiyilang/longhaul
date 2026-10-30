"""Example: a fragile bot that randomly fails — longhaul keeps it alive.

Run with:
    python -m longhaul.cli run -n demo-bot --backoff 1 examples.simple_bot:unstable_bot
or just:
    python examples/simple_bot.py
"""
import random
import time

from longhaul import Daemon, DaemonConfig


def unstable_bot():
    """Pretend work that occasionally crashes. longhaul restarts it."""
    while True:
        time.sleep(2)
        if random.random() < 0.2:
            raise RuntimeError("random bot failure (simulated)")
        print(f"[bot] tick {time.strftime('%H:%M:%S')} alive")


if __name__ == "__main__":
    d = Daemon(unstable_bot, DaemonConfig(name="demo-bot", backoff_base=1.0))
    d.start()
    try:
        while d.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nstopping...")
        d.stop()
    # daemon thread is killed on interpreter exit; no blocking join needed
