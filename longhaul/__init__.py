"""longhaul — self-healing long-running job framework.

Wrap any callable into a daemon that auto-restarts on crash, survives hangs via
health checks, and shouts at you through Telegram / Discord / email / webhooks
when something is actually wrong.
"""

from .core import Daemon, DaemonConfig, DaemonError
from .supervisor import Supervisor
from .alerts import (
    AlertBase,
    TelegramAlert,
    DiscordAlert,
    WebhookAlert,
    EmailAlert,
)

__version__ = "0.1.0"

__all__ = [
    "Daemon",
    "DaemonConfig",
    "DaemonError",
    "Supervisor",
    "AlertBase",
    "TelegramAlert",
    "DiscordAlert",
    "WebhookAlert",
    "EmailAlert",
]
