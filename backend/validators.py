"""Shared validation helpers."""

import re

from email_validator import EmailNotValidError, validate_email

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    """Accept RFC emails; also allow *.local addresses for offline demos."""
    email = (email or "").strip().lower()
    if not email:
        return False
    if email.endswith(".local"):
        return bool(_EMAIL_RE.match(email))
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False
