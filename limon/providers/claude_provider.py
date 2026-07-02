from typing import List
from .base import BaseProvider, ChatResult, ToolCall


class ClaudeProvider(BaseProvider):
    name = "claude"

    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(api_key, model, **kwargs)
        try:
            import anthropic
        except ImportError:
            raise RuntimeError(
                "anthropic paketi kurulu değil. Kurmak için: pip install anthropic"
            )
        self.client = anthropic.Anthropic(api_key=api_key)

    def _convert_tools(self, tools: List[dict]) -> List[dict]:
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"],
            }
            for t in tools
        ]

    def chat(self, system_prompt: str, history: List[dict], tools: List[dict]) -> ChatResult:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=history,
            tools=self._convert_tools(tools),
        )

        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))

        assistant_content = [b.model_dump() for b in response.content]
        return ChatResult(
            text="\n".join(text_parts).strip(),
            tool_calls=tool_calls,
            raw_assistant_message=assistant_content,
        )

    def append_tool_results(self, history, assistant_msg, tool_calls, results):
        history.append({"role": "assistant", "content": assistant_msg})
        tool_result_blocks = [
            {"type": "tool_result", "tool_use_id": tc.id, "content": res}
            for tc, res in zip(tool_calls, results)
        ]
        history.append({"role": "user", "content": tool_result_blocks})
