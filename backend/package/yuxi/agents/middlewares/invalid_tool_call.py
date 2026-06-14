from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain.agents.middleware.types import AgentMiddleware, AgentState, hook_config
from langchain_core.messages import AIMessage
from langgraph.types import Overwrite

if TYPE_CHECKING:
    from langgraph.runtime import Runtime


EMPTY_TOOL_CALL_MESSAGE = (
    "模型返回了无效的工具调用（工具名为空），本次运行已停止以避免重复调用。"
    "请切换到支持工具调用的模型后重试。"
)


class InvalidToolCallMiddleware(AgentMiddleware):
    """Stop an agent run when the model returns a tool call without a name."""

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
