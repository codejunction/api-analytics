"""PostgreSQL connection helpers shared by services."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg

from .sanitize import *  # noqa: F403


def database_url() -> str:
    value = os.getenv("POSTGRES_URL")
    if not value:
        raise RuntimeError("POSTGRES_URL is not set in the environment")
    return value


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    with psycopg.connect(database_url()) as conn:
        yield conn
