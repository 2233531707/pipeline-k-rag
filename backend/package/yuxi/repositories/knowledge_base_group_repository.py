from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, update

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_knowledge import KnowledgeBase, KnowledgeBaseGroup

DEFAULT_KNOWLEDGE_BASE_GROUP_ID = "default"
DEFAULT_KNOWLEDGE_BASE_GROUP_NAME = "默认分组"


class KnowledgeBaseGroupRepository:
    async def ensure_default_group(self) -> KnowledgeBaseGroup:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(KnowledgeBaseGroup).where(KnowledgeBaseGroup.group_id == DEFAULT_KNOWLEDGE_BASE_GROUP_ID)
            )
            group = result.scalar_one_or_none()
            if group is None:
                group = KnowledgeBaseGroup(
                    group_id=DEFAULT_KNOWLEDGE_BASE_GROUP_ID,
                    name=DEFAULT_KNOWLEDGE_BASE_GROUP_NAME,
                    is_default=True,
                )
                session.add(group)
                await session.flush()
            await session.execute(
                update(KnowledgeBase)
                .where(KnowledgeBase.group_id.is_(None))
                .values(group_id=DEFAULT_KNOWLEDGE_BASE_GROUP_ID)
            )
            return group

    async def get_all(self) -> list[KnowledgeBaseGroup]:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(KnowledgeBaseGroup).order_by(KnowledgeBaseGroup.is_default.desc(), KnowledgeBaseGroup.created_at)
            )
            return list(result.scalars().all())

    async def name_exists(self, name: str) -> bool:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(KnowledgeBaseGroup).where(func.lower(KnowledgeBaseGroup.name) == name.lower())
            )
            return result.scalar_one_or_none() is not None

    async def get_by_name(self, name: str) -> KnowledgeBaseGroup | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(KnowledgeBaseGroup).where(func.lower(KnowledgeBaseGroup.name) == name.lower())
            )
            return result.scalar_one_or_none()

    async def get_by_group_id(self, group_id: str) -> KnowledgeBaseGroup | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(KnowledgeBaseGroup).where(KnowledgeBaseGroup.group_id == group_id))
            return result.scalar_one_or_none()

    async def count_databases(self, group_id: str) -> int:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(func.count()).select_from(KnowledgeBase).where(KnowledgeBase.group_id == group_id)
            )
            return int(result.scalar() or 0)

    async def count_child_groups(self, group_id: str) -> int:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(func.count())
                .select_from(KnowledgeBaseGroup)
                .where(KnowledgeBaseGroup.parent_group_id == group_id)
            )
            return int(result.scalar() or 0)

    async def create(self, data: dict[str, Any]) -> KnowledgeBaseGroup:
        data.setdefault("group_id", f"group_{uuid.uuid4().hex[:12]}")
        group = KnowledgeBaseGroup(**data)
        async with pg_manager.get_async_session_context() as session:
            session.add(group)
        return group

    async def update_name(self, group_id: str, name: str) -> KnowledgeBaseGroup | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(KnowledgeBaseGroup).where(KnowledgeBaseGroup.group_id == group_id))
            group = result.scalar_one_or_none()
            if group is None:
                return None
            group.name = name
            return group

    async def is_descendant(self, group_id: str, ancestor_group_id: str) -> bool:
        if group_id == ancestor_group_id:
            return True
        current = await self.get_by_group_id(group_id)
        visited = set()
        while current and current.parent_group_id and current.parent_group_id not in visited:
            if current.parent_group_id == ancestor_group_id:
                return True
            visited.add(current.parent_group_id)
            current = await self.get_by_group_id(current.parent_group_id)
        return False

    async def delete(self, group_id: str) -> None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(KnowledgeBaseGroup).where(KnowledgeBaseGroup.group_id == group_id))
            group = result.scalar_one_or_none()
            if group is not None:
                await session.delete(group)
