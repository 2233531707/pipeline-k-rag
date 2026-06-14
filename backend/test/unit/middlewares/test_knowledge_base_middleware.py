from yuxi.agents.middlewares.knowledge_base import KnowledgeBaseMiddleware


def test_knowledge_base_middleware_defaults_to_all_tools():
    middleware = KnowledgeBaseMiddleware()

    assert "query_knowledge_graph" in {tool.name for tool in middleware.tools}
    assert "show_spatial_map" in {tool.name for tool in middleware.tools}


def test_knowledge_base_middleware_uses_explicit_selection():
    middleware = KnowledgeBaseMiddleware(["query_knowledge_graph", "show_spatial_map"])

    assert [tool.name for tool in middleware.tools] == ["query_knowledge_graph", "show_spatial_map"]


def test_knowledge_base_middleware_allows_disabling_all_tools():
    middleware = KnowledgeBaseMiddleware([])

    assert middleware.tools == []
