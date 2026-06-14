from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "dummy-test-key")

from server.routers import knowledge_router


@pytest.mark.asyncio
async def test_export_portable_database_uses_database_name(monkeypatch) -> None:
    async def get_database_info(kb_id):
        assert kb_id == "kb-1"
        return {"kb_id": kb_id, "name": "示例知识库", "kb_type": "milvus"}

    captured = {}

    async def enqueue_unique_by_payload(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="task-1", status="pending"), True

    monkeypatch.setattr(knowledge_router.knowledge_base, "get_database_info", get_database_info)
    monkeypatch.setattr(
        knowledge_router.tasker,
        "enqueue_unique_by_payload",
        enqueue_unique_by_payload,
    )

    result = await knowledge_router.export_portable_database(
        "kb-1",
        current_user=SimpleNamespace(uid="user-1"),
    )

    assert captured["name"] == "导出知识库迁移包: 示例知识库"
    assert result["task_id"] == "task-1"


@pytest.mark.asyncio
async def test_import_portable_database_accepts_missing_filename(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(knowledge_router.config, "save_dir", str(tmp_path))
    monkeypatch.setattr(
        knowledge_router.model_cache,
        "get_model_info",
        lambda spec: SimpleNamespace(model_type="embedding"),
    )

    async def write_upload(file, path, **kwargs):
        del file, kwargs
        path.write_bytes(b"package")

    captured = {}

    async def enqueue_unique_by_payload(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="task-2", status="pending"), True

    monkeypatch.setattr(knowledge_router, "write_upload_to_path", write_upload)
    monkeypatch.setattr(
        knowledge_router.migration_checksums,
        "compute_sha256_hex",
        lambda path: "abc123",
    )
    monkeypatch.setattr(
        knowledge_router.tasker,
        "enqueue_unique_by_payload",
        enqueue_unique_by_payload,
    )

    result = await knowledge_router.import_portable_database(
        file=SimpleNamespace(filename=None),
        target_name="导入知识库",
        embedding_model_spec="provider/embed",
        graph_chat_model_spec=None,
        current_user=SimpleNamespace(uid="user-1", department_id="dept-1"),
    )

    assert captured["name"] == "导入知识库迁移包: package.yuxikb.zip"
    assert result["task_id"] == "task-2"
