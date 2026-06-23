from __future__ import annotations

import logging
from io import StringIO

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from server.routers.auth_router import auth
from server.utils.access_log_middleware import AccessLogMiddleware
from server.utils.auth_middleware import get_current_user, get_db
from server.utils.cors import get_cors_allow_origins, parse_cors_allow_origins


def test_cors_allowlist_rejects_wildcard_origin():
    with pytest.raises(ValueError, match="wildcard"):
        parse_cors_allow_origins("http://localhost,*")


def test_production_cors_defaults_to_same_origin_only(monkeypatch):
    monkeypatch.setenv("YUXI_ENV", "production")
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)

    assert get_cors_allow_origins() == []


def test_auth_me_route_returns_401_when_current_user_is_missing():
    app = FastAPI()

    async def missing_user():
        return None

    async def fake_db():
        yield None

    app.dependency_overrides[get_current_user] = missing_user
    app.dependency_overrides[get_db] = fake_db
    app.include_router(auth, prefix="/api")
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "请登录后再访问"


def test_local_cors_allowlist_accepts_local_web_origin_only():
    origins = parse_cors_allow_origins("http://localhost,http://127.0.0.1")
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    client = TestClient(app)

    allowed = client.options(
        "/ping",
        headers={"Origin": "http://localhost", "Access-Control-Request-Method": "GET"},
    )
    rejected = client.options(
        "/ping",
        headers={"Origin": "https://example.com", "Access-Control-Request-Method": "GET"},
    )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost"
    assert "access-control-allow-origin" not in rejected.headers


def test_access_log_does_not_emit_authorization_header_or_request_body():
    app = FastAPI()

    @app.post("/echo")
    async def echo():
        return {"ok": True}

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("test_access_log_security")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    app.add_middleware(AccessLogMiddleware, logger=logger)
    client = TestClient(app)

    response = client.post(
        "/echo?visible=true",
        headers={"Authorization": "Bearer secret-token"},
        json={"password": "secret-body"},
    )

    assert response.status_code == 200
    log_text = stream.getvalue()
    assert "POST /echo?visible=true" in log_text
    assert "Authorization" not in log_text
    assert "secret-token" not in log_text
    assert "password" not in log_text
    assert "secret-body" not in log_text
