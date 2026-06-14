from __future__ import annotations

from types import SimpleNamespace

import pytest

from yuxi.agents import base as base_module
from yuxi.agents.context import BaseContext


@pytest.mark.asyncio
async def test_get_info_resolves_knowledge_tool_options(monkeypatch):
    captured_fields = set()

    async def fake_resolve(resource_fields, *, db, user):
        assert db is not None
        assert user is not None
        captured_fields.update(resource_fields)
        return {
            "knowledge_tools": [
                {
                    "key": "query_knowledge_graph",
                    "name": "查询知识图谱",
                    "description": "",
                }
            ]
        }

    monkeypatch.setattr(base_module, "resolve_agent_resource_options", fake_resolve)

    agent = object.__new__(base_module.BaseAgent)
    agent.context_schema = BaseContext
    agent.load_metadata = lambda: {}

    info = await agent.get_info(
        include_configurable_items=True,
        user_role="superadmin",
        db=object(),
        user=SimpleNamespace(),
    )

    assert "knowledge_tools" in captured_fields
    assert info["configurable_items"]["knowledge_tools"]["options"] == [
        {
            "key": "query_knowledge_graph",
            "name": "查询知识图谱",
            "description": "",
        }
    ]
