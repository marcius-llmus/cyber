import uuid
from collections.abc import Sequence
from copy import deepcopy

from llama_index.core.agent.workflow.function_agent import FunctionAgent
from llama_index.core.agent.workflow.workflow_events import AgentOutput
from llama_index.core.llms import ChatMessage
from llama_index.core.memory import BaseMemory
from llama_index.core.tools import AsyncBaseTool, ToolOutput
from llama_index.core.workflow import Context


class CoderAgent(FunctionAgent):
    """
    Custom agent that injects a correlation ID (_run_id) into tool calls.
    This ensures that tool calls and their results can be reliably matched in the UI,
    even if the LLM returns duplicate tool_ids (e.g. Gemini).
    """
    # todo: just for future reference: this is a hack. that's a way to track tool exec
    #       when it starts and it finishes through an injected custom kwarg "_run_id"
    @staticmethod
    def _set_tool_run_ids(tool_calls):
        for tool_call in tool_calls:
            if "_run_id" in tool_call.tool_kwargs:
                raise ValueError("_run_id is a protected argument")
            # Inject unique run ID into kwargs
            # This persists through the tool execution and comes back in the result
            tool_call.tool_kwargs["_run_id"] = str(uuid.uuid4())

    # we do this so it is not required to pass kwargs or run_id as tool args
    @staticmethod
    def _pop_run_id_from_tool_kwargs(tool_kwargs):
        if "_run_id" not in tool_kwargs:
            raise ValueError("run_id not found in tool kwargs")
        tool_kwargs.pop("_run_id")

    async def take_step(
        self,
        ctx: Context,
        llm_input: list[ChatMessage],
        tools: Sequence[AsyncBaseTool],
        memory: BaseMemory,
    ) -> AgentOutput:
        output = await super().take_step(ctx, llm_input, tools, memory)
        self._set_tool_run_ids(output.tool_calls)
        return output

    # this is very hacky
    # hopefully, once I get rich, it will be changed
    async def _call_tool(
        self,
        ctx: Context,
        tool: AsyncBaseTool,
        tool_input: dict,
    ) -> ToolOutput:
        """Call the given tool with the given input."""
        new_tool_kwargs = deepcopy(tool_input)
        self._pop_run_id_from_tool_kwargs(new_tool_kwargs)
        return await super()._call_tool(ctx, tool, new_tool_kwargs)
