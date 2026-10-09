import json
import threading
import http.server

import pytest

from limon import models, update


class _Fake(http.server.BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        _Fake.seen.append((self.path, dict(self.headers)))
        p = self.path
        if p.startswith("/openai"):
            data = {"data": [{"id": "gpt-x"}, {"id": "text-embedding-3"}, {"id": "whisper-1"}]}
        elif p.startswith("/claude"):
            data = {"data": [{"id": "claude-a"}, {"id": "claude-b"}], "has_more": False}
        elif p.startswith("/gemini"):
            data = {"models": [{"name": "models/gemini-x", "supportedGenerationMethods": ["generateContent"]},
                               {"name": "models/embed", "supportedGenerationMethods": ["embedContent"]}]}
        elif p.startswith("/api/tags"):
            data = {"models": [{"name": "llama3.1:latest"}]}
        elif p.startswith("/bad"):
            self.send_response(401)
            self.end_headers()
            return
        out = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


@pytest.fixture
def server(monkeypatch):
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    base = f"http://127.0.0.1:{srv.server_port}"
    monkeypatch.setitem(models.ENDPOINTS, "openai", base + "/openai")
    monkeypatch.setitem(models.ENDPOINTS, "claude", base + "/claude")
    monkeypatch.setitem(models.ENDPOINTS, "gemini", base + "/gemini")
    yield base
    srv.shutdown()


def test_list_models_all_providers(server):
    _Fake.seen.clear()
    assert models.list_models("openai", "sk") == ["gpt-x"]
    assert models.list_models("claude", "ak") == ["claude-a", "claude-b"]
    assert models.list_models("gemini", "gk") == ["gemini-x"]
    assert models.list_models("ollama", ollama_host=server) == ["llama3.1:latest"]
    headers = {p.split("?")[0]: h for p, h in _Fake.seen}
    assert headers["/openai"]["Authorization"] == "Bearer sk"
    assert headers["/claude"]["x-api-key"] == "ak" and headers["/claude"]["anthropic-version"] == "2023-06-01"
    assert headers["/gemini"]["x-goog-api-key"] == "gk"


def test_list_models_auth_error(server, monkeypatch):
    monkeypatch.setitem(models.ENDPOINTS, "openai", server + "/bad")
    with pytest.raises(RuntimeError, match="401"):
        models.list_models("openai", "x")


def test_parse_version():
    assert update.parse_version("v0.10.0") > update.parse_version("0.9.9")
    assert update.parse_version("1.2.3rc1") == (1, 2, 3)


def test_run_update_when_current(monkeypatch):
    out = []
    monkeypatch.setattr(update, "latest_version", lambda: update.__version__)
    assert update.run_update(say=out.append) == 0
    assert "güncel" in out[0]


def test_install_kind_git(monkeypatch, tmp_path):
    monkeypatch.setenv("LIMON_HOME", str(tmp_path / "nohome"))
    assert update.install_kind() in ("git", "pip")
