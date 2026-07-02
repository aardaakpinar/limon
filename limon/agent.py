"""
limon.agent
-----------
Akış:
  Kullanıcı soru sorar
    -> AI (provider) cevap verir ve/veya tool_call(ler) döndürür
    -> Her tool_call için danger.py ile bir tehlike skoru hesaplanır
    -> Skor eşiği geçerse kullanıcıya onay sorulur (aksi halde otomatik çalışır)
    -> Sonuç modele geri gönderilir, model tool_call döndürmeyi bırakana kadar tekrar edilir
    -> Nihai metin kullanıcıya gösterilir
"""

from typing import Callable, List, Optional

from . import danger
from .errors import ProviderError, humanize_provider_error
from .tools import TOOL_DEFINITIONS, TOOL_IMPLEMENTATIONS
from .providers.base import BaseProvider, ToolCall

MAX_TOOL_ITERATIONS = 12

SYSTEM_PROMPT = """\
Sen "limon" adlı bir Linux komut satırı asistanısın. Kullanıcının makinesinde \
dosya okuma/yazma/silme ve kabuk (bash) komutu çalıştırma araçlarına erişimin var.

Kurallar:
- Kullanıcı bir şey yapmanı istediğinde (dosya düzenleme, hata bulma, sistem sorgusu vb.) \
  önce gerektiği kadar bilgi topla (read_file, list_dir, run_command gibi araçlarla), \
  sonra değişikliği uygula.
- write_file çağırırken dosyanın TAM ve nihai içeriğini gönder (parça parça değil).
- Tehlikeli olabilecek komutlar (silme, sistem değişikliği, yetki gerektiren işlemler) \
  otomatik olarak kullanıcı onayına sunulacak; bu yüzden gerekmedikçe bu tür komutlardan kaçın, \
  ama gerekiyorsa çekinme, sistem seni zaten koruyacak.
- Kısa, net ve Türkçe cevap ver. Gereksiz uzun açıklamalardan kaçın.
- Bir işlemi tamamladığında kullanıcıya kısaca ne yaptığını özetle (örn. "3 hata düzeltildi.").
"""


class ToolDecision:
    """Kullanıcı onay akışı için basit bir arayüz. CLI bunu terminal
    promptu ile, başka bir arayüz farklı şekilde uygulayabilir."""

    def ask(self, tool_name: str, args: dict, assessment: danger.DangerAssessment) -> bool:
        raise NotImplementedError

    def on_tool_start(self, tool_name: str, args: dict):
        pass

    def on_tool_result(self, tool_name: str, result: str):
        pass


def _assess_tool_call(tool_def: dict, args: dict) -> danger.DangerAssessment:
    kind = tool_def.get("danger", "none")
    if kind == "command":
        return danger.assess_command(args.get("command", ""))
    if kind == "file_write":
        import os
        path = os.path.expanduser(args.get("path", ""))
        return danger.assess_file_write(path, is_overwrite=os.path.exists(path))
    if kind == "file_delete":
        return danger.assess_file_delete(args.get("path", ""))
    return danger.DangerAssessment(score=0, reasons=[])


class Agent:
    def __init__(self, provider: BaseProvider, danger_threshold: int = 5):
        self.provider = provider
        self.danger_threshold = danger_threshold
        self.history: List[dict] = []
        self.tool_defs_by_name = {t["name"]: t for t in TOOL_DEFINITIONS}

    def run_turn(self, user_message: str, decision: ToolDecision) -> str:
        self.history.append({"role": "user", "content": user_message})

        for _ in range(MAX_TOOL_ITERATIONS):
            try:
                result = self.provider.chat(SYSTEM_PROMPT, self.history, TOOL_DEFINITIONS)
            except ProviderError:
                raise
            except Exception as e:
                raise humanize_provider_error(e)

            if not result.tool_calls:
                self.history.append({"role": "assistant", "content": result.text})
                return result.text

            tool_results = []
            for tc in result.tool_calls:
                tool_def = self.tool_defs_by_name.get(tc.name)
                if tool_def is None:
                    tool_results.append(f"HATA: bilinmeyen araç: {tc.name}")
                    continue

                assessment = _assess_tool_call(tool_def, tc.arguments)
                threshold = self.danger_threshold
                if assessment.score >= threshold:
                    approved = decision.ask(tc.name, tc.arguments, assessment)
                    if not approved:
                        tool_results.append(
                            "İŞLEM İPTAL EDİLDİ: kullanıcı bu adımı onaylamadı. "
                            "Alternatif bir yol öner veya kullanıcıya bilgi ver."
                        )
                        continue

                decision.on_tool_start(tc.name, tc.arguments)
                impl = TOOL_IMPLEMENTATIONS[tc.name]
                try:
                    tool_output = impl(tc.arguments)
                except Exception as e:
                    tool_output = f"HATA: araç çalıştırılırken istisna oluştu: {e}"
                decision.on_tool_result(tc.name, tool_output)
                tool_results.append(tool_output)

            self.provider.append_tool_results(
                self.history, result.raw_assistant_message, result.tool_calls, tool_results
            )

        return "Çok fazla ardışık araç çağrısı yapıldı, işlemi durduruyorum. Lütfen isteğini sadeleştir."
