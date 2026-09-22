"""Scheduled monitor worker that records HTTP health checks for registered URLs."""
from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import requests

from server.database.database import connection


def probe(api_key: str, url: str, secure: bool, ping: bool) -> tuple[str, str, int, int, datetime] | None:
    del secure  # Retained for database/API compatibility; the URL defines the scheme.
    started = datetime.now(timezone.utc)
    try:
        response = requests.request("HEAD" if ping else "GET", url, timeout=2)
    except requests.RequestException:
        return None
    elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    return api_key, url, elapsed, response.status_code, datetime.now(timezone.utc)


def run() -> None:
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT api_key,url,secure,ping FROM monitor")
        monitors = cursor.fetchall()
    random.shuffle(monitors)
    with ThreadPoolExecutor(max_workers=min(32, max(1, len(monitors)))) as executor:
        results = []
        for future in as_completed([executor.submit(probe, *monitor) for monitor in monitors]):
            result = future.result()
            if result:
                results.append(result)
    with connection() as conn, conn.cursor() as cursor:
        if results:
            cursor.executemany("INSERT INTO pings (api_key,url,response_time,status,created_at) VALUES (%s,%s,%s,%s,%s)", results)
        cursor.execute("DELETE FROM pings WHERE created_at < %s", (datetime.now(timezone.utc) - timedelta(days=60),))


if __name__ == "__main__":
    run()
