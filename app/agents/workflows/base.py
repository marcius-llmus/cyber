import inspect
import uuid
import warnings
from collections.abc import Sequence
from typing import Any, cast

from llama_index.core.agent.utils import generate_structured_response
from llama_index.core.agent.workflow.base_agent import (
    DEFAULT_MAX_ITERATIONS,
    BaseWorkflowAgent,
)
from llama_index.core.agent.workflow.workflow_events import (
    AgentInput,
    AgentOutput,
    AgentStream,
    AgentStreamStructuredOutput,
)
from llama_index.core.base.llms.types import ChatResponse
from llama_index.core.bridge.pydantic import BaseModel, Field
from llama_index.core.llms import ChatMessage
from llama_index.core.llms.llm import ToolSelection
from llama_index.core.memory import BaseMemory
from llama_index.core.tools import AsyncBaseTool, ToolOutput
from llama_index.core.workflow import Context
from workflows import step
from workflows.errors import WorkflowRuntimeError
from workflows.events import StopEvent

from app.agents.workflows.workflow_events import ToolCall, ToolCallResult


class CustomFunctionAgent(BaseWorkflowAgent):
    """Function calling agent implementation."""

    scratchpad_key: str = "scratchpad"
    initial_tool_choice: str | None = Field(
        default=None,
        description="The tool to try and force to call on the first iteration of the agent.",
    )
    allow_parallel_tool_calls: bool = Field(
        default=True,
        description="If True, the agent will call multiple tools in parallel. If False, the agent will call tools sequentially.",
    )

    @step
    async def call_tool(self, ctx: Context, ev: ToolCall) -> ToolCallResult:
        """Calls the tool and handles the result."""
        ctx.write_event_to_stream(
            ToolCall(
                tool_name=ev.tool_name,
                tool_kwargs=ev.tool_kwargs,
                tool_id=ev.tool_id,
                internal_tool_call_id=ev.internal_tool_call_id,
            )
        )

        tools = await self.get_tools(ev.tool_name)
        tools_by_name = {tool.metadata.name: tool for tool in tools}
        if ev.tool_name not in tools_by_name:
            tool = None
            result = ToolOutput(
                content=f"Tool {ev.tool_name} not found. Please select a tool that is available.",
                tool_name=ev.tool_name,
                raw_input=ev.tool_kwargs,
                raw_output=None,
                is_error=True,
            )
        else:
            tool = tools_by_name[ev.tool_name]
            result = await self._call_tool(ctx, tool, ev.tool_kwargs)

        result_ev = ToolCallResult(
            tool_name=ev.tool_name,
            tool_kwargs=ev.tool_kwargs,
            tool_id=ev.tool_id,
            internal_tool_call_id=ev.internal_tool_call_id,
            tool_output=result,
            return_direct=tool.metadata.return_direct if tool else False,
        )

        ctx.write_event_to_stream(result_ev)
        return result_ev

    @step
    async def aggregate_tool_results(
        self, ctx: Context, ev: ToolCallResult
    ) -> AgentInput | StopEvent | None:
        """Aggregate tool results and return the next agent input."""
        num_tool_calls = await ctx.store.get("num_tool_calls", default=0)
        if num_tool_calls == 0:
            raise ValueError("No tool calls found, cannot aggregate results.")

        tool_call_results: list[ToolCallResult] = ctx.collect_events(  # type: ignore
            ev, expected=[ToolCallResult] * num_tool_calls
        )
        if not tool_call_results:
            return None

        memory: BaseMemory = await ctx.store.get("memory")

        # track tool calls made during a .run() call
        cur_tool_calls: list[ToolCallResult] = await ctx.store.get(
            "current_tool_calls", default=[]
        )
        cur_tool_calls.extend(tool_call_results)
        await ctx.store.set("current_tool_calls", cur_tool_calls)

        await self.handle_tool_call_results(ctx, tool_call_results, memory)

        if any(
            tool_call_result.return_direct and not tool_call_result.tool_output.is_error
            for tool_call_result in tool_call_results
        ):
            # if any tool calls return directly and it's not an error tool call, take the first one
            return_direct_tool = next(
                tool_call_result
                for tool_call_result in tool_call_results
                if tool_call_result.return_direct
                and not tool_call_result.tool_output.is_error
            )

            # always finalize the agent, even if we're just handing off
            result = AgentOutput(
                response=ChatMessage(
                    role="assistant",
                    content=return_direct_tool.tool_output.content or "",
                ),
                tool_calls=[
                    ToolSelection(
                        tool_id=t.tool_id,
                        tool_name=t.tool_name,
                        tool_kwargs=t.tool_kwargs,
                    )
                    for t in cur_tool_calls
                ],
                raw=return_direct_tool.tool_output.raw_output,
                current_agent_name=self.name,
            )
            result = await self.finalize(ctx, result, memory)
            # we don't want to stop the system if we're just handing off
            if return_direct_tool.tool_name != "handoff":
                await ctx.store.set("current_tool_calls", [])
                return StopEvent(result=result)

        user_msg_str = await ctx.store.get("user_msg_str")
        input_messages = await memory.aget(input=user_msg_str)

        return AgentInput(input=input_messages, current_agent_name=self.name)

    async def _get_response(
        self, current_llm_input: list[ChatMessage], tools: Sequence[AsyncBaseTool]
    ) -> ChatResponse:
        chat_kwargs = {
            "chat_history": current_llm_input,
            "allow_parallel_tool_calls": self.allow_parallel_tool_calls,
            "tools": tools,
        }

        # Only add tool choice if set and if its the first response
        if (
            self.initial_tool_choice is not None
            and current_llm_input[-1].role == "user"
        ):
            chat_kwargs["tool_choice"] = self.initial_tool_choice  # noqa

        return await self.llm.achat_with_tools(**chat_kwargs)  # type: ignore

    @step
    async def parse_agent_output(
        self, ctx: Context, ev: AgentOutput
    ) -> StopEvent | AgentInput | ToolCall | None:
        max_iterations = await ctx.store.get(
            "max_iterations", default=DEFAULT_MAX_ITERATIONS
        )
        num_iterations = await ctx.store.get("num_iterations", default=0)
        num_iterations += 1
        await ctx.store.set("num_iterations", num_iterations)

        if num_iterations >= max_iterations:
            raise WorkflowRuntimeError(
                f"Max iterations of {max_iterations} reached! Either something went wrong, or you can "
                "increase the max iterations with `.run(.., max_iterations=...)`"
            )

        memory: BaseMemory = await ctx.store.get("memory")

        if ev.retry_messages:
            # Retry with the given messages to let the LLM fix potential errors
            history = await memory.aget()
            user_msg_str = await ctx.store.get("user_msg_str")

            return AgentInput(
                input=[
                    *history,
                    ChatMessage(role="user", content=user_msg_str),
                    *ev.retry_messages,
                ],
                current_agent_name=self.name,
            )

        if not ev.tool_calls:
            # important: messages should always be fetched after calling finalize, otherwise they do not contain the agent's response
            output = await self.finalize(ctx, ev, memory)
            messages = await memory.aget()
            cur_tool_calls: list[ToolCallResult] = await ctx.store.get(
                "current_tool_calls", default=[]
            )
            output.tool_calls.extend(cur_tool_calls)  # type: ignore

            if self.structured_output_fn is not None:
                try:
                    if inspect.iscoroutinefunction(self.structured_output_fn):
                        output.structured_response = await self.structured_output_fn(
                            messages
                        )
                    else:
                        output.structured_response = cast(
                            dict[str, Any], self.structured_output_fn(messages)
                        )
                    ctx.write_event_to_stream(
                        AgentStreamStructuredOutput(output=output.structured_response)
                    )
                except Exception as e:
                    warnings.warn(  # noqa
                        f"There was a problem with the generation of the structured output: {e}"
                    )
            if self.output_cls is not None:
                try:
                    llm_input = [*messages]
                    if self.system_prompt:
                        llm_input = [
                            ChatMessage(role="system", content=self.system_prompt),
                            *llm_input,
                        ]
                    output.structured_response = await generate_structured_response(
                        messages=llm_input, llm=self.llm, output_cls=self.output_cls
                    )
                    ctx.write_event_to_stream(
                        AgentStreamStructuredOutput(output=output.structured_response)
                    )
                except Exception as e:
                    warnings.warn(  # noqa
                        f"There was a problem with the generation of the structured output: {e}"
                    )

            await ctx.store.set("current_tool_calls", [])

            return StopEvent(result=output)

        await ctx.store.set("num_tool_calls", len(ev.tool_calls))

        for tool_call in ev.tool_calls:
            ctx.send_event(
                ToolCall(
                    tool_name=tool_call.tool_name,
                    tool_kwargs=tool_call.tool_kwargs,
                    tool_id=tool_call.tool_id,
                    internal_tool_call_id=str(  # this is our internal version
                        uuid.uuid4()
                    ),
                )
            )

        return None

    async def _get_streaming_response(
        self,
        ctx: Context,
        current_llm_input: list[ChatMessage],
        tools: Sequence[AsyncBaseTool],
    ) -> ChatResponse:
        chat_kwargs = {
            "chat_history": current_llm_input,
            "tools": tools,
            "allow_parallel_tool_calls": self.allow_parallel_tool_calls,
        }

        # Only add tool choice if set and if its the first response
        if (
            self.initial_tool_choice is not None
            and current_llm_input[-1].role == "user"
        ):
            chat_kwargs["tool_choice"] = self.initial_tool_choice  # noqa

        response = await self.llm.astream_chat_with_tools(**chat_kwargs)  # type: ignore
        # last_chat_response will be used later, after the loop.
        # We initialize it so it's valid even when 'response' is empty
        last_chat_response = ChatResponse(message=ChatMessage())
        async for last_chat_response in response:
            tool_calls = self.llm.get_tool_calls_from_response(  # type: ignore
                last_chat_response, error_on_no_tool_call=False
            )
            raw = (
                last_chat_response.raw.model_dump()
                if isinstance(last_chat_response.raw, BaseModel)
                else last_chat_response.raw
            )
            ctx.write_event_to_stream(
                AgentStream(
                    delta=last_chat_response.delta or "",
                    response=last_chat_response.message.content or "",
                    tool_calls=tool_calls or [],
                    raw=raw,
                    current_agent_name=self.name,
                    thinking_delta=last_chat_response.additional_kwargs.get(
                        "thinking_delta", None
                    ),
                )
            )

        return last_chat_response

    async def take_step(
        self,
        ctx: Context,
        llm_input: list[ChatMessage],
        tools: Sequence[AsyncBaseTool],
        memory: BaseMemory,
    ) -> AgentOutput:
        """Take a single step with the function calling agent."""
        if not self.llm.metadata.is_function_calling_model:
            raise ValueError("LLM must be a FunctionCallingLLM")

        scratchpad: list[ChatMessage] = await ctx.store.get(
            self.scratchpad_key, default=[]
        )
        current_llm_input = [*llm_input, *scratchpad]

        ctx.write_event_to_stream(
            AgentInput(input=current_llm_input, current_agent_name=self.name)
        )

        if self.streaming:
            last_chat_response = await self._get_streaming_response(
                ctx, current_llm_input, tools
            )
        else:
            last_chat_response = await self._get_response(current_llm_input, tools)

        tool_calls = self.llm.get_tool_calls_from_response(  # type: ignore
            last_chat_response, error_on_no_tool_call=False
        )

        # only add to scratchpad if we didn't select the handoff tool
        scratchpad.append(last_chat_response.message)
        await ctx.store.set(self.scratchpad_key, scratchpad)

        raw = (
            last_chat_response.raw.model_dump()
            if isinstance(last_chat_response.raw, BaseModel)
            else last_chat_response.raw
        )
        return AgentOutput(
            response=last_chat_response.message,
            tool_calls=tool_calls or [],
            raw=raw,
            current_agent_name=self.name,
        )

    async def handle_tool_call_results(
        self, ctx: Context, results: list[ToolCallResult], memory: BaseMemory
    ) -> None:
        """Handle tool call results for function calling agent."""
        scratchpad: list[ChatMessage] = await ctx.store.get(
            self.scratchpad_key, default=[]
        )

        for tool_call_result in results:
            scratchpad.append(
                ChatMessage(
                    role="tool",
                    blocks=tool_call_result.tool_output.blocks,
                    additional_kwargs={"tool_call_id": tool_call_result.tool_id},
                )
            )

            if (
                tool_call_result.return_direct
                and tool_call_result.tool_name != "handoff"
            ):
                scratchpad.append(
                    ChatMessage(
                        role="assistant",
                        content=str(tool_call_result.tool_output.content),
                        additional_kwargs={"tool_call_id": tool_call_result.tool_id},
                    )
                )
                break

        await ctx.store.set(self.scratchpad_key, scratchpad)

    async def finalize(
        self, ctx: Context, output: AgentOutput, memory: BaseMemory
    ) -> AgentOutput:
        """
        Finalize the function calling agent.

        Adds all in-progress messages to memory.
        """
        scratchpad: list[ChatMessage] = await ctx.store.get(
            self.scratchpad_key, default=[]
        )
        await memory.aput_messages(scratchpad)

        # reset scratchpad
        await ctx.store.set(self.scratchpad_key, [])

        return output
