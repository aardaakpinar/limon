from typing import List
from .base import BaseProvider, ChatResult, ToolCall


def _clean_schema(schema: dict) -> dict:
    """Gemini, JSON Schema'nın bir alt kümesini kabul eder; bilinmeyen
    anahtarları (ör. 'additionalProperties') temizler."""
    if not isinstance(schema, dict):
        return schema
    allowed = {"type", "description", "properties", "required", "items", "enum"}
    cleaned = {k: v for k, v in schema.items() if k in allowed}
    if "properties" in cleaned:
        cleaned["properties"] = {k: _clean_schema(v) for k, v in cleaned["properties"].items()}
    if "items" in cleaned:
        cleaned["items"] = _clean_schema(cleaned["items"])
    return cleaned


class GeminiProvider(BaseProvider):
    """google-genai (yeni, güncel SDK) kullanır - google-generativeai artık
    kullanımdan kaldırıldı ve 'thinking' modellerinde thought_signature
    hatası veriyordu."""

    name = "gemini"

    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(api_key, model, **kwargs)
        try:
            from google import genai
        except ImportError:
            raise RuntimeError(
                "google-genai paketi kurulu değil. Kurmak için: pip install google-genai"
            )
        self.genai = genai
        self.client = genai.Client(api_key=api_key)

    def _convert_tools(self, tools: List[dict]):
        from google.genai import types
        function_declarations = [
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=_clean_schema(t["parameters"]) or {"type": "object", "properties": {}},
            )
            for t in tools
        ]
        return [types.Tool(function_declarations=function_declarations)]

    def _to_gemini_contents(self, history: List[dict]):
        """limon'un iç mesaj formatını google-genai 'contents' formatına çevirir.
        Önceki turlarda saklanan ham types.Content nesneleri (asistan cevapları)
        AYNEN geri gönderilir; bu, thought_signature gibi opak alanların
        kaybolmadan korunmasını sağlar."""
        from google.genai import types

        contents = []
        for m in history:
            content = m["content"]
            if isinstance(content, types.Content):
                contents.append(content)
            elif isinstance(content, str):
                role = "model" if m["role"] == "assistant" else "user"
                contents.append(types.Content(role=role, parts=[types.Part(text=content)]))
            else:
                # list of types.Part (ör. function_response parçaları)
                role = "model" if m["role"] == "assistant" else "user"
                contents.append(types.Content(role=role, parts=list(content)))
        return contents

    def chat(self, system_prompt: str, history: List[dict], tools: List[dict]) -> ChatResult:
        from google.genai import types

        contents = self._to_gemini_contents(history)
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=self._convert_tools(tools),
            ),
        )

        candidate = response.candidates[0]
        text_parts = []
        tool_calls = []
        for i, part in enumerate(candidate.content.parts):
            if part.text:
                text_parts.append(part.text)
            elif part.function_call:
                fc = part.function_call
                args = dict(fc.args) if fc.args else {}
                tool_calls.append(ToolCall(id=f"gem_{i}", name=fc.name, arguments=args))

        return ChatResult(
            text="\n".join(text_parts).strip(),
            tool_calls=tool_calls,
            # Ham Content nesnesini olduğu gibi saklıyoruz (thought_signature dahil).
            raw_assistant_message=candidate.content,
        )

    def append_tool_results(self, history, assistant_msg, tool_calls, results):
        from google.genai import types

        history.append({"role": "assistant", "content": assistant_msg})
        response_parts = [
            types.Part(function_response=types.FunctionResponse(name=tc.name, response={"result": res}))
            for tc, res in zip(tool_calls, results)
        ]
        history.append({"role": "user", "content": response_parts})
