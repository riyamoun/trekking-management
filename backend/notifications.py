"""Notification helpers with local mock fallback when mail/webhook secrets are missing."""

from __future__ import annotations

import json
import smtplib
import urllib.request
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from flask import current_app

from backend.extensions import db
from backend.models import NotificationLog


def _append_mock_file(channel: str, recipient: str, subject: str, body: str) -> None:
    reports = Path(current_app.config["REPORTS_DIR"])
    reports.mkdir(parents=True, exist_ok=True)
    log_path = reports / "notifications.log"
    stamp = datetime.utcnow().isoformat()
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(
            f"\n[{stamp}] channel={channel} to={recipient} subject={subject}\n{body}\n"
            f"{'-' * 60}\n"
        )


def _persist_log(channel: str, recipient: str, subject: str, body: str) -> None:
    entry = NotificationLog(
        channel=channel, recipient=recipient, subject=subject, body=body
    )
    db.session.add(entry)
    db.session.commit()


def send_email(recipient: str, subject: str, html_body: str, text_body: str | None = None) -> dict:
    """Send email via SMTP when configured; otherwise write a mock log."""
    server = current_app.config.get("MAIL_SERVER") or ""
    username = current_app.config.get("MAIL_USERNAME") or ""
    password = current_app.config.get("MAIL_PASSWORD") or ""
    sender = current_app.config.get("MAIL_DEFAULT_SENDER", "noreply@trekmanage.local")

    if not server or not username:
        _append_mock_file("mock-email", recipient, subject, html_body)
        _persist_log("mock", recipient, subject, html_body)
        return {"ok": True, "channel": "mock", "recipient": recipient}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(text_body or subject, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        port = int(current_app.config.get("MAIL_PORT", 587))
        use_tls = current_app.config.get("MAIL_USE_TLS", True)
        with smtplib.SMTP(server, port, timeout=15) as smtp:
            if use_tls:
                smtp.starttls()
            smtp.login(username, password)
            smtp.sendmail(sender, [recipient], msg.as_string())
        _persist_log("email", recipient, subject, html_body)
        return {"ok": True, "channel": "email", "recipient": recipient}
    except Exception as exc:
        fallback = f"(email failed: {exc})\n{html_body}"
        _append_mock_file("mock-email-fallback", recipient, subject, fallback)
        _persist_log("mock", recipient, subject, fallback)
        return {"ok": True, "channel": "mock", "error": str(exc)}


def send_webhook(payload: dict) -> dict:
    """POST JSON to WEBHOOK_URL when set; otherwise mock."""
    url = current_app.config.get("WEBHOOK_URL") or ""
    body = json.dumps(payload)
    if not url:
        _append_mock_file("mock-webhook", "local", payload.get("text", "webhook"), body)
        _persist_log("mock", "webhook", payload.get("text", "webhook"), body)
        return {"ok": True, "channel": "mock"}

    try:
        req = urllib.request.Request(
            url,
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            _persist_log("webhook", url, payload.get("text", "webhook"), body)
            return {"ok": True, "channel": "webhook", "status": resp.status}
    except Exception as exc:
        _append_mock_file("mock-webhook-fallback", url or "local", "webhook", f"{exc}\n{body}")
        _persist_log("mock", url or "webhook", "webhook", f"{exc}\n{body}")
        return {"ok": True, "channel": "mock", "error": str(exc)}


def notify_booking(user_email: str, user_name: str, trek_name: str, action: str) -> None:
    subject = f"Booking {action}: {trek_name}"
    html = f"""
    <h2>TrekManage — Booking {action}</h2>
    <p>Hi {user_name},</p>
    <p>Your booking for <strong>{trek_name}</strong> has been <strong>{action}</strong>.</p>
    <p>— TrekManage</p>
    """
    send_email(user_email, subject, html)
    send_webhook({"text": f"Booking {action} for {user_name}: {trek_name}"})
