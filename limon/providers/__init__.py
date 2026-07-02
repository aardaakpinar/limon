from .base import BaseProvider, ChatResult, ToolCall

PROVIDER_CHOICES = ["openai", "gemini", "claude", "ollama"]


def create_provider(provider_name: str, api_key: str, model: str, ollama_host: str = "http://localhost:11434") -> BaseProvider:
    if provider_name == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model=model)
    elif provider_name == "gemini":
        from .gemini_provider import GeminiProvider
        return GeminiProvider(api_key=api_key, model=model)
    elif provider_name == "claude":
        from .claude_provider import ClaudeProvider
        return ClaudeProvider(api_key=api_key, model=model)
    elif provider_name == "ollama":
        from .ollama_provider import OllamaProvider
        return OllamaProvider(api_key=api_key, model=model, host=ollama_host)
    else:
        raise ValueError(f"Bilinmeyen sağlayıcı: {provider_name}")
