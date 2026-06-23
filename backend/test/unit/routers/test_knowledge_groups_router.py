from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from server.routers import knowledge_router


@pytest.mark.asyncio
async def test_list_knowledge_groups_returns_default_group(monkeypatch):
    async def fake_list_groups():
        return {
            "groups": [
                {
                    "group_id": "default",
                    "name": "默认分组",
                    "is_default": True,
                }
            ]
        }

    monkeypatch.setattr(knowledge_router.knowledge_base, "list_groups", fake_list_groups)

    result = await knowledge_router.list_knowledge_groups(current_user=SimpleNamespace(uid="admin"))

    assert result["groups"] == [
        {
            "group_id": "default",
            "name": "默认分组",
            "is_default": True,
        }
    ]


@pytest.mark.asyncio
async def test_create_knowledge_group_trims_name(monkeypatch):
    async def fake_create_group(name, created_by=None, parent_group_id=None):
        assert name == "项目资料"
        assert created_by == "admin"
        assert parent_group_id is None
        return {"group_id": "group-1", "name": name, "is_default": False}

    monkeypatch.setattr(knowledge_router.knowledge_base, "create_group", fake_create_group)

    result = await knowledge_router.create_knowledge_group(
        knowledge_router.CreateKnowledgeGroupRequest(name="  项目资料  "),
        current_user=SimpleNamespace(uid="admin"),
    )

    assert result == {"group_id": "group-1", "name": "项目资料", "is_default": False}


@pytest.mark.asyncio
async def test_create_nested_knowledge_group_passes_parent_group(monkeypatch):
    async def fake_create_group(name, created_by=None, parent_group_id=None):
        assert name == "施工资料"
        assert created_by == "admin"
        assert parent_group_id == "group-parent"
        return {
            "group_id": "group-child",
            "name": name,
            "is_default": False,
            "parent_group_id": parent_group_id,
        }

    monkeypatch.setattr(knowledge_router.knowledge_base, "create_group", fake_create_group)

    result = await knowledge_router.create_knowledge_group(
        knowledge_router.CreateKnowledgeGroupRequest(name="  施工资料  ", parent_group_id="group-parent"),
        current_user=SimpleNamespace(uid="admin"),
    )

    assert result == {
        "group_id": "group-child",
        "name": "施工资料",
        "is_default": False,
        "parent_group_id": "group-parent",
    }


@pytest.mark.asyncio
async def test_create_knowledge_group_rejects_duplicate_name(monkeypatch):
    async def fake_create_group(name, created_by=None, parent_group_id=None):
        raise ValueError("知识库分组名称已存在")

    monkeypatch.setattr(knowledge_router.knowledge_base, "create_group", fake_create_group)

    with pytest.raises(HTTPException) as exc_info:
        await knowledge_router.create_knowledge_group(
            knowledge_router.CreateKnowledgeGroupRequest(name="项目资料"),
            current_user=SimpleNamespace(uid="admin"),
        )

    assert exc_info.value.status_code == 400
    assert "已存在" in exc_info.value.detail


@pytest.mark.asyncio
async def test_default_knowledge_group_cannot_be_renamed(monkeypatch):
    async def fake_rename_group(group_id, name):
        raise ValueError("默认分组不能重命名")

    monkeypatch.setattr(knowledge_router.knowledge_base, "rename_group", fake_rename_group)

    with pytest.raises(HTTPException) as exc_info:
        await knowledge_router.rename_knowledge_group(
            "default",
            knowledge_router.RenameKnowledgeGroupRequest(name="新名称"),
            current_user=SimpleNamespace(uid="admin"),
        )

    assert exc_info.value.status_code == 400
    assert "默认分组" in exc_info.value.detail


@pytest.mark.asyncio
async def test_default_knowledge_group_cannot_be_deleted(monkeypatch):
    async def fake_delete_group(group_id):
        raise ValueError("默认分组不能删除")

    monkeypatch.setattr(knowledge_router.knowledge_base, "delete_group", fake_delete_group)

    with pytest.raises(HTTPException) as exc_info:
        await knowledge_router.delete_knowledge_group("default", current_user=SimpleNamespace(uid="admin"))

    assert exc_info.value.status_code == 400
    assert "默认分组" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_group_rejects_when_has_child_groups(monkeypatch):
    async def fake_delete_group(group_id):
        raise ValueError("知识库分组下仍有子分组，不能删除")

    monkeypatch.setattr(knowledge_router.knowledge_base, "delete_group", fake_delete_group)

    with pytest.raises(HTTPException) as exc_info:
        await knowledge_router.delete_knowledge_group("group-parent", current_user=SimpleNamespace(uid="admin"))

    assert exc_info.value.status_code == 400
    assert "子分组" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_database_can_move_to_group(monkeypatch):
    async def fake_update_database(*args, **kwargs):
        assert kwargs["group_id"] == "group-1"
        return {"kb_id": "kb-1", "group_id": "group-1"}

    monkeypatch.setattr(knowledge_router.knowledge_base, "update_database", fake_update_database)

    result = await knowledge_router.update_database_info(
        "kb-1",
        knowledge_router.UpdateDatabaseRequest(
            name="测试知识库",
            description="",
            group_id="group-1",
        ),
        current_user=SimpleNamespace(uid="admin", department_id=None),
    )

    assert result["database"]["group_id"] == "group-1"


@pytest.mark.asyncio
async def test_update_database_rejects_missing_group(monkeypatch):
    async def fake_update_database(*args, **kwargs):
        raise ValueError("知识库分组不存在")

    monkeypatch.setattr(knowledge_router.knowledge_base, "update_database", fake_update_database)

    with pytest.raises(HTTPException) as exc_info:
        await knowledge_router.update_database_info(
            "kb-1",
            knowledge_router.UpdateDatabaseRequest(
                name="测试知识库",
                description="",
                group_id="missing",
            ),
            current_user=SimpleNamespace(uid="admin", department_id=None),
        )

    assert exc_info.value.status_code == 400
    assert "分组不存在" in exc_info.value.detail


@pytest.mark.asyncio
async def test_accessible_databases_do_not_expose_group_metadata(monkeypatch):
    async def fake_get_databases_by_uid(uid):
        return {
            "databases": [
                {
                    "kb_id": "kb-1",
                    "name": "测试知识库",
                    "description": "用于智能体",
                    "created_by": "admin",
                    "group_id": "group-1",
                }
            ]
        }

    monkeypatch.setattr(knowledge_router.knowledge_base, "get_databases_by_uid", fake_get_databases_by_uid)

    result = await knowledge_router.get_accessible_databases(current_user=SimpleNamespace(uid="user-1"))

    assert result["databases"] == [
        {
            "kb_id": "kb-1",
            "name": "测试知识库",
            "description": "用于智能体",
            "created_by": "admin",
        }
    ]
