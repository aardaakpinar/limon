"""Durum / çalışma zamanı dizinleri. systemd'nin STATE_DIRECTORY / RUNTIME_DIRECTORY
değişkenleri ve LIMON_STATE_DIR / LIMON_RUNTIME_DIR (test, özel kurulum) öncelikli."""

import os
import stat
from dataclasses import dataclass

SOCKET_NAME = "limon.sock"


class PathError(Exception):
    pass


@dataclass
class Paths:
    scope: str
    state_dir: str
    runtime_dir: str

    @property
    def socket(self) -> str:
        return os.path.join(self.runtime_dir, SOCKET_NAME)

    @property
    def db(self) -> str:
        return os.path.join(self.state_dir, "state.db")

    @property
    def audit(self) -> str:
        return os.path.join(self.state_dir, "audit.jsonl")

    @property
    def backups(self) -> str:
        return os.path.join(self.state_dir, "backups")


def _first_dir(value: str) -> str:
    # systemd birden çok dizini ':' ile ayırabilir
    return value.split(":")[0]


def resolve_paths(scope: str = "user") -> Paths:
    if scope not in ("user", "system"):
        raise PathError(f"Geçersiz kapsam: {scope!r} (user | system)")
    home = os.path.expanduser("~")
    if scope == "system":
        state = "/var/lib/limon"
        runtime = "/run/limon"
    else:
        state = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(home, ".local", "state"), "limon")
        xdg_rt = os.environ.get("XDG_RUNTIME_DIR")
        runtime = os.path.join(xdg_rt, "limon") if xdg_rt else os.path.join(state, "run")
    state = os.environ.get("LIMON_STATE_DIR") or (_first_dir(os.environ["STATE_DIRECTORY"]) if os.environ.get("STATE_DIRECTORY") else state)
    runtime = os.environ.get("LIMON_RUNTIME_DIR") or (
        _first_dir(os.environ["RUNTIME_DIRECTORY"]) if os.environ.get("RUNTIME_DIRECTORY") else runtime
    )
    return Paths(scope=scope, state_dir=state, runtime_dir=runtime)


def ensure_private_dir(path: str, mode: int = 0o700, group_access: bool = False) -> None:
    """Dizini oluşturur ve yalnızca sahibine (isteğe bağlı gruba) açar.
    Başka bir kullanıcıya ait ya da simge bağlantılı dizini kabul etmez."""
    if os.path.islink(path):
        raise PathError(f"Güvenlik: {path} bir simge bağlantısı, kullanılmıyor.")
    os.makedirs(path, mode=mode, exist_ok=True)
    st = os.stat(path)
    if hasattr(os, "geteuid") and st.st_uid != os.geteuid():
        raise PathError(f"Güvenlik: {path} başka bir kullanıcıya ait.")
    if not stat.S_ISDIR(st.st_mode):
        raise PathError(f"{path} bir dizin değil.")
    if hasattr(os, "chmod"):
        os.chmod(path, mode)
