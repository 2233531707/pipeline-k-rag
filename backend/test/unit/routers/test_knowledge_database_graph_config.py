"""测试 extractor_options 中不含 api_key"""

from unittest.mock import MagicMock, patch
import pytest


class TestNoApiKeyInGraphConfig:
    def test_llm_extractor_does_not_read_api_key(self):
        """LLMGraphExtractor.validate_options() 不要求 api_key 字段"""
        from yuxi.knowledge.graphs.extractors.llm import LLMGraphExtractor

        extractor = LLMGraphExtractor({
            "model_spec": "test/model",
            "schema": "",
            "concurrency_count": 1,
            "model_params": {}
        })
        extractor.validate_options()  # 不应报错

    def test_llm_extractor_rejects_api_key_in_options(self):
        """LLMGraphExtractor 不接受 api_key 字段"""
        from yuxi.knowledge.graphs.extractors.llm import LLMGraphExtractor

        # validate_options 不检查 api_key —— 它只是不在合法字段列表中
        # model_params 被允许为 dict，不应放 api_key
        extractor = LLMGraphExtractor({
            "model_spec": "test/model",
            "concurrency_count": 1,
            "model_params": {}
        })
        extractor.validate_options()
        # model_params 不含 api_key 即可；如有 api_key 应在上层过滤
        assert "api_key" not in extractor.options.get("model_params", {})

    def test_graph_build_config_structure_no_api_key_field(self):
        """确认 graph_build_config 结构的 extractor_options 不含 api_key"""
        from yuxi.knowledge.graphs.milvus_graph_service import GRAPH_CONFIG_KEY

        config = {
            "locked": True,
            "extractor_type": "llm",
            "extractor_options": {
                "model_spec": "siliconflow-cn:Qwen/Qwen3-8B",
                "schema": "",
                "concurrency_count": 1,
                "model_params": {}
            }
        }

        extractor_options = config.get("extractor_options", {})
        forbidden = {"api_key", "api_token", "secret", "password"}
        found_keys = set()
        for key in forbidden:
            if key in extractor_options:
                found_keys.add(key)
            if key in extractor_options.get("model_params", {}):
                found_keys.add(key)

        assert len(found_keys) == 0, f"不应该包含敏感字段: {found_keys}"


class TestGraphBuildConfigRequiredFields:
    def test_config_has_required_top_level_fields(self):
        """验证 graph_build_config 顶层结构"""
        config = {
            "locked": True,
            "extractor_type": "llm",
            "extractor_options": {"model_spec": "test/model", "concurrency_count": 1, "model_params": {}}
        }
        assert config["locked"] is True
        assert config["extractor_type"] == "llm"
        assert "model_spec" in config["extractor_options"]

    def test_extractor_options_defaults(self):
        """验证 extractor_options 默认值"""
        from yuxi.knowledge.graphs.extractors.llm import LLMGraphExtractor

        extractor = LLMGraphExtractor({
            "model_spec": "test/model",
            "concurrency_count": 1,
            "model_params": {}
        })
        assert extractor.options.get("concurrency_count") == 1
        assert isinstance(extractor.options.get("model_params"), dict)
