"""Validation rules matching the former Go database package."""
from __future__ import annotations

import ipaddress
import re
from datetime import date, datetime, timedelta, timezone

_SQL_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE", "EXEC", "EXECUTE", "UNION", "SCRIPT", "DECLARE")
_SQL_PATTERNS = (re.compile(r"(?i)('|(\\)|;|--|/\*|\*/|xp_|sp_)"), re.compile(r"(?i)(union\s+select|drop\s+table|insert\s+into)"), re.compile(r'''(?i)(\bor\b|\band\b)\s*['\"]?\s*\d+\s*['\"]?\s*[=><]'''))



def valid_string(value: str, maximum: int = 10_000) -> bool:
    if not value or len(value) > maximum or any(ord(char) == 0 or (ord(char) < 32 and char not in "\t\n\r") for char in value):
        return False
    upper = value.upper()
    return not any(keyword in upper for keyword in _SQL_KEYWORDS) and not any(pattern.search(value) for pattern in _SQL_PATTERNS)


def valid_hostname(value: str) -> bool:
    return bool(value) and len(value) <= 253 and valid_string(value)


def valid_path(value: str) -> bool:
    return bool(value) and len(value) <= 2048 and valid_string(value)


def valid_user_agent(value: str) -> bool:
    return bool(value) and len(value) <= 1024 and valid_string(value)


def valid_user_id(value: str) -> bool:
    return bool(value) and len(value) <= 255 and valid_string(value)


def valid_location(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{2}", value))


def valid_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return len(value) <= 45


def valid_status(value: int) -> bool:
    return 100 <= value <= 599


def valid_date(value: date | datetime | None) -> bool:
    if value is None:
        return False
    value_date = value.date() if isinstance(value, datetime) else value
    today = datetime.now(timezone.utc).date()
    return today - timedelta(days=36525) < value_date < today + timedelta(days=3652)
