"""
limon.update
------------
Sürüm denetimi ve `limon update`. Kurulumun nasıl yapıldığını anlar ve ona uygun
güncelleme yolunu seçer:
  - tek komutlu kurulum (~/.limon/src)  -> kurulum betiğini yeniden çalıştır
  - pip / pipx                          -> pip install --upgrade limon
  - git klonu                           -> `git pull` önerir
"""

import os
import re
import shutil
import subprocess
import sys
from typing import Optional, Tuple

from . import __version__

REPO = "aardaakpinar/limon"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPO}/releases/latest"
INSTALL_SH_URL = "https://aardaakpinar.github.io/limon/install.sh"
INSTALL_PS1_URL = "https://aardaakpinar.github.io/limon/install.ps1"


def parse_version(v: str) -> Tuple[int, ...]:
    """'v1.2.3' / '1.2.3rc1' -> (1, 2, 3). Sayısal olmayan ekler yok sayılır."""
    nums = re.findall(r"\d+", v.split("-")[0].split("+")[0])
    return tuple(int(n) for n in nums[:3]) or (0,)


def latest_version() -> Optional[str]:
    """GitHub'daki son sürüm etiketi (ör. '0.2.0'); ulaşılamazsa None."""
    try:
        import requests

        r = requests.get(LATEST_RELEASE_API, timeout=10, headers={"Accept": "application/vnd.github+json"})
        if r.status_code != 200:
            return None
        return r.json().get("tag_name", "").lstrip("v") or None
    except Exception:
        return None


def install_kind() -> str:
    """'script' | 'git' | 'pip'"""
    pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = os.environ.get("LIMON_HOME") or os.path.join(os.path.expanduser("~"), ".limon")
    if os.path.normcase(pkg_parent) == os.path.normcase(os.path.join(home, "src")):
        return "script"
    if os.path.isdir(os.path.join(pkg_parent, ".git")):
        return "git"
    return "pip"


def run_update(check_only: bool = False, say=print) -> int:
    latest = latest_version()
    if latest is None:
        say("Son sürüm bilgisi alınamadı (GitHub'da yayınlanmış bir sürüm yok ya da bağlantı sorunu var).")
    elif parse_version(latest) <= parse_version(__version__):
        say(f"limon güncel (v{__version__}).")
        return 0
    else:
        say(f"Yeni sürüm var: v{latest} (kurulu: v{__version__}).")

    if check_only:
        return 0

    kind = install_kind()
    if kind == "git":
        say("Bu kurulum bir git klonu. Güncellemek için klasörde şunları çalıştır:\n  git pull && pip install -e .")
        return 0

    if kind == "pip":
        say("pip ile güncelleniyor...")
        pipx = shutil.which("pipx")
        in_pipx = pipx and "pipx" in os.path.abspath(sys.prefix).replace("\\", "/")
        cmd = [pipx, "upgrade", "limon"] if in_pipx else [sys.executable, "-m", "pip", "install", "--upgrade", "limon"]
        return subprocess.call(cmd)

    # kind == "script": kurulum betiğini yeniden çalıştır
    say("Kurulum betiği yeniden çalıştırılıyor...")
    try:
        import requests

        if os.name == "nt":
            ps = shutil.which("powershell") or shutil.which("pwsh")
            if not ps:
                say(f"PowerShell bulunamadı. Elle çalıştır: irm {INSTALL_PS1_URL} | iex")
                return 1
            return subprocess.call([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                                    f"irm {INSTALL_PS1_URL} | iex"])
        bash = shutil.which("bash")
        if not bash:
            say(f"bash bulunamadı. Elle çalıştır: curl -fsSL {INSTALL_SH_URL} | bash")
            return 1
        script = requests.get(INSTALL_SH_URL, timeout=30)
        script.raise_for_status()
        return subprocess.run([bash, "-s"], input=script.content).returncode
    except Exception as e:
        say(f"Güncelleme başarısız: {e}")
        return 1
