from __future__ import annotations

import gzip
import json
import os
from datetime import date, datetime
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from server.database.database import connection, valid_date, valid_ip_address, valid_location, valid_status, valid_string


class MonitorInput(BaseModel):
    user_id: str
    url: str
    secure: bool = False
    ping: bool = False


def error(message: str, code: int = 400) -> HTTPException:
    return HTTPException(code, {"status": code, "message": message})


def _gzip_json(value: Any) -> Response:
    body = gzip.compress(json.dumps(value, default=str, separators=(",", ":")).encode())
    return Response(body, media_type="application/json", headers={"Content-Encoding": "gzip"})


def _user_key(cursor: Any, user_id: str) -> str:
    cursor.execute("SELECT api_key FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    if not row:
        raise error("Invalid user ID.")
    return str(row[0])


def _request_rows(cursor: Any, api_key: str, page: int, size: int) -> tuple[list[list[Any]], dict[str, str]]:
    cursor.execute("""SELECT r.ip_address::text, r.path, r.hostname, r.user_agent_id, r.method, r.response_time, r.status, r.location, r.user_id, r.created_at
        FROM requests r WHERE r.api_key=%s ORDER BY r.created_at LIMIT %s OFFSET %s""", (api_key, size, (page - 1) * size))
    rows = [list(row) for row in cursor.fetchall()]
    ids = [row[3] for row in rows if row[3] is not None]
    agents: dict[str, str] = {}
    if ids:
        cursor.execute("SELECT id, user_agent FROM user_agents WHERE id = ANY(%s)", (ids,))
        agents = {str(identifier): agent for identifier, agent in cursor.fetchall()}
    for row in rows:
        row[0] = (row[0] or "").split("/")[0]
        for index in (2, 7, 8):
            row[index] = row[index] or ""
    return rows, agents


def create_app() -> FastAPI:
    app = FastAPI(title="API Analytics API")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    page_size = int(os.getenv("PAGE_SIZE", "250000"))
    max_load = int(os.getenv("MAX_LOAD", "1000000"))

    @app.get("/api/health")
    def health() -> dict[str, str]:
        try:
            with connection() as conn, conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as exc:
            raise HTTPException(503, {"status": "unhealthy", "error": "Database connection failed"}) from exc
        return {"status": "healthy"}

    @app.get("/api/generate")
    @app.get("/api/generate-api-key")
    def generate_key() -> str:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("INSERT INTO users (api_key,user_id,created_at,last_accessed) VALUES (gen_random_uuid(),gen_random_uuid(),NOW(),NOW()) RETURNING api_key")
            return str(cursor.fetchone()[0])

    @app.get("/api/user-id/{api_key}")
    def user_id(api_key: str) -> str:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE api_key=%s", (api_key,))
            row = cursor.fetchone()
            if not row:
                raise error("Invalid API key.")
            return str(row[0])

    @app.get("/api/requests/{user_id}")
    @app.get("/api/requests/{user_id}/{page}")
    def dashboard_requests(user_id: str, page: int = Query(0, ge=0)) -> Response:
        with connection() as conn, conn.cursor() as cursor:
            api_key = _user_key(cursor, user_id)
            current = max(page, 1)
            rows: list[list[Any]] = []
            agents: dict[str, str] = {}
            while len(rows) < max_load:
                fetched, lookup = _request_rows(cursor, api_key, current, page_size)
                rows.extend(fetched)
                agents.update(lookup)
                if page or len(fetched) < page_size:
                    break
                current += 1
            cursor.execute("UPDATE users SET last_accessed=NOW() WHERE api_key=%s", (api_key,))
        return _gzip_json({"user_agents": agents, "requests": rows[:max_load]})

    @app.get("/api/data")
    def data(x_auth_token: str | None = Header(None), api_key: str | None = Header(None, alias="API-Key"), page: int = 1, compact: bool = False, date_value: date | None = Query(None, alias="date"), date_from: date | None = Query(None, alias="dateFrom"), date_to: date | None = Query(None, alias="dateTo"), hostname: str = "", ip: str = "", location: str = "", status: int = 0, user_id: str = Query("", alias="userID")) -> list[Any]:
        token = x_auth_token or api_key
        if not token:
            raise error("Invalid API key.")
        clauses, args = ["r.api_key=%s"], [token]
        if date_value and valid_date(date_value):
            clauses.extend(("r.created_at >= %s", "r.created_at < %s + interval '1 day'")); args.extend((date_value, date_value))
        else:
            if date_from and valid_date(date_from): clauses.append("r.created_at >= %s"); args.append(date_from)
            if date_to and valid_date(date_to): clauses.append("r.created_at <= %s"); args.append(date_to)
        for value, validator, column in ((ip, valid_ip_address, "r.ip_address"), (location, valid_location, "r.location"), (hostname, valid_string, "r.hostname"), (user_id, valid_string, "r.user_id")):
            if value and validator(value): clauses.append(f"{column}=%s"); args.append(value)
        if status and valid_status(status): clauses.append("r.status=%s"); args.append(status)
        args.extend((50_000, max(page - 1, 0) * 50_000))
        query = "SELECT r.ip_address::text,r.path,r.hostname,u.user_agent,r.method,r.response_time,r.status,r.location,r.user_id,r.created_at FROM requests r JOIN user_agents u ON r.user_agent_id=u.id WHERE " + " AND ".join(clauses) + " ORDER BY r.created_at LIMIT %s OFFSET %s"
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute(query, args); rows = [list(row) for row in cursor.fetchall()]
            cursor.execute("UPDATE users SET last_accessed=NOW() WHERE api_key=%s", (token,))
        if compact:
            return [["ip_address", "path", "hostname", "user_agent", "method", "response_time", "status", "location", "user_id", "created_at"], *rows]
        return [dict(zip(("ip_address","path","hostname","user_agent","method","response_time","status","location","user_id","created_at"), row)) for row in rows]

    @app.get("/api/delete/{api_key}")
    def delete_account(api_key: str) -> dict[str, object]:
        with connection() as conn, conn.cursor() as cursor:
            for table in ("requests", "monitor", "pings", "users"):
                cursor.execute(f"DELETE FROM {table} WHERE api_key=%s", (api_key,))
        return {"status": 200, "message": "Account data deleted successfully."}

    @app.get("/api/monitor/pings/{user_id}")
    def monitor_pings(user_id: str) -> dict[str, list[dict[str, Any]]]:
        with connection() as conn, conn.cursor() as cursor:
            key = _user_key(cursor, user_id)
            cursor.execute("SELECT url FROM monitor WHERE api_key=%s", (key,)); result = {url: [] for (url,) in cursor.fetchall()}
            cursor.execute("SELECT url,response_time,status,created_at FROM pings WHERE api_key=%s", (key,))
            for url, response_time, status, created_at in cursor.fetchall(): result.setdefault(url, []).append({"response_time": response_time, "status": status, "created_at": created_at})
        return result

    @app.post("/api/monitor/add", status_code=201)
    def add_monitor(monitor: MonitorInput) -> dict[str, object]:
        with connection() as conn, conn.cursor() as cursor:
            key = _user_key(cursor, monitor.user_id)
            cursor.execute("SELECT count(*) FROM monitor WHERE api_key=%s", (key,))
            if cursor.fetchone()[0] >= 3: raise error("Monitor limit reached.")
            try: cursor.execute("INSERT INTO monitor (api_key,url,secure,ping,created_at) VALUES (%s,%s,%s,%s,NOW())", (key, monitor.url, monitor.secure, monitor.ping))
            except Exception as exc: raise error("Monitor already exists.", 409) from exc
        return {"status": 201, "message": "New monitor created successfully."}

    @app.post("/api/monitor/delete", status_code=201)
    def delete_monitor(monitor: MonitorInput) -> dict[str, object]:
        with connection() as conn, conn.cursor() as cursor:
            key = _user_key(cursor, monitor.user_id)
            cursor.execute("DELETE FROM pings WHERE api_key=%s AND url=%s", (key, monitor.url)); cursor.execute("DELETE FROM monitor WHERE api_key=%s AND url=%s", (key, monitor.url))
        return {"status": 201, "message": "Monitor deleted successfully."}

    return app


app = create_app()
