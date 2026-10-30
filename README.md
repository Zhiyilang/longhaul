# longhaul

[![PyPI](https://img.shields.io/pypi/v/longhaul.svg)](https://pypi.org/project/longhaul)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org)
[![CI](https://github.com/YOUR_USERNAME/longhaul/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/longhaul/actions)

**Self-healing daemons for your bots, scrapers, and AI agents — run them 24/7 without babysitting.**

`longhaul` wraps any Python callable into a supervised long-running job that:

- 🔁 **Auto-restarts** on crash with exponential backoff (and gives up cleanly after N tries).
- 💓 **Health-checks** via heartbeats — detects silent hangs, not just crashes.
- 📣 **Alerts** you through Telegram / Discord / email / any webhook when something is *actually* wrong.
- 🐣 **Zero dependencies** — pure standard library. Drop it in anywhere.
- 🧰 Ships a **CLI** (`longhaul run`, `longhaul supervise`) so you don't even have to write boilerplate.

> Built from hard-won lessons running automation 24/7: the only thing worse than a bot that
> crashes is a bot that *silently* hangs and burns money while you sleep.

## Install

```bash
pip install longhaul
```

Or, with zero install, just copy `longhaul/` into your project.

## Quickstart (3 lines)

```python
from longhaul import Daemon, DaemonConfig

def my_bot():
    while True:
        do_work()          # your bot / scraper / agent main loop
        Daemon.heartbeat() # optional: prove you're alive

Daemon(my_bot, DaemonConfig(name="my-bot", backoff_base=2)).start()
```

That's it. `my_bot` will be restarted automatically if it throws, and the process
keeps running until you call `.stop()`.

## CLI

Run a single job straight from a module:

```bash
# module:callable  ->  mybots.price_watch:run
longhaul run -n price-bot --backoff 2 --health 60 mybots.price_watch:run
```

Or supervise a whole fleet from JSON:

```bash
longhaul supervise config.json
```

```json
{
  "daemons": [
    { "name": "price-bot",  "target": "mybots.price_watch:run", "max_restarts": 0,  "backoff": 2, "health": 60 },
    { "name": "sync-agent", "target": "mybots.sync:run",        "max_restarts": 10, "backoff": 5, "health": 120 }
  ]
}
```

See [`examples/`](examples) for runnable demos.

## Alerts

Wire up a notifier so you hear about real problems instead of discovering them at 9am:

```python
from longhaul import Supervisor, Daemon, DaemonConfig
from longhaul import TelegramAlert, DiscordAlert, EmailAlert, WebhookAlert

alerts = [
    TelegramAlert(token="...", chat_id="..."),
    DiscordAlert(webhook_url="https://discord.com/api/webhooks/..."),
    WebhookAlert(url="https://hooks.slack.com/services/..."),   # Slack-compatible
    # EmailAlert(host="smtp.gmail.com", port=587, user="you", password="app-pass", to_addr="you@x.com"),
]

sup = Supervisor([Daemon(my_bot, DaemonConfig(name="bot"))], alerts=alerts)
sup.start_all()
```

The built-in watchdog pings each daemon every 30s and fires an alert when one dies
or stops sending heartbeats.

## Configuration

| `DaemonConfig` field | default | meaning |
|---|---|---|
| `name` | `"daemon"` | identifier used in logs/alerts |
| `max_restarts` | `0` | max retries before giving up (`0` = unlimited) |
| `backoff_base` | `2.0` | initial delay between retries (seconds) |
| `backoff_max` | `300.0` | cap on the retry delay |
| `backoff_factor` | `2.0` | exponential growth of the delay |
| `health_timeout` | `0.0` | heartbeat timeout; `0` disables the hang check |
| `stop_on_return` | `False` | if `True`, a clean return ends the loop |

## A note on cooperative shutdown

`longhaul` restarts threads on *exceptions* automatically. For *clean* stops
(Ctrl-C, `.stop()`), your target should be cooperative — either return periodically
or check the stop signal:

```python
from longhaul import Daemon, DaemonConfig

def my_bot():
    while not Daemon._stop.is_set():   # cooperative
        do_work()
        Daemon.heartbeat()
```

Targets that loop forever without checking the stop event will be force-killed when
the host process exits (daemon threads).

## Why not just cron / systemd / supervisor?

You can absolutely use those. `longhaul` is for the **Python-native, in-process**
case: you want one process to own a fleet of jobs, with heartbeats and alerts wired
in code, and you want it to be portable across Windows/linux/macOS without admin
rights or extra services.

## Development

```bash
pip install -e . pytest
pytest -q
```

## License

[MIT](LICENSE) — do whatever you want, just keep the notice.
