"""
limon.cli
---------
Terminal arayüzü: REPL döngüsü, tool onay promptları, renkli çıktı ve
`limon config` ile ilk kurulum sihirbazı.
"""

import argparse
import os
import shutil
import sys
import time

from . import config as cfgmod
from .agent import Agent, ToolDecision
from .danger import DangerAssessment
from .errors import ProviderError
from .providers import PROVIDER_CHOICES, create_provider

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

BANNER = f"""
{YELLOW}{BOLD}  ██╗     ██╗███╗   ███╗ ██████╗ ███╗   ██╗{RESET}
{YELLOW}{BOLD}  ██║     ██║████╗ ████║██╔═══██╗████╗  ██║{RESET}
{YELLOW}{BOLD}  ██║     ██║██╔████╔██║██║   ██║██╔██╗ ██║{RESET}
{YELLOW}{BOLD}  ██║     ██║██║╚██╔╝██║██║   ██║██║╚██╗██║{RESET}
{YELLOW}{BOLD}  ███████╗██║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║{RESET}
{YELLOW}{BOLD}  ╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝{RESET}
{DIM}  Linux için AI komut asistanı{RESET}
"""

TOOL_ICONS = {
    "read_file": "📄",
    "write_file": "✏️",
    "delete_file": "🗑️",
    "list_dir": "📁",
    "run_command": "🖥️",
    "get_current_datetime": "🕒",
}


class CLIToolDecision(ToolDecision):
    def on_tool_start(self, tool_name, args):
        icon = TOOL_ICONS.get(tool_name, "🔧")
        summary = _summarize_args(tool_name, args)
        print(f"{DIM}{icon} {tool_name} {summary}{RESET}")

    def on_tool_result(self, tool_name, result):
        first_line = result.strip().splitlines()[0] if result.strip() else ""
        if "HATA" in first_line:
            print(f"{RED}  ✗ {first_line}{RESET}")

    def ask(self, tool_name: str, args: dict, assessment: DangerAssessment) -> bool:
        icon = TOOL_ICONS.get(tool_name, "🔧")
        summary = _summarize_args(tool_name, args)
        bar = "█" * assessment.score + "░" * (10 - assessment.score)
        color = RED if assessment.score >= 8 else YELLOW
        print()
        print(f"{color}{BOLD}⚠ ONAY GEREKİYOR{RESET}  [{color}{bar}{RESET}] {assessment.score}/10")
        print(f"  {icon} {BOLD}{tool_name}{RESET} {summary}")
        print(f"  {DIM}Sebep: {assessment.describe()}{RESET}")
        try:
            answer = input(f"  Devam edilsin mi? [{GREEN}e{RESET}vet / {RED}h{RESET}ayır]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        return answer in ("e", "evet", "y", "yes")


def _summarize_args(tool_name: str, args: dict) -> str:
    if tool_name == "run_command":
        return args.get("command", "")
    if tool_name in ("read_file", "write_file", "delete_file"):
        return args.get("path", "")
    if tool_name == "list_dir":
        return args.get("path", ".")
    return str(args)


def run_setup_wizard():
    cfg = cfgmod.load_config()
    print(BANNER)
    print("İlk kurulum / ayarlar\n")

    try:
        print("Sağlayıcı seç:")
        for i, p in enumerate(PROVIDER_CHOICES, 1):
            marker = " (mevcut)" if p == cfg["provider"] else ""
            print(f"  {i}. {p}{marker}")
        choice = input(f"Seçim [{PROVIDER_CHOICES.index(cfg['provider'])+1}]: ").strip()
        if choice:
            try:
                cfg["provider"] = PROVIDER_CHOICES[int(choice) - 1]
            except (ValueError, IndexError):
                print(f"{RED}Geçersiz seçim, mevcut sağlayıcı korunuyor.{RESET}")

        default_model = cfgmod.DEFAULT_MODELS.get(cfg["provider"], "")
        model = input(f"Model [{cfg.get('model') or default_model}]: ").strip()
        cfg["model"] = model or cfg.get("model") or default_model

        if cfg["provider"] in ("openai", "gemini", "claude"):
            current = cfg["api_keys"].get(cfg["provider"], "")
            masked = (current[:4] + "..." + current[-4:]) if len(current) > 8 else ("(yok)" if not current else current)
            key = input(f"{cfg['provider']} API anahtarı [{masked}]: ").strip()
            if key:
                cfg["api_keys"][cfg["provider"]] = key
        else:
            host = input(f"Ollama host [{cfg.get('ollama_host')}]: ").strip()
            if host:
                cfg["ollama_host"] = host

        threshold = input(f"Tehlike onay eşiği (0-10) [{cfg.get('danger_threshold')}]: ").strip()
        if threshold:
            try:
                cfg["danger_threshold"] = max(0, min(10, int(threshold)))
            except ValueError:
                pass
    except (EOFError, KeyboardInterrupt):
        print(f"\n{YELLOW}Kurulum iptal edildi, değişiklikler kaydedilmedi.{RESET}")
        sys.exit(1)

    cfgmod.save_config(cfg)
    print(f"\n{GREEN}✓ Ayarlar kaydedildi:{RESET} {cfgmod.CONFIG_PATH}\n")


def build_provider(cfg: dict):
    provider_name = cfg["provider"]
    api_key = cfgmod.get_api_key(cfg, provider_name)
    if provider_name != "ollama" and not api_key:
        print(f"{RED}Hata: {provider_name} için API anahtarı bulunamadı.{RESET}")
        print(f"  'limon config' komutuyla ayarlayabilir, ya da ortam değişkeni tanımlayabilirsin.")
        sys.exit(1)
    try:
        return create_provider(
            provider_name, api_key=api_key, model=cfg["model"], ollama_host=cfg.get("ollama_host", "")
        )
    except RuntimeError as e:
        print(f"{RED}Hata: {e}{RESET}")
        sys.exit(1)


def repl(cfg: dict):
    provider = build_provider(cfg)
    agent = Agent(provider, danger_threshold=cfg.get("danger_threshold", 5))
    decision = CLIToolDecision()

    print(BANNER)
    print(f"{DIM}sağlayıcı: {cfg['provider']} | model: {cfg['model']} | eşik: {cfg.get('danger_threshold')}{RESET}")
    print(f"{DIM}çıkmak için: exit / quit / Ctrl+D{RESET}\n")

    while True:
        try:
            user_input = input(f"{CYAN}{BOLD}> {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", ":q"):
            break
        if user_input.lower() in ("/config",):
            run_setup_wizard()
            provider = build_provider(cfg)
            agent = Agent(provider, danger_threshold=cfg.get("danger_threshold", 5))
            continue
        if user_input.lower() in ("/reset",):
            agent.history = []
            print(f"{DIM}Konuşma geçmişi sıfırlandı.{RESET}")
            continue

        attempts = 0
        while True:
            try:
                answer = agent.run_turn(user_input, decision)
                break
            except ProviderError as e:
                print(f"{RED}Hata: {e}{RESET}")
                if e.retry_after is None or attempts >= 1:
                    answer = ""
                    break
                attempts += 1
                wait = int(e.retry_after) + 1
                print(f"{YELLOW}{wait} saniye sonra tekrar denenecek...{RESET}")
                time.sleep(wait)
                continue
            except Exception as e:
                print(f"{RED}Hata: {e}{RESET}")
                answer = ""
                break

        if answer:
            print(answer)
        print()


def uninstall():
    """Limon ayarlarını ve yapılandırma dosyalarını kaldır."""
    print(f"{YELLOW}{BOLD}⚠ Uyarı: Limon yapılandırması silinecek!{RESET}\n")
    print(f"Bu işlem aşağıdaki dosyaları silecek:")
    print(f"  {cfgmod.CONFIG_DIR}/\n")
    
    try:
        confirm = input(f"Emin misin? [{RED}H{RESET}ayır / {GREEN}e{RESET}vet]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(f"\n{YELLOW}İşlem iptal edildi.{RESET}")
        return
    
    if confirm not in ("e", "evet", "y", "yes"):
        print(f"{YELLOW}İşlem iptal edildi.{RESET}")
        return
    
    try:
        if os.path.exists(cfgmod.CONFIG_DIR):
            shutil.rmtree(cfgmod.CONFIG_DIR)
            print(f"\n{GREEN}✓ Limon yapılandırması başarıyla silindi.{RESET}")
        else:
            print(f"\n{YELLOW}Zaten yapılandırma dosyası yok.{RESET}")
    except Exception as e:
        print(f"{RED}Hata: {e}{RESET}")
        sys.exit(1)
    
    print(f"\nPaketi tamamen kaldırmak için:")
    print(f"  {CYAN}pip uninstall limon{RESET}")


def main():
    parser = argparse.ArgumentParser(prog="limon", description="Linux için AI komut asistanı")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("config", help="Sağlayıcı / API anahtarı / eşik ayarlarını yapılandır")
    sub.add_parser("uninstall", help="Limon yapılandırmasını ve ayarlarını kaldır")
    parser.add_argument("-p", "--prompt", help="Tek seferlik komut (REPL açmadan çalıştır)")
    args = parser.parse_args()

    cfg = cfgmod.load_config()

    if args.command == "config":
        run_setup_wizard()
        return

    if args.command == "uninstall":
        uninstall()
        return

    if not cfgmod.get_api_key(cfg, cfg["provider"]) and cfg["provider"] != "ollama":
        print(f"{YELLOW}Henüz yapılandırma yapılmamış görünüyor.{RESET}")
        run_setup_wizard()
        cfg = cfgmod.load_config()

    if args.prompt:
        provider = build_provider(cfg)
        agent = Agent(provider, danger_threshold=cfg.get("danger_threshold", 5))
        decision = CLIToolDecision()
        attempts = 0
        while True:
            try:
                print(agent.run_turn(args.prompt, decision))
                break
            except ProviderError as e:
                print(f"{RED}Hata: {e}{RESET}")
                if e.retry_after is None or attempts >= 1:
                    break
                attempts += 1
                wait = int(e.retry_after) + 1
                print(f"{YELLOW}{wait} saniye sonra tekrar denenecek...{RESET}")
                time.sleep(wait)
                continue
        return

    repl(cfg)


def entrypoint():
    """Konsol betiği (limon.exe / limon) buradan başlar; beklenmedik
    Ctrl+C / EOF durumlarında çirkin bir traceback yerine temiz çıkış yapar."""
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{DIM}Çıkılıyor.{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    entrypoint()
