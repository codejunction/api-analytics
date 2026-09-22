from server.database.database import connection

def users_count(interval: str = "") -> int:
    query = "SELECT count(*) FROM users" + (" WHERE created_at >= NOW() - %s::interval" if interval else "")
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute(query, (interval,) if interval else ()); return cursor.fetchone()[0]
