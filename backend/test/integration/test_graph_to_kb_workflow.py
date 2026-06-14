"""显式图谱查询提示到知识库增强检索的链路测试。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from yuxi.agents.toolkits.kbs import graph_tools, tools

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _invoke(tool, **kwargs):
    callback = tool.coroutine or tool.func
    return await callback(**kwargs)


async def test_graph_hints_are_forwarded_to_kb_retriever(monkeypatch):
    runtime = SimpleNamespace(
        context=SimpleNamespace(
            _visible_knowledge_bases=[
                {"kb_id": "kb-graph", "name": "管网知识库", "kb_type": "milvus"}
            ]
        )
    )
    graph_service = SimpleNamespace(
        query_nodes=AsyncMock(
            return_value={
                "nodes": [
                    {
                        "id": "node-1",
                        "type": "Entity",
                        "name": "供水管道",
                        "properties": {"entity_id": "entity-pipe"},
                    }
                ],
                "edges": [],
            }
        )
    )
    from yuxi.knowledge.graphs import milvus_graph_service

    monkeypatch.setattr(milvus_graph_service, "MilvusGraphService", lambda **_kwargs: graph_service)

    received_kwargs = {}

    async def retriever(query_text, **kwargs):
        received_kwargs.update(kwargs)
        return [{"content": "管道巡检规范", "metadata": {"file_id": "file-1"}}]

    monkeypatch.setattr(
        tools.knowledge_base,
        "get_retrievers",
        lambda: {
            "kb-graph": {
                "name": "管网知识库",
                "metadata": {"kb_type": "milvus"},
                "retriever": retriever,
            }
        },
    )

    graph_result = await _invoke(
        graph_tools.query_knowledge_graph,
        kb_id="kb-graph",
        keyword="供水管道",
        max_depth=1,
        max_nodes=50,
        exclude_chunk=True,
        runtime=runtime,
    )
    kb_result = await _invoke(
        tools.query_kb,
        kb_id="kb-graph",
        query_text="如何巡检供水管道",
        graph_entity_ids=graph_result["retrieval_hints"]["graph_entity_ids"],
        runtime=runtime,
    )

    assert received_kwargs["graph_entity_ids"] == ["entity-pipe"]
    assert kb_result["results"][0]["content"] == "管道巡检规范"
