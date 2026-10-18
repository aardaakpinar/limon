"""systemd kurulum/kaldırma. İki kapsam:

  user   (varsayılan): ~/.config/systemd/user/limon-daemon.service, root GEREKMEZ, daemon
                       kullanıcının kendi yetkisiyle çalışır. Kullanıcı oturumu servislerini yönetir;
                       sistem servislerini yalnızca izler/okur (okuma için 'systemd-journal' grubu gerekebilir).
  system (--system):   /etc/systemd/system/limon-daemon.service, ayrı ve kısıtlı 'limon' kullanıcısı
                       (root DEĞİL). Kurulum için bir kez root gerekir; daemon root olarak çalışmaz.
                       Servis yönetimi sudo ile değil, yalnızca belirli birimlere ve yalnızca
                       restart/reset-failed eylemlerine izin veren bir polkit kuralıyla yapılır.

Tekrar çalıştırılabilir (idempotent): içerik aynıysa dosya yeniden yazılmaz."""

import os
import re
import shutil
import sys
import tempfile
from typing import Callable, Iterable, List, Optional

from .adapters import check_supported
from .proc import ProcResult, run as default_run

UNIT_NAME = "limon-daemon.service"
SERVICE_USER = "limon"
SYSTEM_UNIT_DIR = "/etc/systemd/system"
POLKIT_RULE = "/etc/polkit-1/rules.d/50-limon.rules"
SYSTEM_CONFIG_DIR = "/etc/limon"

_UNIT_NAME_RE = re.compile(r"^[A-Za-z0-9:_.@\-]+\.service$")


class InstallError(RuntimeError):
    pass


def _q(arg: str) -> str:
    """systemd ExecStart tırnaklama: ", \\, % ve $ kaçışları."""
    arg = arg.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%").replace("$", "$$")
    return f'"{arg}"'


def user_unit_dir() -> str:
    return os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "systemd", "user")


def unit_path(scope: str) -> str:
    return os.path.join(SYSTEM_UNIT_DIR if scope == "system" else user_unit_dir(), UNIT_NAME)


_COMMON_HARDENING = [
    "NoNewPrivileges=yes", "PrivateTmp=yes", "ProtectKernelTunables=yes", "ProtectKernelModules=yes",
    "ProtectControlGroups=yes", "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6", "RestrictNamespaces=yes",
    "LockPersonality=yes", "RestrictRealtime=yes", "RestrictSUIDSGID=yes", "SystemCallArchitectures=native",
    "UMask=0077",
]


def render_unit(scope: str, python_exe: str, allowed_roots: Iterable[str] = (), ipc_group: str = "") -> str:
    if scope not in ("user", "system"):
        raise InstallError("kapsam user veya system olmalı")
    exec_start = f"{_q(python_exe)} -m limon daemon run --scope {scope}"
    lines = [
        "[Unit]",
        f"Description=Limon AI sistem ajanı ({'sistem' if scope == 'system' else 'kullanıcı oturumu'})",
        "Documentation=https://github.com/aardaakpinar/limon",
    ]
    if scope == "system":
        lines.append("After=network-online.target systemd-journald.service")
    lines += ["StartLimitIntervalSec=300", "StartLimitBurst=5", "", "[Service]", "Type=simple",
              f"ExecStart={exec_start}", "Restart=on-failure", "RestartSec=10", "TimeoutStopSec=20"]
    lines += _COMMON_HARDENING
    lines += ["StateDirectory=limon", "StateDirectoryMode=0700", "RuntimeDirectory=limon",
              "RuntimeDirectoryMode=" + ("0750" if ipc_group else "0700")]
    if scope == "system":
        rw = " ".join(a for a in allowed_roots if a.startswith("/") and " " not in a)
        lines += [
            f"User={SERVICE_USER}", f"Group={SERVICE_USER}", "SupplementaryGroups=systemd-journal",
            f"Environment=LIMON_CONFIG_DIR={SYSTEM_CONFIG_DIR}",
            f"EnvironmentFile=-{SYSTEM_CONFIG_DIR}/limon.env",  # API anahtarları burada (0640 root:limon), unit'e gömülmez
            "ConfigurationDirectory=limon", "ConfigurationDirectoryMode=0750",
            "ProtectSystem=strict", "ProtectHome=yes", "PrivateDevices=yes", "ProtectClock=yes",
            "ProtectHostname=yes", "CapabilityBoundingSet=", "AmbientCapabilities=",
        ]
        if rw:
            lines.append(f"ReadWritePaths={rw}")
    lines += ["", "[Install]", "WantedBy=" + ("multi-user.target" if scope == "system" else "default.target"), ""]
    return "\n".join(lines)


def render_polkit_rule(units: Iterable[str]) -> str:
    """'limon' kullanıcısına YALNIZCA verilen birimler için restart / reset-failed izni."""
    names = sorted({u for u in units if _UNIT_NAME_RE.match(u)})
    if not names:
        raise InstallError("polkit kuralı için açık birim adı gerekli (watch_units / auto_units)")
    js_list = ", ".join('"' + n + '"' for n in names)
    return (
        "// limon-daemon: dar yetki. Yalnızca listelenen birimler, yalnızca restart/reset-failed.\n"
        "polkit.addRule(function(action, subject) {\n"
        '  if (subject.user !== "' + SERVICE_USER + '") return polkit.Result.NOT_HANDLED;\n'
        '  if (action.id !== "org.freedesktop.systemd1.manage-units") return polkit.Result.NOT_HANDLED;\n'
        "  var units = [" + js_list + "];\n"
        '  var verb = action.lookup("verb");\n'
        '  if ((verb === "restart" || verb === "reset-failed") && units.indexOf(action.lookup("unit")) !== -1) {\n'
        "    return polkit.Result.YES;\n"
        "  }\n"
        "  return polkit.Result.NO;\n"
        "});\n"
    )


def _atomic_write(path: str, content: str, mode: int = 0o644) -> bool:
    """İçerik aynıysa False; yazdıysa True."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            if f.read() == content:
                return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".limon-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return True


class Installer:
    def __init__(self, scope: str, python_exe: Optional[str] = None, runner: Callable[..., ProcResult] = default_run,
                 say: Callable[[str], None] = print, check: bool = True):
        self.scope = scope
        self.python_exe = python_exe or sys.executable
        self._run = runner
        self.say = say
        if check:
            check_supported()

    def _ctl(self, *args) -> ProcResult:
        argv = ["systemctl"] + (["--user"] if self.scope == "user" else []) + list(args)
        return self._run(argv, timeout=30)

    def _need(self, res: ProcResult, what: str):
        if not res.ok:
            raise InstallError(f"{what} başarısız: {(res.err or res.out).strip()[:300]}")

    def _preflight(self):
        if self.scope == "user":
            if hasattr(os, "geteuid") and os.geteuid() == 0:
                raise InstallError("Kullanıcı kapsamı root ile kurulmaz. Normal kullanıcıyla çalıştır, ya da --system kullan.")
            if not os.environ.get("XDG_RUNTIME_DIR"):
                raise InstallError("XDG_RUNTIME_DIR tanımlı değil: kullanıcı systemd oturumu yok. Bir masaüstü/ssh oturumundan çalıştır.")
        else:
            if os.geteuid() != 0:
                raise InstallError("Sistem kapsamı kurulumu için bir kez root gerekir (daemon root olarak ÇALIŞMAZ): sudo limon daemon install --system")
            exe = os.path.realpath(self.python_exe)
            if exe.startswith("/home/") or exe.startswith("/root/"):
                raise InstallError(
                    f"{exe} ev dizininde; 'limon' servis kullanıcısı buna erişemez (ProtectHome=yes). "
                    "limon'u herkesin okuyabildiği bir yere kurup --python ile göster, ör.: "
                    "python3 -m venv /opt/limon && /opt/limon/bin/pip install limon && "
                    "sudo limon daemon install --system --python /opt/limon/bin/python"
                )

    def install(self, allowed_roots=(), polkit_units=(), ipc_group="", enable: bool = True, start: bool = False) -> List[str]:
        self._preflight()
        done = []
        if self.scope == "system":
            if not shutil.which("useradd") and not self._user_exists():
                raise InstallError("'useradd' bulunamadı; 'limon' sistem kullanıcısını elle oluşturun.")
            if not self._user_exists():
                self._need(self._run(["useradd", "--system", "--user-group", "--home-dir", "/var/lib/limon",
                                      "--shell", "/usr/sbin/nologin", SERVICE_USER], timeout=30), "useradd")
                done.append(f"'{SERVICE_USER}' sistem kullanıcısı oluşturuldu")
            os.makedirs(SYSTEM_CONFIG_DIR, exist_ok=True)
            shutil.chown(SYSTEM_CONFIG_DIR, "root", SERVICE_USER)
            os.chmod(SYSTEM_CONFIG_DIR, 0o750)
            if polkit_units:
                if _atomic_write(POLKIT_RULE, render_polkit_rule(polkit_units)):
                    done.append(f"polkit kuralı yazıldı: {POLKIT_RULE}")
            else:
                done.append("polkit kuralı yazılmadı (watch_units/auto_units boş): servis yeniden başlatma eylemleri yetki hatası verir")
        unit = render_unit(self.scope, self.python_exe, allowed_roots, ipc_group)
        path = unit_path(self.scope)
        if _atomic_write(path, unit):
            done.append(f"unit yazıldı: {path}")
        else:
            done.append(f"unit zaten güncel: {path}")
        self._need(self._ctl("daemon-reload"), "systemctl daemon-reload")
        if enable:
            self._need(self._ctl("enable", UNIT_NAME), "systemctl enable")
            done.append("açılışta/oturumda otomatik başlatma etkin")
        if start:
            self._need(self._ctl("restart", UNIT_NAME), "systemctl restart")
            done.append("servis başlatıldı")
        return done

    def _user_exists(self) -> bool:
        try:
            import pwd
            pwd.getpwnam(SERVICE_USER)
            return True
        except (KeyError, ImportError):
            return False

    def uninstall(self, purge: bool = False, state_dir: Optional[str] = None) -> List[str]:
        done = []
        if self.scope == "system" and hasattr(os, "geteuid") and os.geteuid() != 0:
            raise InstallError("Sistem kapsamını kaldırmak için root gerekir: sudo limon daemon uninstall --system")
        self._ctl("disable", "--now", UNIT_NAME)  # kurulu değilse hata verir; sorun değil
        path = unit_path(self.scope)
        if os.path.exists(path):
            os.unlink(path)
            done.append(f"unit silindi: {path}")
        if self.scope == "system" and os.path.exists(POLKIT_RULE):
            os.unlink(POLKIT_RULE)
            done.append(f"polkit kuralı silindi: {POLKIT_RULE}")
        self._ctl("daemon-reload")
        if purge and state_dir and os.path.isdir(state_dir):
            shutil.rmtree(state_dir)
            done.append(f"durum dizini silindi: {state_dir}")
        elif state_dir:
            done.append(f"durum/audit verisi korundu: {state_dir} (silmek için --purge)")
        return done
