"""知识库创建时的图谱抽取模型配置流程测试。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from server.routers import knowledge_router


def _user():
    return SimpleNamespace(uid="user-1", department_id="dept-1")


def _patch_create_dependencies(monkeypatch, *, chat_model_type: str | None = "chat"):
    monkeypatch.setattr(knowledge_router.knowledge_base, "database_name_exists", AsyncMock(return_value=False))
    monkeypatch.setattr(
        knowledge_router.knowledge_base,
        "create_database",
        AsyncMock(return_value={"kb_id": "kb-created", "name": "测试知识库"}),
    )
    monkeypatch.setattr(knowledge_router.knowledge_base, "delete_database", AsyncMock())
    monkeypatch.setattr(
        knowledge_router.model_cache,
        "get_model_info",
        lambda spec: (
            SimpleNamespace(model_type="embedding" if spec == "embed/model" else chat_model_type)
            if chat_model_type
            else None
        ),
    )

    configure = AsyncMock(
        return_value={
            "locked": True,
            "extractor_type": "llm",
            "extractor_options": {"model_spec": "chat/model"},
        }
    )
    monkeypatch.setattr(knowledge_router.MilvusGraphService, "configure", configure)

    from yuxi.agents.buildin import agent_manager

    monkeypatch.setattr(agent_manager, "reload_all", AsyncMock())
    return configure


async def _create(graph_build_config):
    return await knowledge_router.create_database(
        database_name="测试知识库",
        description="",
        embedding_model_spec="embed/model",
        kb_type="milvus",
        additional_params={},
        llm_model_spec=None,
        graph_build_config=graph_build_config,
        share_config=None,
        group_id=None,
        current_user=_user(),
    )


@pytest.mark.asyncio
async def test_create_without_graph_config_succeeds(monkeypatch):
    configure = _patch_create_dependencies(monkeypatch)
    result = await _create(None)
    assert result["kb_id"] == "kb-created"
    configure.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_passes_group_id_to_manager(monkeypatch):
    _patch_create_dependencies(monkeypatch)
    await knowledge_router.create_database(
        database_name="测试知识库",
        description="",
        embedding_model_spec="embed/model",
        kb_type="milvus",
        additional_params={},
        llm_model_spec=None,
        graph_build_config=None,
        share_config=None,
        group_id="group-1",
        current_user=_user(),
    )
    assert knowledge_router.knowledge_base.create_database.await_args.kwargs["group_id"] == "group-1"


@pytest.mark.asyncio
async def test_graph_config_requires_chat_model(monkeypatch):
    _patch_create_dependencies(monkeypatch)
    with pytest.raises(HTTPException, match="必须选择 Chat 模型") as exc_info:
        await _create({"enabled": True, "extractor_type": "llm", "extractor_options": {}})
    assert exc_info.value.status_code == 400
    knowledge_router.knowledge_base.create_database.assert_not_awaited()


@pytest.mark.asyncio
async def test_graph_config_rejects_non_chat_model(monkeypatch):
    _patch_create_dependencies(monkeypatch, chat_model_type="embedding")
    with pytest.raises(HTTPException, match="不支持的 Chat 模型"):
        await _create(
            {
                "enabled": True,
                "extractor_type": "llm",
                "extractor_options": {"model_spec": "not-chat/model"},
            }
        )


@pytest.mark.asyncio
async def test_graph_config_rejects_credentials(monkeypatch):
    _patch_create_dependencies(monkeypatch)
    with pytest.raises(HTTPException, match="不得包含 API Key"):
        await _create(
            {
                "enabled": True,
                "extractor_type": "llm",
                "extractor_options": {
                    "model_spec": "chat/model",
                    "model_params": {"api_key": "secret"},
                },
            }
        )


@pytest.mark.asyncio
async def test_graph_config_is_persisted_by_configure(monkeypatch):
    configure = _patch_create_dependencies(monkeypatch)
    options = {
        "model_spec": "chat/model",
        "schema": "管道, 阀门",
        "concurrency_count": 2,
        "model_params": {},
    }
    result = await _create(
        {
            "enabled": True,
            "extractor_type": "llm",
            "extractor_options": options,
        }
    )
    configure.assert_awaited_once_with(
        "kb-created",
        extractor_type="llm",
        extractor_options=options,
        created_by="user-1",
    )
    assert result["graph_build_config"]["locked"] is True


@pytest.mark.asyncio
async def test_configure_failure_rolls_back_created_database(monkeypatch):
    configure = _patch_create_dependencies(monkeypatch)
    configure.side_effect = ValueError("配置无效")
    with pytest.raises(HTTPException, match="图谱抽取预配置失败"):
        await _create(
            {
                "enabled": True,
                "extractor_type": "llm",
                "extractor_options": {"model_spec": "chat/model"},
            }
        )
    knowledge_router.knowledge_base.delete_database.assert_awaited_once_with("kb-created")


@pytest.mark.asyncio
async def test_graph_build_index_rejects_over_limit_config_before_enqueue(monkeypatch):
    async def fake_has_running(kb_id: str) -> bool:
        return False

    class FakeGraphService:
        async def validate_build_config(self, kb_id: str):
            raise ValueError("图谱抽取并发数 8 不能超过部署上限 3")

    async def fake_enqueue_unique_by_payload(**kwargs):
        raise AssertionError("over-limit graph build should not be enqueued")

    monkeypatch.setattr(knowledge_router, "_has_running_graph_build_task", fake_has_running)
    monkeypatch.setattr(
        knowledge_router.knowledge_base, "get_database_info", AsyncMock(return_value={"name": "测试知识库"})
    )
    monkeypatch.setattr(knowledge_router, "MilvusGraphService", lambda: FakeGraphService())
    monkeypatch.setattr(knowledge_router.tasker, "enqueue_unique_by_payload", fake_enqueue_unique_by_payload)

    with pytest.raises(HTTPException) as exc_info:
        await knowledge_router.index_graph_build("kb_1", {"batch_size": 20}, current_user=_user())

    assert exc_info.value.status_code == 400
    assert "不能超过部署上限 3" in exc_info.value.detail
