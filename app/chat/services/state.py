import uuid
from typing import Any

from app.chat.schemas import AIGenerationResult


class MessageStateAccumulator:
    """
    Encapsulates the in-memory state of a message being generated.
    This mirrors the 'blocks' and 'tool_calls' columns in the DB.
    """
    def __init__(self):
        self.tool_calls: dict[str, dict[str, Any]] = {}
        self.ordered_blocks: list[dict[str, Any]] = []
        self.current_text_block_id: str | None = None

    def append_text(self, delta: str) -> str:
        """Appends text, creating a new block if necessary. Returns block_id."""
        if self.current_text_block_id is None:
            self.current_text_block_id = str(uuid.uuid4())
            self.ordered_blocks.append({
                "type": "text",
                "block_id": self.current_text_block_id,
                "content": ""
            })
        
        # Append to the last block (assuming it matches current ID)
        if self.ordered_blocks:
            self.ordered_blocks[-1]["content"] += delta
            
        return self.current_text_block_id

    def add_tool_call(self, run_id: str, tool_id: str, name: str, kwargs: dict):
        self.current_text_block_id = None # Reset text block on tool call
        self.tool_calls[run_id] = {
            "id": tool_id,
            "name": name,
            "kwargs": kwargs,
            "run_id": run_id,
            "output": None,
        }
        self.ordered_blocks.append({
            "type": "tool",
            "tool_run_id": run_id,
            "tool_name": name,
        })

    def add_tool_result(self, run_id: str, output: str):
        if run_id in self.tool_calls:
            self.tool_calls[run_id]["output"] = output

    def to_result(self, final_content: str) -> AIGenerationResult:
        return AIGenerationResult(
            content=final_content,
            tool_calls=list(self.tool_calls.values()),
            blocks=self.ordered_blocks,
        )