"""
limon.danger
------------
Çalıştırılacak komutlara / dosya işlemlerine 0-10 arası bir "tehlike skoru" atar.
Skor, tanımlı desenlerin (regex) toplamına ve hedef yolun sistem dizini olup
olmadığına göre hesaplanır. Skor eşik değerini (varsayılan 5) geçerse kullanıcı
onayı istenir.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional, Tuple, List

# (regex, puan, açıklama)
COMMAND_PATTERNS = [
    (r"\brm\s+.*-[a-zA-Z]*r[a-zA-Z]*f", 9, "Yinelemeli / zorla silme (rm -rf)"),
    (r"\brm\s+-[a-zA-Z]*f", 5, "Zorla silme (rm -f)"),
    (r":\(\)\s*\{\s*:\|\s*:&\s*\}\s*;\s*:", 10, "Fork bomb"),
    (r"\bmkfs(\.|$)", 10, "Dosya sistemi biçimlendirme"),
    (r"\bdd\s+if=", 9, "Ham disk yazma (dd)"),
    (r">\s*/dev/(sd|nvme|hd)", 10, "Diske doğrudan yazma"),
    (r"\bshutdown\b|\breboot\b|\bpoweroff\b|\bhalt\b", 6, "Sistemi kapatma/yeniden başlatma"),
    (r"\bsudo\b", 5, "Yönetici (root) yetkisi"),
    (r"\bchmod\s+(-R\s+)?0?777", 6, "Aşırı geniş izin (777)"),
    (r"\bchown\s+-R\s+", 4, "Yinelemeli sahiplik değişimi"),
    (r"\bkill\s+-9\b|\bkillall\b|\bpkill\b", 4, "Zorla süreç sonlandırma"),
    (r"\biptables\b|\bufw\b|\bfirewall-cmd\b", 5, "Güvenlik duvarı kuralı değişimi"),
    (r"curl[^|]*\|\s*(sudo\s+)?(bash|sh)\b", 8, "İnternetten script indirip doğrudan çalıştırma"),
    (r"wget[^|]*\|\s*(sudo\s+)?(bash|sh)\b", 8, "İnternetten script indirip doğrudan çalıştırma"),
    (r"\bgit\s+push\s+.*--force", 5, "Zorla git push (geçmişi ezer)"),
    (r"\bgit\s+reset\s+--hard", 4, "Yinelenemez git reset"),
    (r"\bDROP\s+TABLE\b|\bDROP\s+DATABASE\b|\bTRUNCATE\b", 8, "Veritabanı yapısını/verisini silme"),
    (r"\bapt(-get)?\s+(remove|purge)\b|\byum\s+remove\b|\bpacman\s+-R\b", 4, "Paket kaldırma"),
    (r"\buserdel\b|\bpasswd\b|\bvisudo\b", 6, "Kullanıcı/parola/sudoers değişimi"),
    (r"\bcrontab\s+-r\b", 5, "Tüm zamanlanmış görevleri silme"),
    (r">\s*/etc/", 7, "Sistem yapılandırma dosyasının üzerine yazma"),
    (r"\bnc\b.*-e\b|\bnetcat\b.*-e\b", 7, "Ters kabuk / reverse shell şüphesi"),
    (r"\beval\b|\bexec\(", 3, "Dinamik kod çalıştırma"),
]

SYSTEM_PATH_PREFIXES = [
    "/etc", "/boot", "/sys", "/proc", "/usr", "/bin", "/sbin",
    "/lib", "/root", "/var/lib", "/dev",
]


@dataclass
class DangerAssessment:
    score: int
    reasons: List[str] = field(default_factory=list)

    @property
    def requires_confirmation(self) -> bool:
        return self.score >= 5

    def describe(self) -> str:
        if not self.reasons:
            return "Belirgin bir risk tespit edilmedi."
        return "; ".join(self.reasons)


def _path_risk(path: str) -> Tuple[int, Optional[str]]:
    if not path:
        return 0, None
    abspath = os.path.abspath(os.path.expanduser(path))
    for prefix in SYSTEM_PATH_PREFIXES:
        if abspath == prefix or abspath.startswith(prefix + "/"):
            return 7, f"Sistem dizinine erişim: {abspath}"
    return 0, None


def assess_command(command: str) -> DangerAssessment:
    score = 0
    reasons = []
    for pattern, points, desc in COMMAND_PATTERNS:
        if re.search(pattern, command, flags=re.IGNORECASE):
            score += points
            reasons.append(desc)

    for token in re.findall(r"(/[\w./\-]+)", command):
        p_score, p_reason = _path_risk(token)
        if p_reason and p_reason not in reasons:
            score += p_score
            reasons.append(p_reason)

    return DangerAssessment(score=min(score, 10), reasons=reasons)


def assess_file_write(path: str, is_overwrite: bool) -> DangerAssessment:
    score = 1 if is_overwrite else 0
    reasons = []
    if is_overwrite:
        reasons.append("Var olan dosyanın üzerine yazılacak (yedek alınacak)")

    p_score, p_reason = _path_risk(path)
    if p_reason:
        score += p_score
        reasons.append(p_reason)

    return DangerAssessment(score=min(score, 10), reasons=reasons)


def assess_file_delete(path: str) -> DangerAssessment:
    score = 4
    reasons = ["Dosya silme işlemi"]
    p_score, p_reason = _path_risk(path)
    if p_reason:
        score += p_score
        reasons.append(p_reason)
    return DangerAssessment(score=min(score, 10), reasons=reasons)
