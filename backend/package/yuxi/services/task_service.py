import asyncio
import copy
import uuid
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from yuxi.repositories.task_repository import TaskRepository
from yuxi.utils.datetime_utils import coerce_any_to_utc_datetime, utc_isoformat
from yuxi.utils.logging_config import logger

TaskCoroutine = Callable[["TaskContext"], Awaitable[Any]]
ACTIVE_STATUSES = {"pending", "running", "queued"}
RETRYABLE_FAILURE_STATUS = "retryable_failed"
TERMINAL_STATUSES = {"success", "failed", "cancelled", RETRYABLE_FAILURE_STATUS}
TASK_META_KEY = "_tasker"
MAX_TASK_LOGS = 100
DEFAULT_TASK_TYPE_TIMEOUTS: dict[str, float] = {
    "graph_task": 60 * 60,
    "knowledge_ingest": 2 * 60 * 60,
    "knowledge_parse": 60 * 60,
    "knowledge_index": 2 * 60 * 60,
    "knowledge_spatial_analysis": 60 * 60,
    "knowledge_portable_export": 2 * 60 * 60,
    "knowledge_portable_import": 3 * 60 * 60,
    "evaluation_benchmark_generation": 60 * 60,
    "evaluation_run": 2 * 60 * 60,
}


def _iso_to_utc_naive(value: str | None) -> datetime | None:
    if not value:
        return None
    return coerce_any_to_utc_datetime(value).replace(tzinfo=None)


def _normalise_timeout(value: float | int | None) -> float | None:
    if value is None:
        return None
    timeout = float(value)
    return timeout if timeout > 0 else None


def _get_payload_task_meta(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    meta = payload.get(TASK_META_KEY)
    return dict(meta) if isinstance(meta, dict) else {}


def _set_payload_task_meta(payload: dict[str, Any], meta: dict[str, Any]) -> None:
    payload[TASK_META_KEY] = meta


def _append_payload_task_log(
    payload: dict[str, Any],
    event: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    meta = _get_payload_task_meta(payload)
    logs = list(meta.get("logs") or [])
    logs.append(
        {
            "event": event,
            "message": message,
            "at": utc_isoformat(),
            "details": details or {},
        }
    )
    meta["logs"] = logs[-MAX_TASK_LOGS:]
    _set_payload_task_meta(payload, meta)


@dataclass
class Task:
    id: str
    name: str
    type: str
    status: str = "pending"
    progress: float = 0.0
    message: str = ""
    created_at: str = field(default_factory=utc_isoformat)
    updated_at: str = field(default_factory=utc_isoformat)
    started_at: str | None = None
    completed_at: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    result: Any | None = None
    error: str | None = None
    cancel_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        meta = _get_payload_task_meta(self.payload)
        data["resource_key"] = meta.get("resource_key")
        data["retry_of"] = meta.get("retry_of")
        data["continuation_of"] = meta.get("continuation_of")
        data["hard_timeout_seconds"] = meta.get("hard_timeout_seconds")
        data["logs"] = list(meta.get("logs") or [])
        data["can_continue"] = bool(
            self.status == RETRYABLE_FAILURE_STATUS and meta.get("continuation_available")
        )
        return data

    def to_summary_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        data.pop("payload", None)
        data.pop("result", None)
        data.pop("logs", None)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            id=data["id"],
            name=data.get("name", "Unnamed Task"),
            type=data.get("type", "general"),
            status=data.get("status", "pending"),
            progress=data.get("progress", 0.0),
            message=data.get("message", ""),
            created_at=data.get("created_at", utc_isoformat()),
            updated_at=data.get("updated_at", utc_isoformat()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            payload=data.get("payload", {}),
            result=data.get("result"),
            error=data.get("error"),
            cancel_requested=data.get("cancel_requested", False),
        )


class TaskContext:
    def __init__(self, tasker: "Tasker", task_id: str):
        self._tasker = tasker
        self.task_id = task_id

    async def set_progress(self, progress: float, message: str | None = None) -> None:
        await self._tasker._update_task(
            self.task_id,
            progress=max(0.0, min(progress, 100.0)),
            message=message,
        )

    async def set_message(self, message: str) -> None:
        await self._tasker._update_task(self.task_id, message=message)

    async def set_result(self, result: Any) -> None:
        await self._tasker._update_task(self.task_id, result=result)

    def is_cancel_requested(self) -> bool:
        return self._tasker._is_cancel_requested(self.task_id)

    async def raise_if_cancelled(self) -> None:
        if self.is_cancel_requested():
            raise asyncio.CancelledError("Task was cancelled")


class Tasker:
    def __init__(
        self,
        worker_count: int = 2,
        *,
        repository: TaskRepository | None = None,
        task_timeouts: dict[str, float | int | None] | None = None,
        default_timeout_seconds: float | int | None = None,
    ):
        self.worker_count = max(1, worker_count)
        self._queue: asyncio.Queue[tuple[str, TaskCoroutine]] = asyncio.Queue()
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()
        self._workers: list[asyncio.Task[Any]] = []
        self._started = False
        self._repo = repository or TaskRepository()
        self._task_timeouts = dict(DEFAULT_TASK_TYPE_TIMEOUTS)
        if task_timeouts:
            for task_type, timeout in task_timeouts.items():
                normalised = _normalise_timeout(timeout)
                if normalised is None:
                    self._task_timeouts.pop(task_type, None)
                else:
                    self._task_timeouts[task_type] = normalised
        self._default_timeout_seconds = _normalise_timeout(default_timeout_seconds)
        self._continuation_factories: dict[str, TaskCoroutine] = {}

    async def start(self) -> None:
        async with self._lock:
            if self._started:
                return
            await self._load_state()
            for _ in range(self.worker_count):
                worker = asyncio.create_task(self._worker_loop(), name="tasker-worker")
                self._workers.append(worker)
            self._started = True
            logger.info("Tasker started with {} workers", self.worker_count)

    async def shutdown(self) -> None:
        async with self._lock:
            if not self._started:
                return
            for worker in self._workers:
                worker.cancel()
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()
            self._started = False
            logger.info("Tasker shutdown complete")

    def configure_task_timeout(self, task_type: str, timeout_seconds: float | int | None) -> None:
        normalised = _normalise_timeout(timeout_seconds)
        if normalised is None:
            self._task_timeouts.pop(task_type, None)
        else:
            self._task_timeouts[task_type] = normalised

    async def enqueue(
        self,
        *,
        name: str,
        task_type: str,
        payload: dict[str, Any] | None = None,
        coroutine: TaskCoroutine,
        resource_key: str | None = None,
        hard_timeout_seconds: float | int | None = None,
    ) -> Task:
        task = self._build_task(
            name=name,
            task_type=task_type,
            payload=payload,
            resource_key=resource_key,
            hard_timeout_seconds=hard_timeout_seconds,
        )
        async with self._lock:
            self._tasks[task.id] = task
            self._continuation_factories[task.id] = coroutine
            await self._persist_task(task)
            await self._queue.put((task.id, coroutine))
        logger.info("Enqueued task {} ({})", task.id, name)
        return task

    async def enqueue_unique(
        self,
        *,
        name: str,
        task_type: str,
        resource_key: str,
        payload: dict[str, Any] | None = None,
        coroutine: TaskCoroutine,
        statuses: set[str] | None = None,
        hard_timeout_seconds: float | int | None = None,
    ) -> tuple[Task, bool]:
        active_statuses = statuses or ACTIVE_STATUSES
        async with self._lock:
            existing = self._find_task_by_resource_locked(task_type, resource_key, active_statuses)
            if existing:
                return existing, False
            task = self._build_task(
                name=name,
                task_type=task_type,
                payload=payload,
                resource_key=resource_key,
                hard_timeout_seconds=hard_timeout_seconds,
            )
            self._tasks[task.id] = task
            self._continuation_factories[task.id] = coroutine
            await self._persist_task(task)
            await self._queue.put((task.id, coroutine))
        logger.info("Enqueued task {} ({})", task.id, name)
        return task, True

    async def find_task_by_payload(
        self,
        *,
        task_type: str,
        payload_match: dict[str, Any],
        statuses: set[str] | None = None,
        resource_key: str | None = None,
    ) -> Task | None:
        async with self._lock:
            if resource_key:
                task = self._find_task_by_resource_locked(task_type, resource_key, statuses)
                if task:
                    return task
            return self._find_task_by_payload_locked(task_type, payload_match, statuses)

    async def find_task_by_resource(
        self,
        *,
        task_type: str,
        resource_key: str,
        statuses: set[str] | None = None,
    ) -> Task | None:
        async with self._lock:
            return self._find_task_by_resource_locked(task_type, resource_key, statuses)

    async def enqueue_unique_by_payload(
        self,
        *,
        name: str,
        task_type: str,
        payload: dict[str, Any] | None = None,
        coroutine: TaskCoroutine,
        payload_match: dict[str, Any],
        statuses: set[str] | None = None,
        resource_key: str | None = None,
        hard_timeout_seconds: float | int | None = None,
    ) -> tuple[Task, bool]:
        task_payload = payload or {}
        async with self._lock:
            existing = None
            if resource_key:
                existing = self._find_task_by_resource_locked(task_type, resource_key, statuses or ACTIVE_STATUSES)
            if existing is None:
                existing = self._find_task_by_payload_locked(task_type, payload_match, statuses)
            if existing:
                return existing, False
            task = self._build_task(
                name=name,
                task_type=task_type,
                payload=task_payload,
                resource_key=resource_key,
                hard_timeout_seconds=hard_timeout_seconds,
            )
            self._tasks[task.id] = task
            self._continuation_factories[task.id] = coroutine
            await self._persist_task(task)
            await self._queue.put((task.id, coroutine))
        logger.info("Enqueued task {} ({})", task.id, name)
        return task, True

    async def continue_task(self, task_id: str) -> tuple[Task, bool]:
        async with self._lock:
            previous = self._tasks.get(task_id)
            if not previous:
                raise KeyError("Task not found")
            if previous.status != RETRYABLE_FAILURE_STATUS:
                raise ValueError("只有可继续的失败任务可以继续执行")

            coroutine = self._continuation_factories.get(task_id)
            if coroutine is None:
                self._set_continuation_available_locked(previous, False)
                await self._persist_task(previous)
                raise ValueError("任务无法在当前进程继续执行，请重新提交原业务操作")

            previous_meta = _get_payload_task_meta(previous.payload)
            resource_key = previous_meta.get("resource_key")
            if resource_key:
                existing = self._find_task_by_resource_locked(previous.type, resource_key, ACTIVE_STATUSES)
                if existing:
                    return existing, False

            self._append_task_log_locked(previous, "continue_requested", "用户请求继续执行任务")
            self._set_continuation_available_locked(previous, False)
            business_payload = copy.deepcopy(previous.payload)
            business_payload.pop(TASK_META_KEY, None)
            retry_of = previous_meta.get("retry_of") or previous.id
            task = self._build_task(
                name=previous.name,
                task_type=previous.type,
                payload=business_payload,
                resource_key=resource_key,
                hard_timeout_seconds=previous_meta.get("hard_timeout_seconds"),
                retry_of=retry_of,
                continuation_of=previous.id,
            )
            self._append_task_log_locked(
                task,
                "continue_created",
                "继续执行任务已创建",
                {"previous_task_id": previous.id, "retry_of": retry_of},
            )
            self._tasks[task.id] = task
            self._continuation_factories[task.id] = coroutine
            await self._persist_task(previous)
            await self._persist_task(task)
            await self._queue.put((task.id, coroutine))
        logger.info("Continued task {} from {}", task.id, previous.id)
        return task, True

    def _build_task(
        self,
        *,
        name: str,
        task_type: str,
        payload: dict[str, Any] | None,
        resource_key: str | None,
        hard_timeout_seconds: float | int | None,
        retry_of: str | None = None,
        continuation_of: str | None = None,
    ) -> Task:
        task_payload = copy.deepcopy(payload or {})
        timeout = self._resolve_task_timeout(task_type, hard_timeout_seconds)
        meta = _get_payload_task_meta(task_payload)
        if resource_key:
            meta["resource_key"] = resource_key
        if timeout is not None:
            meta["hard_timeout_seconds"] = timeout
        if retry_of:
            meta["retry_of"] = retry_of
        if continuation_of:
            meta["continuation_of"] = continuation_of
        meta["continuation_available"] = True
        _set_payload_task_meta(task_payload, meta)
        task = Task(id=uuid.uuid4().hex, name=name, type=task_type, payload=task_payload)
        self._append_task_log_locked(task, "enqueued", "任务已排队", {"resource_key": resource_key})
        return task

    def _resolve_task_timeout(self, task_type: str, override: float | int | None) -> float | None:
        if override is not None:
            return _normalise_timeout(override)
        return self._task_timeouts.get(task_type, self._default_timeout_seconds)

    def _task_timeout(self, task: Task) -> float | None:
        meta = _get_payload_task_meta(task.payload)
        return _normalise_timeout(meta.get("hard_timeout_seconds"))

    def _find_task_by_payload_locked(
        self,
        task_type: str,
        payload_match: dict[str, Any],
        statuses: set[str] | None,
    ) -> Task | None:
        for task in self._tasks.values():
            if task.type != task_type:
                continue
            if statuses is not None and task.status not in statuses:
                continue
            if all(task.payload.get(key) == value for key, value in payload_match.items()):
                return task
        return None

    def _find_task_by_resource_locked(
        self,
        task_type: str,
        resource_key: str,
        statuses: set[str] | None,
    ) -> Task | None:
        for task in self._tasks.values():
            if task.type != task_type:
                continue
            if statuses is not None and task.status not in statuses:
                continue
            meta = _get_payload_task_meta(task.payload)
            if meta.get("resource_key") == resource_key:
                return task
        return None

    async def list_tasks(self, status: str | None = None, limit: int = 100) -> dict[str, Any]:
        async with self._lock:
            all_tasks = list(self._tasks.values())

        status_counter = Counter(task.status for task in all_tasks)
        type_counter = Counter(task.type for task in all_tasks)
        all_tasks.sort(key=lambda item: item.created_at or utc_isoformat(), reverse=True)

        tasks = all_tasks
        if status:
            tasks = [task for task in tasks if task.status == status]

        limited_tasks = tasks[: max(limit, 0)]

        summary: dict[str, Any] = {
            "total": len(all_tasks),
            "filtered_total": len(tasks),
            "status_counts": dict(status_counter),
            "type_counts": dict(type_counter),
        }

        return {
            "tasks": [task.to_summary_dict() for task in limited_tasks],
            "summary": summary,
        }

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        async with self._lock:
            task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    async def cancel_task(self, task_id: str) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.status in TERMINAL_STATUSES:
                return False
            task.cancel_requested = True
            task.updated_at = utc_isoformat()
            self._append_task_log_locked(task, "cancel_requested", "任务取消请求已记录")
            await self._persist_task(task)
        logger.info("Cancellation requested for task {}", task_id)
        return True

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task by id. Returns True if deleted, False if not found."""
        async with self._lock:
            if task_id not in self._tasks:
                return False
            del self._tasks[task_id]
            self._continuation_factories.pop(task_id, None)
        await self._repo.delete(task_id)
        logger.info("Deleted task {}", task_id)
        return True

    async def _worker_loop(self) -> None:
        while True:
            try:
                task_id, coroutine = await self._queue.get()
                try:
                    task = await self._get_task_instance(task_id)
                    if not task:
                        continue
                    if task.cancel_requested:
                        await self._mark_cancelled(task_id, "Task was cancelled before execution")
                        continue
                    await self._update_task(
                        task_id,
                        status="running",
                        progress=0.0,
                        message="任务开始执行",
                        started_at=utc_isoformat(),
                        log_event="started",
                        log_message="任务开始执行",
                    )
                    context = TaskContext(self, task_id)
                    try:
                        timeout = self._task_timeout(task)
                        if timeout is None:
                            result = await coroutine(context)
                        else:
                            result = await asyncio.wait_for(coroutine(context), timeout=timeout)
                        if task.cancel_requested:
                            await self._mark_cancelled(task_id, "Task cancelled during execution")
                            continue
                        await self._update_task(
                            task_id,
                            status="success",
                            progress=100.0,
                            message="任务已完成",
                            result=result,
                            completed_at=utc_isoformat(),
                            log_event="success",
                            log_message="任务已完成",
                        )
                    except TimeoutError:
                        timeout = self._task_timeout(task)
                        await self._mark_retryable_failed(
                            task_id,
                            message="任务执行超时，可继续执行",
                            error=f"任务执行超过硬超时限制 {timeout:g} 秒" if timeout else "任务执行超时",
                            event="timeout",
                            details={"timeout_seconds": timeout},
                        )
                    except asyncio.CancelledError:
                        current_task = asyncio.current_task()
                        if current_task and current_task.cancelling():
                            raise
                        await self._mark_cancelled(task_id, "任务被取消")
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("Task {} failed: {}", task_id, exc)
                        await self._update_task(
                            task_id,
                            status="failed",
                            progress=100.0,
                            message="任务执行失败",
                            error=str(exc),
                            completed_at=utc_isoformat(),
                            log_event="failed",
                            log_message="任务执行失败",
                            log_details={"error": str(exc)},
                        )
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.exception("Tasker worker error: {}", exc)

    async def _get_task_instance(self, task_id: str) -> Task | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def _mark_cancelled(self, task_id: str, message: str) -> None:
        await self._update_task(
            task_id,
            status="cancelled",
            progress=100.0,
            message=message,
            completed_at=utc_isoformat(),
            log_event="cancelled",
            log_message=message,
        )

    async def _mark_retryable_failed(
        self,
        task_id: str,
        *,
        message: str,
        error: str,
        event: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task.status = RETRYABLE_FAILURE_STATUS
            task.progress = 100.0
            task.message = message
            task.error = error
            task.completed_at = utc_isoformat()
            task.updated_at = utc_isoformat()
            self._set_continuation_available_locked(task, task_id in self._continuation_factories)
            self._append_task_log_locked(task, event, message, details)
            await self._persist_task(task)

    async def _update_task(
        self,
        task_id: str,
        *,
        status: str | None = None,
        progress: float | None = None,
        message: str | None = None,
        result: Any = None,
        error: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
        log_event: str | None = None,
        log_message: str | None = None,
        log_details: dict[str, Any] | None = None,
    ) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            if status:
                task.status = status
            if progress is not None:
                task.progress = max(0.0, min(progress, 100.0))
            if message is not None:
                task.message = message
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            if started_at is not None:
                task.started_at = started_at
            if completed_at is not None:
                task.completed_at = completed_at
            if status in TERMINAL_STATUSES and status != RETRYABLE_FAILURE_STATUS:
                self._set_continuation_available_locked(task, False)
            if log_event:
                self._append_task_log_locked(task, log_event, log_message or message or log_event, log_details)
            task.updated_at = utc_isoformat()
            await self._persist_task(task)

    def _is_cancel_requested(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        return bool(task and task.cancel_requested)

    async def _load_state(self) -> None:
        records = await self._repo.list_all()
        updated: list[Task] = []
        for record in records:
            task = Task.from_dict(record.to_dict())
            if task.status not in TERMINAL_STATUSES:
                task.status = RETRYABLE_FAILURE_STATUS
                task.progress = 100.0
                task.message = "服务重启时任务中断，可继续执行"
                task.error = "服务重启时任务中断"
                task.completed_at = utc_isoformat()
                task.updated_at = utc_isoformat()
                self._set_continuation_available_locked(task, False)
                self._append_task_log_locked(task, "restart_interrupted", task.message)
                updated.append(task)
            self._tasks[task.id] = task
        for task in updated:
            await self._persist_task(task)
        if updated:
            logger.info("Marked {} interrupted tasks as retryable failed", len(updated))

    def _set_continuation_available_locked(self, task: Task, available: bool) -> None:
        meta = _get_payload_task_meta(task.payload)
        meta["continuation_available"] = bool(available)
        _set_payload_task_meta(task.payload, meta)

    def _append_task_log_locked(
        self,
        task: Task,
        event: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        _append_payload_task_log(task.payload, event, message, details)

    async def _persist_task(self, task: Task) -> None:
        data: dict[str, Any] = {
            "name": task.name,
            "type": task.type,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "payload": task.payload,
            "result": task.result,
            "error": task.error,
            "cancel_requested": 1 if task.cancel_requested else 0,
            "created_at": _iso_to_utc_naive(task.created_at),
            "updated_at": _iso_to_utc_naive(task.updated_at),
            "started_at": _iso_to_utc_naive(task.started_at),
            "completed_at": _iso_to_utc_naive(task.completed_at),
        }
        await self._repo.upsert(task.id, data)


tasker = Tasker()


__all__ = [
    "ACTIVE_STATUSES",
    "RETRYABLE_FAILURE_STATUS",
    "TERMINAL_STATUSES",
    "tasker",
    "TaskContext",
    "Tasker",
]
