"""Pluggable alert channels. Built on the standard library — zero extra deps."""
from __future__ import annotations

import json
import smtplib
import urllib.request
from email.mime.text import MIMEText


class AlertBase:
    def send(self, message: str) -> None:  # pragma: no cover
        raise NotImplementedError


class _HTTPMixin:
    url: str

    def _post(self, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=data, headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)


class TelegramAlert(AlertBase, _HTTPMixin):
    def __init__(self, token: str, chat_id: str):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def send(self, message: str) -> None:
        self._post({"chat_id": self.chat_id, "text": message})


class DiscordAlert(AlertBase, _HTTPMixin):
    def __init__(self, webhook_url: str):
        self.url = webhook_url

    def send(self, message: str) -> None:
        self._post({"content": message})


class WebhookAlert(AlertBase, _HTTPMixin):
    def __init__(self, url: str):
        self.url = url

    def send(self, message: str) -> None:
        self._post({"text": message})


class EmailAlert(AlertBase):
    def __init__(self, host: str, port: int, user: str, password: str,
                 to_addr: str, use_tls: bool = True):
        self.host, self.port = host, port
        self.user, self.password = user, password
        self.to_addr = to_addr
        self.use_tls = use_tls

    def send(self, message: str) -> None:
        msg = MIMEText(message)
        msg["Subject"] = "longhaul alert"
        msg["From"] = self.user
        msg["To"] = self.to_addr
        with smtplib.SMTP(self.host, self.port) as s:
            if self.use_tls:
                s.starttls()
            s.login(self.user, self.password)
            s.sendmail(self.user, [self.to_addr], msg.as_string())
