from types import SimpleNamespace

import pytest
from langchain.agents.middleware.types import ModelResponse
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Overwrite

from yuxi.agents.middlewares.invalid_tool_call import (
    EMPTY_TOOL_CALL_MESSAGE,
    InvalidToolCallMiddleware,
)
from yuxi.agents.toolkits.kbs.graph_tools import query_knowledge_graph
from yuxi.agents.toolkits.kbs.tools import list_kbs


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


@pytest.mark.asyncio
async def test_empty_tool_name_is_recovered_when_arguments_match_one_tool():
    middleware = InvalidToolCallMiddleware()

    class UninspectableSchema:
        @classmethod
        def model_json_schema(cls):
            raise ValueError("unsupported callable")

    uninspectable_tool = SimpleNamespace(name="task", args_schema=UninspectableSchema)
    request = SimpleNamespace(tools=[uninspectable_tool, list_kbs, query_knowledge_graph])
    response = ModelResponse(
        result=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "",
                        "args": {"kb_id": "1", "keyword": "*", "max_nodes": 20},
                        "id": "call-empty",
                        "type": "tool_call",
                    }
                ],
            )
        ]
    )

    async def handler(_request):
        return response

    repaired = await middleware.awrap_model_call(request, handler)

    assert repaired.result[-1].tool_calls[0]["name"] == "query_knowledge_graph"
    assert await middleware.aafter_model({"messages": repaired.result}, SimpleNamespace()) is None
