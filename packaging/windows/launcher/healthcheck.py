from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class HealthResult:
    ok: bool
    url: str
    detail: str


def check_url(url: str, timeout: float = 3.0) -> HealthResult:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            detail = f"HTTP {response.status}"
            if "application/json" in response.headers.get("content-type", ""):
                payload = json.loads(body)
                detail = str(payload.get("message") or payload.get("status") or detail)
            return HealthResult(200 <= response.status < 400, url, detail)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        return HealthResult(False, url, str(exc))


def wait_for_health(url: str, timeout: float = 180.0, interval: float = 3.0) -> HealthResult:
    deadline = time.monotonic() + timeout
    result = check_url(url)
    while not result.ok and time.monotonic() < deadline:
        time.sleep(interval)
        result = check_url(url)
    return result
