"""Database query helpers retained at the former Go package location."""
from .database import connection


def create_user() -> str:
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("INSERT INTO users (api_key,user_id,created_at,last_accessed) VALUES (gen_random_uuid(),gen_random_uuid(),NOW(),NOW()) RETURNING api_key")
        return str(cursor.fetchone()[0])


def get_user_id(api_key: str) -> str | None:
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT user_id FROM users WHERE api_key=%s", (api_key,))
        row = cursor.fetchone()
        return str(row[0]) if row else None


def get_api_key(user_id: str) -> str | None:
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT api_key FROM users WHERE user_id=%s", (user_id,))
        row = cursor.fetchone()
        return str(row[0]) if row else None
