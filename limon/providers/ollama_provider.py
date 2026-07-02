from typing import List
from .base import BaseProvider, ChatResult, ToolCall


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(self, api_key: str, model: str, host: str = "http://localhost:11434", **kwargs):
        super().__init__(api_key, model, **kwargs)
        try:
            import requests
        except ImportError:
            raise RuntimeError("requests paketi kurulu değil. Kurmak için: pip install requests")
        self.requests = requests
        self.host = host.rstrip("/")

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
        try:
            resp = self.requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "tools": self._convert_tools(tools),
                    "stream": False,
                },
                timeout=180,
            )
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(
                f"Ollama'ya bağlanılamadı ({self.host}). Ollama çalışıyor mu? "
                f"('ollama serve') Hata: {e}"
            )
        data = resp.json()
        msg = data.get("message", {})
        tool_calls = []
        for i, tc in enumerate(msg.get("tool_calls", []) or []):
            fn = tc.get("function", {})
            tool_calls.append(
                ToolCall(id=f"ollama_{i}", name=fn.get("name", ""), arguments=fn.get("arguments", {}) or {})
            )

        return ChatResult(
            text=(msg.get("content") or "").strip(),
            tool_calls=tool_calls,
            raw_assistant_message=msg,
        )

    def append_tool_results(self, history, assistant_msg, tool_calls, results):
        history.append({"role": "assistant", "content": assistant_msg.get("content", "")})
        for tc, res in zip(tool_calls, results):
            history.append({"role": "tool", "content": res})
