"""Daemon <-> CLI yerel iletişimi: Unix domain socket, satır tabanlı JSON.
Ağ üzerinden erişim YOKTUR. Güvenlik katmanları:
  1. Runtime dizini 0700, soket 0600 (ipc_group tanımlıysa 0660 + grup),
  2. Her bağlantıda SO_PEERCRED ile eş kimliği (uid) denetimi,
  3. İstek boyutu/şema doğrulaması, yalnızca izinli işlemler."""

import json
import os
import re
import socket
import stat
import struct
import threading
from typing import Callable, Dict, Optional

from .paths import Paths, ensure_private_dir

MAX_REQUEST_BYTES = 64 * 1024
ID_RE = re.compile(r"^[0-9a-f]{8}$")

# işlem -> {parametre: tür}
OPS: Dict[str, Dict[str, type]] = {
    "ping": {}, "status": {}, "approvals": {},
    "events": {"limit": int},
    "approve": {"id": str}, "reject": {"id": str},
    "diagnose": {"window": int},
}


class IPCError(Exception):
    pass


def validate_request(obj) -> tuple:
    if not isinstance(obj, dict):
        raise IPCError("istek bir JSON nesnesi olmalı")
    op = obj.get("op")
    if op not in OPS:
        raise IPCError("bilinmeyen işlem")
    params = obj.get("params", {})
    if not isinstance(params, dict):
        raise IPCError("params nesne olmalı")
    spec = OPS[op]
    clean = {}
    for k, v in params.items():
        if k not in spec:
            raise IPCError(f"beklenmeyen parametre: {str(k)[:30]}")
        if isinstance(v, bool) or not isinstance(v, spec[k]):
            raise IPCError(f"'{k}' türü geçersiz")
        clean[k] = v
    if op in ("approve", "reject") and not ID_RE.match(clean.get("id", "")):
        raise IPCError("geçersiz görev kimliği")
    if "limit" in clean:
        clean["limit"] = max(1, min(clean["limit"], 200))
    if "window" in clean:
        clean["window"] = max(60, min(clean["window"], 7 * 86400))
    return op, clean


def peer_credentials(conn: socket.socket) -> tuple:
    """(pid, uid, gid) — yalnızca Linux (SO_PEERCRED)."""
    data = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    return struct.unpack("3i", data)


def peer_allowed(uid: int, gid: int, group_name: str = "") -> bool:
    if uid == os.geteuid() or uid == 0:
        return True
    if group_name:
        try:
            import grp
            import pwd
            g = grp.getgrnam(group_name)
            name = pwd.getpwuid(uid).pw_name
            return g.gr_gid == gid or name in g.gr_mem or g.gr_gid in os.getgrouplist(name, gid)
        except (KeyError, OSError):
            return False
    return False


class IPCServer:
    def __init__(self, paths: Paths, handler: Callable[[str, dict], dict], group: str = "",
                 peer_check: Optional[Callable[[socket.socket], bool]] = None):
        self.paths, self.handler, self.group = paths, handler, group
        self._peer_check = peer_check or self._default_peer_check
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def _default_peer_check(self, conn) -> bool:
        _pid, uid, gid = peer_credentials(conn)
        return peer_allowed(uid, gid, self.group)

    def start(self) -> None:
        sock_path = self.paths.socket
        if len(sock_path.encode()) > 100:
            raise IPCError(f"soket yolu çok uzun: {sock_path}")
        ensure_private_dir(self.paths.runtime_dir, 0o750 if self.group else 0o700)
        if self.group:
            try:
                import grp
                os.chown(self.paths.runtime_dir, -1, grp.getgrnam(self.group).gr_gid)
            except (KeyError, PermissionError, OSError):
                pass
        if os.path.lexists(sock_path):
            if not stat.S_ISSOCK(os.lstat(sock_path).st_mode):
                raise IPCError(f"{sock_path} bir soket değil, silinmedi.")
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            probe.settimeout(1)
            try:
                probe.connect(sock_path)
                raise IPCError("başka bir limon daemon zaten çalışıyor (soket yanıt veriyor).")
            except (ConnectionRefusedError, FileNotFoundError, socket.timeout):
                os.unlink(sock_path)  # eski/ölü soket
            finally:
                probe.close()
        old = os.umask(0o177)  # bind ile chmod arasında açık pencere kalmasın
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.bind(sock_path)
        finally:
            os.umask(old)
        if self.group:
            try:
                import grp
                os.chown(sock_path, -1, grp.getgrnam(self.group).gr_gid)
                os.chmod(sock_path, 0o660)
            except (KeyError, PermissionError, OSError):
                os.chmod(sock_path, 0o600)
        else:
            os.chmod(sock_path, 0o600)
        s.listen(8)
        s.settimeout(0.5)
        self._sock = s
        self._thread = threading.Thread(target=self._loop, name="limon-ipc", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        if self._sock:
            self._sock.close()
        try:
            os.unlink(self.paths.socket)
        except OSError:
            pass

    def _loop(self):
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _reply(self, conn, obj: dict):
        try:
            conn.sendall((json.dumps(obj, ensure_ascii=False, default=str) + "\n").encode())
        except OSError:
            pass

    def _serve(self, conn: socket.socket):
        with conn:
            conn.settimeout(5)
            try:
                if not self._peer_check(conn):
                    self._reply(conn, {"ok": False, "error": "yetkisiz: bu kullanıcı daemon'a erişemez"})
                    return
            except Exception:
                self._reply(conn, {"ok": False, "error": "eş kimliği doğrulanamadı"})
                return
            buf = b""
            try:
                while b"\n" not in buf:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    if len(buf) > MAX_REQUEST_BYTES:
                        self._reply(conn, {"ok": False, "error": "istek çok büyük"})
                        return
                line = buf.split(b"\n", 1)[0]
                op, params = validate_request(json.loads(line.decode("utf-8")))
            except (IPCError, ValueError, UnicodeDecodeError) as e:
                self._reply(conn, {"ok": False, "error": f"geçersiz istek: {e}"})
                return
            except OSError:
                return
            conn.settimeout(150)  # diagnose gibi uzun işlemler için
            try:
                self._reply(conn, {"ok": True, "result": self.handler(op, params)})
            except Exception as e:
                self._reply(conn, {"ok": False, "error": str(e)[:300]})


def request(paths: Paths, op: str, params: Optional[dict] = None, timeout: float = 150) -> dict:
    """CLI tarafı. Daemon yoksa ConnectionError fırlatır."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(paths.socket)
    except (FileNotFoundError, ConnectionRefusedError, PermissionError) as e:
        s.close()
        raise ConnectionError(f"daemon'a bağlanılamadı ({paths.socket}): {e}")
    try:
        s.sendall((json.dumps({"op": op, "params": params or {}}) + "\n").encode())
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        resp = json.loads(buf.decode("utf-8"))
    finally:
        s.close()
    if not resp.get("ok"):
        raise RuntimeError(resp.get("error", "bilinmeyen hata"))
    return resp["result"]
