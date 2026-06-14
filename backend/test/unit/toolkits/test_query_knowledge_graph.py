"""测试显式知识图谱查询工具 query_knowledge_graph"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from yuxi.agents.toolkits.kbs.graph_tools import (
    QueryKnowledgeGraphInput,
    _extract_retrieval_hints,
    query_knowledge_graph,
)


def _graph_tool_callable():
    """LangChain @tool 装饰器返回 StructuredTool 对象，需要通过 coroutine/func 获取原始函数"""
    callback = getattr(query_knowledge_graph, "coroutine", None)
    if callback is not None:
        return callback
    callback = getattr(query_knowledge_graph, "func", None)
    if callback is not None:
        return callback
    raise AssertionError("query_knowledge_graph tool has no callable entry")


async def _run_graph_query(**kwargs):
    callback = _graph_tool_callable()
    result = callback(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


class TestQueryKnowledgeGraphInput:
    def test_default_values(self):
        schema = QueryKnowledgeGraphInput(kb_id="kb-1", keyword="test")
        assert schema.kb_id == "kb-1"
        assert schema.keyword == "test"
        assert schema.max_depth == 1
        assert schema.max_nodes == 50
        assert schema.exclude_chunk is True

    def test_custom_values(self):
        schema = QueryKnowledgeGraphInput(
            kb_id="kb-x",
            keyword="管道漏损",
            max_depth=2,
            max_nodes=100,
            exclude_chunk=False,
        )
        assert schema.max_depth == 2
        assert schema.max_nodes == 100
        assert schema.exclude_chunk is False

    def test_empty_keyword_allowed_by_schema(self):
        """Schema 不验证业务规则，空关键词由函数逻辑处理"""
        schema = QueryKnowledgeGraphInput(kb_id="kb-1", keyword="")
        assert schema.keyword == ""


class TestExtractRetrievalHints:
    def test_empty_nodes_and_edges(self):
        hints = _extract_retrieval_hints([], [], "test")
        assert hints["graph_entity_ids"] == []
        assert hints["chunk_ids"] == []
        assert hints["file_ids"] == []
        assert "test" in hints["keywords"]

    def test_extracts_entity_ids_from_nodes(self):
        nodes = [
            {
                "id": "n1",
                "type": "Person",
                "name": "张三",
                "properties": {"entity_id": "ent_001"},
            },
            {
                "id": "n2",
                "type": "Organization",
                "name": "公司A",
                "properties": {"entity_id": "ent_002"},
            },
        ]
        hints = _extract_retrieval_hints(nodes, [], "张三 公司")
        assert hints["graph_entity_ids"] == ["ent_001", "ent_002"]
        assert "张三" in hints["keywords"]

    def test_extracts_chunk_ids_from_chunk_nodes(self):
        nodes = [
            {
                "id": "c1",
                "type": "Chunk",
                "name": "chunk-1",
                "properties": {"chunk_id": "chunk_001", "file_id": "file_a"},
            },
        ]
        hints = _extract_retrieval_hints(nodes, [], "test")
        assert hints["chunk_ids"] == ["chunk_001"]
        assert hints["file_ids"] == ["file_a"]

    def test_extracts_from_edges(self):
        edges = [
            {
                "id": "e1",
                "source_id": "n1",
                "target_id": "n2",
                "type": "RELATED_TO",
                "properties": {"chunk_id": "chunk_from_edge"},
            },
        ]
        hints = _extract_retrieval_hints([], edges, "test")
        assert "chunk_from_edge" in hints["chunk_ids"]

    def test_deduplicates_hints(self):
        nodes = [
            {"id": "n1", "type": "Entity", "name": "A", "properties": {"entity_id": "ent_001"}},
            {"id": "n2", "type": "Entity", "name": "B", "properties": {"entity_id": "ent_001"}},
        ]
        hints = _extract_retrieval_hints(nodes, [], "test")
        assert hints["graph_entity_ids"] == ["ent_001"]

    def test_keyword_split(self):
        hints = _extract_retrieval_hints([], [], "供水，管道,漏损、检测")
        assert "供水" in hints["keywords"]
        assert "管道" in hints["keywords"]
        assert "漏损" in hints["keywords"]
        assert "检测" in hints["keywords"]


class TestQueryKnowledgeGraph:
    def _make_visible_kbs(self, kb_id="kb-graph", kb_type="milvus"):
        return [{"kb_id": kb_id, "name": "测试知识库", "kb_type": kb_type}]

    def _make_runtime(self, visible_kbs=None):
        context = SimpleNamespace(_visible_knowledge_bases=visible_kbs or self._make_visible_kbs())
        return SimpleNamespace(context=context)

    @pytest.mark.asyncio
    async def test_missing_kb_id(self):
        result = await _run_graph_query(kb_id="", keyword="test", runtime=None)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_empty_keyword(self):
        runtime = self._make_runtime()
        result = await _run_graph_query(kb_id="kb-graph", keyword="", runtime=runtime)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_no_visible_kbs(self):
        runtime = SimpleNamespace(context=SimpleNamespace(_visible_knowledge_bases=[]))
        result = await _run_graph_query(kb_id="kb-graph", keyword="test", runtime=runtime)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_kb_not_in_visible_list(self):
        runtime = self._make_runtime(visible_kbs=[{"kb_id": "other-kb", "name": "其他", "kb_type": "milvus"}])
        result = await _run_graph_query(kb_id="kb-graph", keyword="test", runtime=runtime)
        assert "error" in result
        assert "不存在" in result["error"] or "未启用" in result["error"]

    @pytest.mark.asyncio
    async def test_non_milvus_kb_rejected(self):
        runtime = self._make_runtime(visible_kbs=[{"kb_id": "kb-dify", "name": "Dify库", "kb_type": "dify"}])
        result = await _run_graph_query(kb_id="kb-dify", keyword="test", runtime=runtime)
        assert "error" in result
        assert "不支持图谱" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_graph_result(self):
        runtime = self._make_runtime()

        with patch(
            "yuxi.knowledge.graphs.milvus_graph_service.MilvusGraphService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.query_nodes = AsyncMock(return_value={"nodes": [], "edges": []})
            mock_svc_cls.return_value = mock_svc

            result = await _run_graph_query(kb_id="kb-graph", keyword="test", runtime=runtime)

        assert result["kb_id"] == "kb-graph"
        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["retrieval_hints"]["graph_entity_ids"] == []

    @pytest.mark.asyncio
    async def test_graph_with_nodes_and_edges(self):
        runtime = self._make_runtime()
        nodes = [
            {"id": "n1", "type": "Entity", "name": "张三", "properties": {"entity_id": "ent_1"}},
        ]
        edges = [
            {"id": "e1", "source_id": "n1", "target_id": "n2", "type": "WORKS_AT", "properties": {}},
        ]

        with patch(
            "yuxi.knowledge.graphs.milvus_graph_service.MilvusGraphService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.query_nodes = AsyncMock(return_value={"nodes": nodes, "edges": edges})
            mock_svc_cls.return_value = mock_svc

            result = await _run_graph_query(kb_id="kb-graph", keyword="张三", runtime=runtime)

        assert result["kb_id"] == "kb-graph"
        assert result["query"] == "张三"
        assert len(result["nodes"]) == 1
        assert len(result["edges"]) == 1
        assert "ent_1" in result["retrieval_hints"]["graph_entity_ids"]

    @pytest.mark.asyncio
    async def test_graph_service_exception(self):
        runtime = self._make_runtime()

        with patch(
            "yuxi.knowledge.graphs.milvus_graph_service.MilvusGraphService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.query_nodes = AsyncMock(side_effect=RuntimeError("Neo4j 连接失败"))
            mock_svc_cls.return_value = mock_svc

            result = await _run_graph_query(kb_id="kb-graph", keyword="test", runtime=runtime)

        assert "error" in result
        assert "图谱查询失败" in result["error"]

    @pytest.mark.asyncio
    async def test_session_not_enabled_kb_filtered(self):
        """知识库存在但未在当前会话中启用"""
        runtime = self._make_runtime(visible_kbs=[{"kb_id": "kb-disabled", "name": "未启用", "kb_type": "milvus"}])
        result = await _run_graph_query(kb_id="kb-graph", keyword="test", runtime=runtime)
        assert "error" in result
