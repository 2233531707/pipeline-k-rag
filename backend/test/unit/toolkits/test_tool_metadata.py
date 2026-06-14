from yuxi.agents.toolkits.service import get_tool_metadata


def test_runtime_knowledge_tools_are_visible_in_tool_metadata():
    tools = {item["slug"]: item for item in get_tool_metadata()}

    assert tools["query_knowledge_graph"]["category"] == "knowledge"
    assert tools["list_spatial_layers"]["category"] == "knowledge"
    assert tools["query_spatial_features"]["category"] == "knowledge"
    assert tools["show_spatial_map"]["category"] == "knowledge"
