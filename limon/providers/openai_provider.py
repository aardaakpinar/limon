import json
from typing import List
from .base import BaseProvider, ChatResult, ToolCall


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(api_key, model, **kwargs)
        try:
            import openai
        except ImportError:
            raise RuntimeError(
                "openai paketi kurulu değil. Kurmak için: pip install openai"
            )
        self.client = openai.OpenAI(api_key=api_key)

    def _convert_tools(self, tools: List[dict]) -> List[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in tools
        ]

    def chat(self, system_prompt: str, history: List[dict], tools: List[dict]) -> ChatResult:
        messages = [{"role": "system", "content": system_prompt}] + history
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self._convert_tools(tools),
        )
        msg = response.choices[0].message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

        return ChatResult(
            text=(msg.content or "").strip(),
            tool_calls=tool_calls,
            raw_assistant_message=msg,
        )

    def append_tool_results(self, history, assistant_msg, tool_calls, results):
        history.append({
            "role": "assistant",
            "content": assistant_msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments, ensure_ascii=False)},
                }
                for tc in tool_calls
            ],
        })
        for tc, res in zip(tool_calls, results):
            history.append({"role": "tool", "tool_call_id": tc.id, "content": res})
