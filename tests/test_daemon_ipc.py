import json
import os
import socket
import stat
import sys
import tempfile
import shutil
import unittest

from daemon_fakes import rd, wr
from limon.daemon.ipc import IPCError, IPCServer, MAX_REQUEST_BYTES, request, validate_request
from limon.daemon.paths import Paths

posix = unittest.skipUnless(sys.platform.startswith("linux"), "Unix domain socket + SO_PEERCRED yalnızca Linux")


class ValidateTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_request({"op": "ping"}), ("ping", {}))
        self.assertEqual(validate_request({"op": "approve", "params": {"id": "deadbeef"}}), ("approve", {"id": "deadbeef"}))
        self.assertEqual(validate_request({"op": "events", "params": {"limit": 99999}})[1]["limit"], 200)
        self.assertEqual(validate_request({"op": "diagnose", "params": {"window": 1}})[1]["window"], 60)

    def test_invalid(self):
        bad = [[], "x", {"op": "shutdown"}, {"op": "approve"}, {"op": "approve", "params": {"id": "../../x"}},
               {"op": "approve", "params": {"id": "DEADBEEF"}}, {"op": "ping", "params": {"x": 1}},
               {"op": "events", "params": {"limit": "5"}}, {"op": "events", "params": {"limit": True}},
               {"op": "ping", "params": []}, {"op": 5}]
        for b in bad:
            with self.assertRaises(IPCError, msg=repr(b)):
                validate_request(b)


@posix
class ServerTests(unittest.TestCase):
    def setUp(self):
        base = tempfile.mkdtemp(prefix="lm", dir="/tmp")
        self.addCleanup(shutil.rmtree, base, True)
        self.paths = Paths("user", os.path.join(base, "s"), os.path.join(base, "r"))
        self.seen = []
        self.srv = IPCServer(self.paths, lambda op, p: self.seen.append((op, p)) or {"echo": op})
        self.srv.start()
        self.addCleanup(self.srv.stop)

    def raw(self, data: bytes) -> dict:
        s = socket.socket(socket.AF_UNIX); s.settimeout(3); s.connect(self.paths.socket)
        s.sendall(data)
        buf = b""
        while b"\n" not in buf:
            c = s.recv(4096)
            if not c: break
            buf += c
        s.close()
        return json.loads(buf)

    def test_roundtrip(self):
        self.assertEqual(request(self.paths, "ping", timeout=3), {"echo": "ping"})

    def test_socket_and_dir_permissions(self):
        self.assertEqual(stat.S_IMODE(os.stat(self.paths.socket).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.paths.runtime_dir).st_mode), 0o700)

    def test_unauthorized_peer_is_rejected_before_reading(self):
        self.srv._peer_check = lambda conn: False
        r = self.raw(b'{"op":"approve","params":{"id":"deadbeef"}}\n')
        self.assertFalse(r["ok"]); self.assertIn("yetkisiz", r["error"])
        self.assertEqual(self.seen, [])  # işleyiciye hiç ulaşmadı

    def test_default_peer_check_allows_same_user(self):
        self.assertTrue(request(self.paths, "ping", timeout=3))

    def test_malformed_and_oversized_requests(self):
        self.assertFalse(self.raw(b"bu json degil\n")["ok"])
        self.assertFalse(self.raw(b'{"op":"rm -rf"}\n')["ok"])
        self.assertFalse(self.raw(b"x" * (MAX_REQUEST_BYTES + 5000))["ok"])
        self.assertEqual(self.seen, [])

    def test_handler_errors_do_not_crash_server(self):
        def boom(op, p): raise RuntimeError("patladı")
        self.srv.handler = boom
        with self.assertRaises(RuntimeError): request(self.paths, "ping", timeout=3)
        self.srv.handler = lambda op, p: {"ok": 1}
        self.assertEqual(request(self.paths, "ping", timeout=3), {"ok": 1})

    def test_second_server_refused_and_stale_socket_replaced(self):
        with self.assertRaises(IPCError):
            IPCServer(self.paths, lambda o, p: {}).start()
        self.srv.stop()
        # ölü soket dosyası bırak
        s = socket.socket(socket.AF_UNIX); s.bind(self.paths.socket); s.close()
        srv2 = IPCServer(self.paths, lambda o, p: {"v": 2}); srv2.start(); self.addCleanup(srv2.stop)
        self.assertEqual(request(self.paths, "ping", timeout=3), {"v": 2})

    def test_non_socket_file_is_never_deleted(self):
        self.srv.stop()
        wr(self.paths.socket, "önemli")
        with self.assertRaises(IPCError): IPCServer(self.paths, lambda o, p: {}).start()
        self.assertEqual(rd(self.paths.socket), "önemli")

    def test_client_error_when_daemon_absent(self):
        self.srv.stop()
        with self.assertRaises(ConnectionError): request(self.paths, "ping", timeout=1)


if __name__ == "__main__":
    unittest.main()
