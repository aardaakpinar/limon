import http.server
import threading

import pytest

from limon import tools
from limon.agent import _assess_tool_call, build_system_prompt
from limon.tools import TOOL_DEFINITIONS

DEFS = {t["name"]: t for t in TOOL_DEFINITIONS}


def call(name, **args):
    return tools.TOOL_IMPLEMENTATIONS[name](args)


@pytest.fixture
def work(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "x.py").write_text("a = 1\nb = 2\nb = 2\nc = 3\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "y.txt").write_text("hello TODO\n")
    (tmp_path / ".env").write_text("SECRET=1 TODO\n")
    return tmp_path


def test_every_definition_has_implementation():
    assert set(DEFS) == set(tools.TOOL_IMPLEMENTATIONS)


def test_read_file_range(work):
    out = call("read_file", path="x.py", start_line=2, end_line=3)
    assert "satır 2-3 / 4" in out and "2\tb = 2" in out and "a = 1" not in out
    assert call("read_file", path="x.py", start_line=9).startswith("HATA")


def test_edit_file_unique_and_replace_all(work):
    assert "2 kez" in call("edit_file", path="x.py", old_string="b = 2", new_string="b = 5")
    assert call("edit_file", path="x.py", old_string="a = 1", new_string="a = 10").startswith("OK")
    assert "2 değişiklik" in call("edit_file", path="x.py", old_string="b = 2", new_string="b = 5", replace_all=True)
    assert (work / "x.py").read_text() == "a = 10\nb = 5\nb = 5\nc = 3\n"
    assert call("edit_file", path="x.py", old_string="zzz", new_string="q").startswith("HATA")


def test_backups_in_same_second_do_not_overwrite(work):
    for i in range(3):
        call("edit_file", path="x.py", old_string=f"c = {3 if i == 0 else i + 100}", new_string=f"c = {i + 101}")
    assert len(list((work / ".limon_backups").iterdir())) == 3


def test_grep_skips_secrets_and_bad_regex(work):
    out = call("grep", pattern="todo", ignore_case=True)
    assert "y.txt" in out and ".env" not in out
    assert call("grep", pattern="(").startswith("HATA")


def test_glob(work):
    out = call("glob", pattern="**/*.*")
    assert "x.py" in out and "y.txt" in out


@pytest.mark.parametrize("name,args,minimum", [
    ("read_file", {"path": "~/.ssh/id_rsa"}, 5),
    ("read_file", {"path": "~/.config/limon/config.json"}, 5),
    ("grep", {"pattern": "a", "path": "~/.aws"}, 5),
    ("web_fetch", {"url": "http://localhost:1/"}, 5),
    ("web_fetch", {"url": "http://169.254.169.254/latest"}, 5),
    ("edit_file", {"path": "/etc/hosts"}, 5),
])
def test_dangerous_calls_need_confirmation(name, args, minimum):
    assert _assess_tool_call(DEFS[name], args).score >= minimum


def test_plain_read_is_free():
    assert _assess_tool_call(DEFS["read_file"], {"path": "x.py"}).score == 0


def test_web_fetch_html_and_redirect(monkeypatch):
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/r":
                self.send_response(302)
                self.send_header("Location", "/p")
                self.end_headers()
                return
            body = b"<html><head><style>a{}</style></head><body><h1>Baslik</h1><p>Merhaba <b>dunya</b></p><script>evil()</script></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    out = call("web_fetch", url=f"http://127.0.0.1:{srv.server_port}/r")
    srv.shutdown()
    assert "Baslik" in out and "Merhaba dunya" in out and "evil" not in out
    assert call("web_fetch", url="file:///etc/passwd").startswith("HATA")


def test_run_command_timeout_is_clamped(monkeypatch):
    seen = {}
    monkeypatch.setattr(tools.subprocess, "run", lambda *a, **k: seen.update(k) or type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    call("run_command", command="true", timeout=99999)
    assert seen["timeout"] == 600


def test_project_instructions(tmp_path):
    (tmp_path / "LIMON.md").write_text("Hep Türkçe yaz.")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert "Hep Türkçe yaz." in build_system_prompt(str(deep))
