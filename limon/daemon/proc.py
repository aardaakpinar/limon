"""Güvenli alt süreç çalıştırma: kabuk yok (argv listesi), zaman aşımı, çıktı sınırı,
süreç grubu temizliği ve minimal ortam."""

import os
import subprocess
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional

_ENV_KEEP = ("PATH", "LANG", "LC_ALL", "HOME", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS")


@dataclass
class ProcResult:
    rc: int
    out: str
    err: str
    timed_out: bool = False
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.rc == 0 and not self.timed_out


Runner = Callable[..., ProcResult]


def _drain(stream, cap: int, sink: list, flag: list):
    total = 0
    while True:
        chunk = stream.read(4096)
        if not chunk:
            break
        if total < cap:
            sink.append(chunk[: cap - total])
        if total + len(chunk) > cap:
            flag[0] = True
        total += len(chunk)


def run(argv: List[str], timeout: int = 20, max_output: int = 200_000, env: Optional[dict] = None) -> ProcResult:
    if not argv or not all(isinstance(a, str) for a in argv):
        raise ValueError("argv boş olamaz ve yalnızca metin içermeli")
    base_env = {k: os.environ[k] for k in _ENV_KEEP if k in os.environ}
    base_env.setdefault("LANG", "C.UTF-8")
    base_env.update(env or {})
    try:
        p = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=base_env, start_new_session=True,
        )
    except OSError as e:
        return ProcResult(rc=127, out="", err=f"çalıştırılamadı: {e}")
    out_b, err_b, flag = [], [], [False]
    threads = [
        threading.Thread(target=_drain, args=(p.stdout, max_output, out_b, flag), daemon=True),
        threading.Thread(target=_drain, args=(p.stderr, max_output, err_b, flag), daemon=True),
    ]
    for t in threads:
        t.start()
    timed_out = False
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(p.pid, 9)
        except (ProcessLookupError, PermissionError, AttributeError):
            p.kill()
        p.wait()
    for t in threads:
        t.join(timeout=2)
    for stream in (p.stdout, p.stderr):  # uzun ömürlü daemon'da dosya tanıtıcısı sızmasın
        try:
            stream.close()
        except OSError:
            pass
    dec = lambda parts: b"".join(parts).decode("utf-8", errors="replace")
    return ProcResult(rc=p.returncode if p.returncode is not None else -1, out=dec(out_b), err=dec(err_b),
                      timed_out=timed_out, truncated=flag[0])
