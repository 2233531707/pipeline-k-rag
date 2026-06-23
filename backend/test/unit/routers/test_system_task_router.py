from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.routers import system_task_router
from server.utils.auth_middleware import get_admin_user


class FakeTask:
    id = "task-new"
    status = "pending"

    def to_summary_dict(self):
        return {"id": self.id, "status": self.status, "can_continue": False}


class FakeUser(SimpleNamespace):
    pass


def _build_app(monkeypatch, fake_tasker) -> TestClient:
    app = FastAPI()
    app.include_router(system_task_router.tasks, prefix="/api")

    async def fake_admin_user():
        return FakeUser(uid="admin", role="admin")

    app.dependency_overrides[get_admin_user] = fake_admin_user
    monkeypatch.setattr(system_task_router, "tasker", fake_tasker)
    return TestClient(app)


def test_continue_task_route_returns_new_task(monkeypatch):
    class FakeTasker:
        async def continue_task(self, task_id):
            assert task_id == "task-old"
            return FakeTask(), True

    client = _build_app(monkeypatch, FakeTasker())
    response = client.post("/api/tasks/task-old/continue")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "task-new",
        "previous_task_id": "task-old",
        "status": "pending",
        "deduplicated": False,
        "task": {"id": "task-new", "status": "pending", "can_continue": False},
    }


def test_continue_task_route_rejects_non_retryable_task(monkeypatch):
    class FakeTasker:
        async def continue_task(self, task_id):
            raise ValueError("只有可继续的失败任务可以继续执行")

    client = _build_app(monkeypatch, FakeTasker())
    response = client.post("/api/tasks/task-old/continue")

    assert response.status_code == 409
    assert "可继续" in response.json()["detail"]
