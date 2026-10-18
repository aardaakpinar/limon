"""Hassas veri filtreleme. Sağlayıcıya giden / diske yazılan her metin buradan geçer.
Filtre 'en iyi çaba'dır; asıl koruma, sağlayıcıya ortam değişkeni ve dosya içeriğinin
hiç gönderilmemesidir."""

import re
from typing import List, Tuple

_PLACEHOLDER = "[GİZLENDİ]"

_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(-----END [A-Z ]*PRIVATE KEY-----|\Z)", re.S), _PLACEHOLDER),
    (re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{16,}"), _PLACEHOLDER),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}"), _PLACEHOLDER),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}"), _PLACEHOLDER),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"), _PLACEHOLDER),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), _PLACEHOLDER),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"), _PLACEHOLDER),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=\-]{8,}"), r"\1 " + _PLACEHOLDER),
    (re.compile(r"(?i)(://[^/\s:@]+:)[^@\s/]+(@)"), r"\1" + _PLACEHOLDER + r"\2"),
    (re.compile(
        r"(?i)\b([A-Za-z0-9_.\-]*(?:password|passwd|parola|secret|token|api[_-]?key|apikey|private[_-]?key|credential|auth)[A-Za-z0-9_.\-]*)"
        r"(\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;&\"']+)"
    ), r"\1\2" + _PLACEHOLDER),
]

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def redact(text: str) -> str:
    if not text:
        return ""
    text = _CTRL.sub("", text)
    for rx, repl in _PATTERNS:
        text = rx.sub(repl, text)
    return text


def clip(text: str, max_chars: int, keep_tail: bool = True) -> str:
    """Boyut sınırı; log için sondaki (en yeni) kısım korunur."""
    if len(text) <= max_chars:
        return text
    cut = len(text) - max_chars
    if keep_tail:
        return f"[… {cut} karakter kırpıldı …]\n" + text[-max_chars:]
    return text[:max_chars] + f"\n[… {cut} karakter kırpıldı …]"


def safe(text: str, max_chars: int, keep_tail: bool = True) -> str:
    return clip(redact(text), max_chars, keep_tail)
