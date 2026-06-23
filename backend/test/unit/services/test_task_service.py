from __future__ import annotations

import asyncio
from typing import Any

import pytest

from yuxi.services.task_service import RETRYABLE_FAILURE_STATUS, Tasker
from yuxi.utils.datetime_utils import format_utc_datetime, utc_isoformat

pytestmark = pytest.mark.asyncio


class FakeTaskRecord:
    def __init__(self, task_id: str, data: dict[str, Any]):
        self.id = task_id
        self.data = dict(data)

    def to_dict(self) -> dict[str, Any]:
        def convert(value):
            if value is None or isinstance(value, str):
                return value
            return format_utc_datetime(value)

        return {
            "id": self.id,
            "name": self.data.get("name", "Task"),
            "type": self.data.get("type", "general"),
            "status": self.data.get("status", "pending"),
            "progress": self.data.get("progress", 0.0),
            "message": self.data.get("message", ""),
            "created_at": convert(self.data.get("created_at") or utc_isoformat()),
            "updated_at": convert(self.data.get("updated_at") or utc_isoformat()),
            "started_at": convert(self.data.get("started_at")),
            "completed_at": convert(self.data.get("completed_at")),
            "payload": self.data.get("payload") or {},
            "result": self.data.get("result"),
            "error": self.data.get("error"),
            "cancel_requested": bool(self.data.get("cancel_requested", 0)),
        }


class FakeTaskRepository:
    def __init__(self, records: list[FakeTaskRecord] | None = None):
        self.records = {record.id: record for record in records or []}

    async def list_all(self) -> list[FakeTaskRecord]:
        return list(self.records.values())

    async def upsert(self, task_id: str, data: dict[str, Any]) -> FakeTaskRecord:
        record = FakeTaskRecord(task_id, data)
        self.records[task_id] = record
        return record

    async def delete(self, task_id: str) -> bool:
        return self.records.pop(task_id, None) is not None


async def _noop(context):
    await context.set_progress(100, "done")
    return {"ok": True}


async def _wait_for_status(tasker: Tasker, task_id: str, status: str) -> dict[str, Any]:
    for _ in range(80):
        task = await tasker.get_task(task_id)
        if task and task.get("status") == status:
            return task
        await asyncio.sleep(0.02)
    task = await tasker.get_task(task_id)
    raise AssertionError(f"task {task_id} did not reach {status}, got {task}")


async def test_enqueue_unique_enforces_task_type_and_business_resource():
    tasker = Tasker(repository=FakeTaskRepository())

    first, first_created = await tasker.enqueue_unique(
        name="图谱构建",
        task_type="graph_task",
        resource_key="kb:alpha",
        payload={"kb_id": "alpha"},
        coroutine=_noop,
    )
    duplicate, duplicate_created = await tasker.enqueue_unique(
        name="图谱构建",
        task_type="graph_task",
        resource_key="kb:alpha",
        payload={"kb_id": "alpha"},
        coroutine=_noop,
    )
    other_type, other_type_created = await tasker.enqueue_unique(
        name="文档解析",
        task_type="knowledge_parse",
        resource_key="kb:alpha",
        payload={"kb_id": "alpha"},
        coroutine=_noop,
    )

    assert first_created is True
    assert duplicate_created is False
    assert duplicate.id == first.id
    assert other_type_created is True
    assert other_type.id != first.id


async def test_hard_timeout_marks_retryable_failed_and_continue_links_new_task():
    repo = FakeTaskRepository()
    tasker = Tasker(worker_count=1, repository=repo, task_timeouts={"slow_task": 0.01})
    attempts = 0

    async def maybe_slow(context):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            await asyncio.sleep(1)
        await context.set_progress(90, "almost done")
        return {"attempts": attempts}

    await tasker.start()
    try:
        task = await tasker.enqueue(
            name="慢任务",
            task_type="slow_task",
            resource_key="resource:1",
            coroutine=maybe_slow,
        )

        timed_out = await _wait_for_status(tasker, task.id, RETRYABLE_FAILURE_STATUS)
        assert timed_out["can_continue"] is True
        assert timed_out["hard_timeout_seconds"] == 0.01
        assert timed_out["resource_key"] == "resource:1"
        assert any(entry["event"] == "timeout" for entry in timed_out["logs"])

        continued, created = await tasker.continue_task(task.id)
        assert created is True
        assert continued.id != task.id

        continued_detail = await tasker.get_task(continued.id)
        assert continued_detail["continuation_of"] == task.id
        assert continued_detail["retry_of"] == task.id
        assert any(entry["event"] == "continue_created" for entry in continued_detail["logs"])

        completed = await _wait_for_status(tasker, continued.id, "success")
        assert completed["result"] == {"attempts": 2}
    finally:
        await tasker.shutdown()


async def test_start_marks_pending_and_running_tasks_retryable_failed_after_restart():
    interrupted_payload = {
        "_tasker": {
            "resource_key": "kb:alpha",
            "hard_timeout_seconds": 60,
            "continuation_available": True,
            "logs": [],
        }
    }
    repo = FakeTaskRepository(
        [
            FakeTaskRecord(
                "task-pending",
                {
                    "name": "等待任务",
                    "type": "knowledge_parse",
                    "status": "pending",
                    "payload": interrupted_payload,
                },
            ),
            FakeTaskRecord(
                "task-running",
                {
                    "name": "运行任务",
                    "type": "knowledge_parse",
                    "status": "running",
                    "payload": interrupted_payload,
                },
            ),
        ]
    )
    tasker = Tasker(worker_count=1, repository=repo)

    await tasker.start()
    try:
        pending = await tasker.get_task("task-pending")
        running = await tasker.get_task("task-running")
    finally:
        await tasker.shutdown()

    for task in (pending, running):
        assert task["status"] == RETRYABLE_FAILURE_STATUS
        assert task["can_continue"] is False
        assert task["error"] == "服务重启时任务中断"
        assert any(entry["event"] == "restart_interrupted" for entry in task["logs"])
