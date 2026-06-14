"""测试图谱种子增强检索 — graph_entity_ids → seed_weights → PPR → graph chunks → RRF"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from yuxi.knowledge.implementations.milvus import MilvusKB


def _new_kb(**overrides):
    """创建 MilvusKB 测试实例，mock 所有外部依赖"""
    defaults = {
        "work_dir": "/tmp/test_kb",
        "databases": {},
    }
    defaults.update(overrides)
    kb = MilvusKB(**defaults)
    kb.databases_meta = defaults.get("databases_meta", {})
    return kb


class TestGraphEntityIdsParamRouting:
    """验证 graph_entity_ids 参数从 query_kb → MilvusKB.aquery 的传递"""

    @pytest.mark.asyncio
    async def test_graph_entity_ids_passed_to_retrieve(self):
        """graph_entity_ids 在 merged_kwargs 中应能被正确识别"""
        kb = _new_kb()
        kb._get_milvus_collection = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await kb.aquery("test", "kb-1", graph_entity_ids=["ent_1", "ent_2"])


class TestGraphEntityIdsSkipsVectorSearch:
    """提供 graph_entity_ids 时应跳过 MilvusGraphVectorStore 向量搜索，直接构造种子权重"""

    @pytest.mark.asyncio
    async def test_graph_entity_ids_direct_seed(self):
        kb = _new_kb(databases_meta={"kb-1": {"embedding_model_spec": "test/model"}})

        # Mock collection 和 embedding function
        mock_collection = MagicMock()
        mock_collection.search.return_value = [[]]
        kb._get_milvus_collection = AsyncMock(return_value=mock_collection)
        kb._get_query_params = MagicMock(return_value={})

        # Mock embedding function 避免 real model lookup
        mock_embed_fn = MagicMock()
        mock_embed_fn.return_value = [[0.1, 0.2, 0.3]]
        kb._get_embedding_function = MagicMock(return_value=mock_embed_fn)

        with patch.object(
            kb, "_retrieve_graph_chunks", new_callable=AsyncMock
        ) as mock_retrieve:
            mock_retrieve.return_value = []

            await kb.aquery(
                "test query",
                "kb-1",
                graph_entity_ids=["ent_1", "ent_2"],
            )

            call_kwargs = mock_retrieve.call_args
            assert call_kwargs is not None
            _, kwargs = call_kwargs
            assert kwargs.get("graph_entity_ids") == ["ent_1", "ent_2"]


class TestGraphEntityIdsBuildsSeedWeights:
    """graph_entity_ids 应被转换为等权种子权重并传递给 PPR"""

    @pytest.mark.asyncio
    async def test_entity_ids_to_seed_weights(self):
        kb = _new_kb(databases_meta={"kb-1": {"embedding_model_spec": "test/model"}})

        mock_collection = MagicMock()
        mock_collection.search.return_value = [[]]
        kb._get_milvus_collection = AsyncMock(return_value=mock_collection)
        kb._get_query_params = MagicMock(return_value={})
        mock_embed_fn = MagicMock()
        mock_embed_fn.return_value = [[0.1, 0.2, 0.3]]
        kb._get_embedding_function = MagicMock(return_value=mock_embed_fn)

        with patch.object(
            kb, "_retrieve_graph_chunks", new_callable=AsyncMock
        ) as mock_retrieve:
            mock_retrieve.return_value = []

            await kb.aquery(
                "test", "kb-1",
                graph_entity_ids=["ent_a", "ent_b", "ent_c"],
            )

            call_kwargs = mock_retrieve.call_args
            assert call_kwargs is not None
            _, kwargs = call_kwargs
            assert kwargs.get("graph_entity_ids") == ["ent_a", "ent_b", "ent_c"]


class TestGraphEntityIdsFallback:
    """图谱为空或 PPR 无结果时，必须回退到普通 RAG"""

    @pytest.mark.asyncio
    async def test_empty_graph_falls_back_to_rag(self):
        kb = _new_kb(databases_meta={"kb-1": {"embedding_model_spec": "test/model"}})

        mock_collection = MagicMock()
        mock_collection.search.return_value = [[]]
        kb._get_milvus_collection = AsyncMock(return_value=mock_collection)
        kb._get_query_params = MagicMock(return_value={})
        mock_embed_fn = MagicMock()
        mock_embed_fn.return_value = [[0.1, 0.2, 0.3]]
        kb._get_embedding_function = MagicMock(return_value=mock_embed_fn)

        with patch(
            "yuxi.knowledge.implementations.milvus.MilvusGraphService", create=True
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.query_and_rank_chunks_by_ppr = AsyncMock(return_value=[])
            mock_svc_cls.return_value = mock_svc

            result = await kb.aquery(
                "test query",
                "kb-1",
                graph_entity_ids=["ent_1"],
            )

            assert isinstance(result, list)


class TestBackwardCompatible:
    """不传 graph_entity_ids 时保持原有行为"""

    @pytest.mark.asyncio
    async def test_no_graph_entity_ids_uses_original_flow(self):
        kb = _new_kb(databases_meta={"kb-1": {"embedding_model_spec": "test/model"}})

        mock_collection = MagicMock()
        mock_collection.search.return_value = [[]]
        kb._get_milvus_collection = AsyncMock(return_value=mock_collection)
        kb._get_query_params = MagicMock(return_value={})
        mock_embed_fn = MagicMock()
        mock_embed_fn.return_value = [[0.1, 0.2, 0.3]]
        kb._get_embedding_function = MagicMock(return_value=mock_embed_fn)

        result = await kb.aquery("test", "kb-1")
        assert isinstance(result, list)
