from unittest.mock import AsyncMock

import pytest

from yuxi.knowledge.manager import KnowledgeBaseManager


@pytest.mark.asyncio
async def test_create_group_rejects_missing_parent_group(monkeypatch):
    manager = KnowledgeBaseManager("test-work-dir")

    class FakeGroupRepo:
        async def ensure_default_group(self):
            return None

        async def get_by_group_id(self, group_id):
            return None

        async def name_exists(self, name):
            return False

    monkeypatch.setattr(
        "yuxi.repositories.knowledge_base_group_repository.KnowledgeBaseGroupRepository",
        FakeGroupRepo,
    )

    with pytest.raises(ValueError, match="父知识库分组不存在"):
        await manager.create_group("施工资料", parent_group_id="missing")


@pytest.mark.asyncio
async def test_delete_group_rejects_when_has_child_groups(monkeypatch):
    manager = KnowledgeBaseManager("test-work-dir")

    class FakeGroupRepo:
        async def ensure_default_group(self):
            return None

        async def get_by_group_id(self, group_id):
            return type("Group", (), {"is_default": False})()

        async def count_child_groups(self, group_id):
            return 1

        async def count_databases(self, group_id):
            return 0

        delete = AsyncMock()

    monkeypatch.setattr(
        "yuxi.repositories.knowledge_base_group_repository.KnowledgeBaseGroupRepository",
        FakeGroupRepo,
    )

    with pytest.raises(ValueError, match="子分组"):
        await manager.delete_group("group-parent")
