"""
limon.providers.base
---------------------
Tüm sağlayıcıların uyması gereken ortak arayüz.

Ortak mesaj formatı (limon içinde kullanılan, sağlayıcıya-özgü DEĞİL):
    {"role": "user"|"assistant"|"tool", "content": str, ...}

chat() metodu şunu döndürür:
    ChatResult(text=..., tool_calls=[ToolCall(id, name, arguments), ...])

tool_calls boşsa, model son cevabı verdi demektir (text kullanıcıya gösterilir).
tool_calls doluysa, agent.py bunları çalıştırıp sonucu tekrar modele gönderir.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ChatResult:
    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw_assistant_message: Any = None  # sağlayıcıya özgü, sonraki turda geri göndermek için


class BaseProvider:
    name = "base"

    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model

    def chat(self, system_prompt: str, history: List[dict], tools: List[dict]) -> ChatResult:
        raise NotImplementedError

    def append_tool_results(self, history: List[dict], assistant_msg: Any,
                             tool_calls: List[ToolCall], results: List[str]) -> None:
        """history listesini yerinde değiştirerek asistan mesajını ve tool
        sonuçlarını sağlayıcıya uygun formatta ekler."""
        raise NotImplementedError
