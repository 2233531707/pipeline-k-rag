from __future__ import annotations

import os

LOCAL_WEB_CORS_ORIGINS = (
    "kb-desktop://app",
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:15173",
    "http://127.0.0.1:15173",
)


def parse_cors_allow_origins(raw_origins: str | None) -> list[str]:
    if raw_origins is None:
        return []

    origins: list[str] = []
    for item in raw_origins.split(","):
        origin = item.strip().rstrip("/")
        if not origin:
            continue
        if origin == "*":
            raise ValueError("CORS_ALLOW_ORIGINS wildcard origins are not allowed with credentials.")
        if origin not in origins:
            origins.append(origin)
    return origins


def get_cors_allow_origins() -> list[str]:
    env_origins = os.getenv("CORS_ALLOW_ORIGINS")
    if env_origins is not None:
        return parse_cors_allow_origins(env_origins)

    yuxi_env = (os.getenv("YUXI_ENV") or "development").strip().lower()
    if yuxi_env == "production":
        return []
    return list(LOCAL_WEB_CORS_ORIGINS)
