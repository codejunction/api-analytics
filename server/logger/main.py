from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from server.database.database import connection, valid_hostname, valid_path, valid_user_agent, valid_user_id

METHODS = {name: index for index, name in enumerate(("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "CONNECT", "HEAD", "TRACE"))}
FRAMEWORKS = {name: index for index, name in enumerate(("FastAPI", "Flask", "Gin", "Echo", "Express", "Fastify", "Koa", "Chi", "Fiber", "Actix", "Axum", "Tornado", "Django", "Rails", "Laravel", "Sinatra", "Rocket", "ASP.NET Core", "Hono"))}


class LoggedRequest(BaseModel):
    path: str
    hostname: str
    ip_address: str = ""
    user_agent: str
    method: str
    status: int
    response_time: int
    user_id: str = ""
    created_at: datetime


class LogPayload(BaseModel):
    api_key: str
    requests: list[LoggedRequest]
    framework: str
    privacy_level: int = Field(ge=0, le=2)


class PerKeyRateLimiter:
    def __init__(self, limit: int = 10, window_seconds: float = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.accesses: dict[str, deque[float]] = defaultdict(deque)

    def allowed(self, key: str) -> bool:
        now = time.monotonic()
        entries = self.accesses[key]
        while entries and entries[0] <= now - self.window_seconds:
            entries.popleft()
        if len(entries) >= self.limit:
            return False
        entries.append(now)
        return True


def _country_code(ip_address: str) -> str:
    if not ip_address:
        return ""
    try:
        import geoip2.database
        with geoip2.database.Reader(os.getenv("GEOIP_DATABASE", "GeoLite2-Country.mmdb")) as reader:
            return reader.country(ip_address).country.iso_code or ""
    except (FileNotFoundError, ValueError):
        return ""


def create_app() -> FastAPI:
    app = FastAPI(title="API Analytics Logger")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    limiter = PerKeyRateLimiter()
    max_insert = int(os.getenv("MAX_INSERT", "2000"))

    @app.get("/api/health")
    def health() -> dict[str, str]:
        try:
            with connection() as conn, conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as error:
            raise HTTPException(503, {"status": "unhealthy", "error": "Database connection failed"}) from error
        return {"status": "healthy"}

    @app.post("/api/log-request", status_code=201)
    @app.post("/api/requests", status_code=201)
    def log_requests(payload: LogPayload, request: Request) -> dict[str, object]:
        if not payload.api_key:
            raise HTTPException(400, {"status": 400, "message": "API key required."})
        if not limiter.allowed(payload.api_key):
            raise HTTPException(429, {"status": 429, "message": "Too many requests."})
        if not payload.requests or payload.framework not in FRAMEWORKS:
            raise HTTPException(400, {"status": 400, "message": "Invalid request data."})

        accepted: list[tuple[object, ...]] = []
        agents: set[str] = set()
        for item in payload.requests[:max_insert]:
            if item.method not in METHODS or not valid_path(item.path) or not valid_hostname(item.hostname) or not valid_user_agent(item.user_agent) or not valid_user_id(item.user_id):
                continue
            location = _country_code(item.ip_address) if payload.privacy_level < 2 else ""
            address = item.ip_address if payload.privacy_level == 0 else None
            agents.add(item.user_agent)
            accepted.append((payload.api_key.replace('"', ''), item.path[:255], item.hostname[:255], address, item.status, item.response_time, METHODS[item.method], FRAMEWORKS[payload.framework], location, item.user_id[:255], item.created_at, item.user_agent))
        if not accepted:
            raise HTTPException(400, {"status": 400, "message": "Invalid request data."})

        with connection() as conn, conn.cursor() as cursor:
            cursor.executemany("INSERT INTO user_agents (user_agent) VALUES (%s) ON CONFLICT (user_agent) DO NOTHING", [(agent,) for agent in agents])
            cursor.executemany("""INSERT INTO requests (api_key, path, hostname, ip_address, status, response_time, method, framework, location, user_id, created_at, user_agent_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,(SELECT id FROM user_agents WHERE user_agent=%s))""", accepted)
        return {"status": 201, "message": "API requests logged successfully."}

    return app


app = create_app()
