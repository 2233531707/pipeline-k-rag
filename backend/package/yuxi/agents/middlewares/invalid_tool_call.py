from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
    ResponseT,
    hook_config,
)
from langchain_core.messages import AIMessage
from langgraph.types import Overwrite

from yuxi.utils.logging_config import logger

if TYPE_CHECKING:
    from langgraph.runtime import Runtime


EMPTY_TOOL_CALL_MESSAGE = (
    "模型返回了无效的工具调用（工具名为空），本次运行已停止以避免重复调用。请切换到支持工具调用的模型后重试。"
)


def _tool_schema(tool: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(tool, dict):
        function = tool.get("function") if isinstance(tool.get("function"), dict) else tool
        name = str(function.get("name") or "")
        parameters = function.get("parameters")
        return name, parameters if isinstance(parameters, dict) else {}

    name = str(getattr(tool, "name", "") or "")
    args_schema = getattr(tool, "args_schema", None)
    if args_schema is not None and hasattr(args_schema, "model_json_schema"):
        try:
            return name, args_schema.model_json_schema()
        except Exception:
            return name, {}

    args = getattr(tool, "args", None)
    return name, {"properties": args} if isinstance(args, dict) else {}


def _infer_tool_name(tool_args: dict[str, Any], tools: list[Any]) -> str | None:
    if not tool_args:
        return None

    supplied = set(tool_args)
    candidates = []
    for tool in tools:
        name, schema = _tool_schema(tool)
        properties = schema.get("properties")
        if not name or not isinstance(properties, dict) or not supplied.issubset(properties):
            continue
        required = schema.get("required") or []
        if isinstance(required, list) and set(required).issubset(supplied):
            candidates.append(name)

    return candidates[0] if len(candidates) == 1 else None


def _repair_empty_tool_names(response: ModelResponse | AIMessage, tools: list[Any]) -> ModelResponse | AIMessage:
    messages = response.result if isinstance(response, ModelResponse) else [response]
    repaired_messages = []
    changed = False

    for message in messages:
        if not isinstance(message, AIMessage):
            repaired_messages.append(message)
            continue

        repaired_calls = []
        for call in message.tool_calls:
            if str(call.get("name") or "").strip():
                repaired_calls.append(call)
                continue

            inferred_name = _infer_tool_name(call.get("args") or {}, tools)
            if not inferred_name:
                repaired_calls.append(call)
                continue

            repaired_calls.append({**call, "name": inferred_name})
            changed = True
            logger.warning(f"Recovered empty tool call name as '{inferred_name}' from its arguments")

        repaired_messages.append(message.model_copy(update={"tool_calls": repaired_calls}))

    if not changed:
        return response
    if isinstance(response, ModelResponse):
        return ModelResponse(result=repaired_messages, structured_response=response.structured_response)
    return repaired_messages[0]


class InvalidToolCallMiddleware(AgentMiddleware):
    """Recover uniquely identifiable empty tool names, otherwise stop the run."""

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT] | AIMessage:
        response = handler(request)
        return _repair_empty_tool_names(response, request.tools)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse[ResponseT]]],
    ) -> ModelResponse[ResponseT] | AIMessage:
        response = await handler(request)
        return _repair_empty_tool_names(response, request.tools)

    @hook_config(can_jump_to=["end"])
    def after_model(self, state: AgentState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        del runtime
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        if not isinstance(last_message, AIMessage):
            return None

        invalid_calls = [call for call in last_message.tool_calls if not str(call.get("name") or "").strip()]
        if not invalid_calls:
            return None

        return {
            "jump_to": "end",
            "messages": Overwrite([*messages[:-1], AIMessage(content=EMPTY_TOOL_CALL_MESSAGE)]),
        }

    @hook_config(can_jump_to=["end"])
    async def aafter_model(self, state: AgentState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        return self.after_model(state, runtime)
