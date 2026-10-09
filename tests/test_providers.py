import json
import sys
import threading
import http.server
from types import SimpleNamespace as NS

from limon.agent import Agent, ToolDecision
from limon.providers import create_provider


def test_claude_history_format(monkeypatch):
    calls = []

    class Msgs:
        def create(self, **kw):
            calls.append(kw)
            if len(calls) == 1:
                return NS(content=[NS(type="text", text="bakıyorum"),
                                   NS(type="tool_use", id="tu1", name="list_dir", input={"path": "."})])
            return NS(content=[NS(type="text", text="bitti")])

    monkeypatch.setitem(sys.modules, "anthropic", NS(Anthropic=lambda api_key: NS(messages=Msgs())))
    assert Agent(create_provider("claude", "k", "m")).run_turn("ls", ToolDecision()) == "bitti"
    hist = calls[1]["messages"]
    assert hist[1]["content"] == [{"type": "text", "text": "bakıyorum"},
                                  {"type": "tool_use", "id": "tu1", "name": "list_dir", "input": {"path": "."}}]
    assert hist[2]["content"][0]["tool_use_id"] == "tu1"


def test_openai_history_format(monkeypatch):
    calls = []

    class Comp:
        def create(self, **kw):
            calls.append(json.loads(json.dumps(kw, default=lambda o: o.__dict__)))
            if len(calls) == 1:
                tc = NS(id="c1", function=NS(name="get_current_datetime", arguments="{}"))
                return NS(choices=[NS(message=NS(content=None, tool_calls=[tc]))])
            return NS(choices=[NS(message=NS(content="tamam", tool_calls=None))])

    monkeypatch.setitem(sys.modules, "openai", NS(OpenAI=lambda api_key: NS(chat=NS(completions=Comp()))))
    assert Agent(create_provider("openai", "k", "m")).run_turn("saat", ToolDecision()) == "tamam"
    msgs = calls[1]["messages"]
    assert msgs[2]["tool_calls"][0]["id"] == "c1" and msgs[3]["tool_call_id"] == "c1"


def test_ollama_keeps_tool_calls_in_history(monkeypatch):
    seen = []

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(body)
            if not any(m["role"] == "tool" for m in body["messages"]):
                msg = {"role": "assistant", "content": "",
                       "tool_calls": [{"function": {"name": "get_current_datetime", "arguments": {}}}]}
            else:
                msg = {"role": "assistant", "content": "Tamam."}
            out = json.dumps({"message": msg}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    p = create_provider("ollama", "", "llama3.1", ollama_host=f"http://127.0.0.1:{srv.server_port}")
    assert Agent(p).run_turn("saat?", ToolDecision()) == "Tamam."
    srv.shutdown()
    assistant = seen[1]["messages"][2]
    assert assistant["tool_calls"][0]["function"]["name"] == "get_current_datetime"
    assert seen[1]["messages"][3]["tool_name"] == "get_current_datetime"
