from yuxi.agents.buildin.chatbot.prompt import build_prompt_with_context


class _Context:
    system_prompt = ""


def test_build_prompt_with_context_prioritizes_spatial_tools_for_map_requests() -> None:
    prompt = build_prompt_with_context(_Context())

    assert "优先使用知识库空间工具" in prompt
    assert "先调用 list_spatial_layers" in prompt
    assert "优先调用 show_spatial_map" in prompt
    assert "不要先去文件系统" in prompt
