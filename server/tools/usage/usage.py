from server.database.database import connection

def table_size(table: str) -> str:
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT pg_size_pretty(pg_total_relation_size(%s))", (table,)); return cursor.fetchone()[0]
