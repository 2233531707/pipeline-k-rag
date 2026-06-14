from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Overwrite

from yuxi.agents.middlewares.invalid_tool_call import (
    EMPTY_TOOL_CALL_MESSAGE,
    InvalidToolCallMiddleware,
)


@pytest.mark.asyncio
async def test_empty_tool_name_stops_run_without_retry_loop():
    middleware = InvalidToolCallMiddleware()
    state = {
        "messages": [
            HumanMessage(content="查询知识图谱"),
            AIMessage(
                content="",
                tool_calls=[{"name": "", "args": {}, "id": "call-empty", "type": "tool_call"}],
            ),
        ]
    }

    result = await middleware.aafter_model(state, SimpleNamespace())

    assert result["jump_to"] == "end"
    assert isinstance(result["messages"], Overwrite)
    assert result["messages"].value[-1].content == EMPTY_TOOL_CALL_MESSAGE
    assert result["messages"].value[-1].tool_calls == []


@pytest.mark.asyncio
async def test_valid_tool_name_continues_run():
    middleware = InvalidToolCallMiddleware()
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "query_knowledge_graph",
                        "args": {"kb_id": "kb-1", "keyword": "供水"},
                        "id": "call-valid",
                        "type": "tool_call",
                    }
                ],
            )
        ]
    }

    assert await middleware.aafter_model(state, SimpleNamespace()) is None
