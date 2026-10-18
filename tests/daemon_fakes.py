"""Daemon testleri için sahte (mock) bileşenler. Gerçek systemd/journald/sağlayıcı kullanılmaz."""

import json
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace as NS

from limon.daemon.adapters.base import HealthProbe, LogSource, ServiceManager
from limon.daemon.adapters import Platform
from limon.daemon.config import DaemonConfig
from limon.daemon.paths import Paths
from limon.daemon.service import LimonDaemon
from limon.providers.base import ChatResult, ToolCall


def rd(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def wr(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class FakeClock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s

    def advance(self, s):
        self.t += s


class FakeServices(ServiceManager):
    def __init__(self):
        self.failed = []
        self.props = {}
        self.healthy = {}          # birim -> bool
        self.restart_heals = True  # restart birimi düzeltir mi
        self.calls = []

    def list_failed(self):
        return list(self.failed)

    def show(self, unit):
        return dict(self.props.get(unit, {"ActiveState": "failed", "SubState": "failed", "Result": "exit-code", "NRestarts": "0"}))

    def is_healthy(self, unit):
        return self.healthy.get(unit, unit not in self.failed)

    def restart(self, unit):
        self.calls.append(("restart", unit))
        if self.restart_heals:
            self.healthy[unit] = True
            if unit in self.failed:
                self.failed.remove(unit)
        return True, "tamam"

    def reset_failed(self, unit):
        self.calls.append(("reset_failed", unit))
        return True, "tamam"


class FakeLogs(LogSource):
    def __init__(self):
        self.entries = {}
        self.errors = {}

    def tail(self, unit, lines, since_seconds=None):
        return list(self.entries.get(unit, []))

    def error_counts(self, since_seconds):
        return dict(self.errors)


class FakeProbe(HealthProbe):
    def __init__(self):
        self.disks = [{"mount": "/", "percent": 40, "free_bytes": 1}]

    def disk_usage(self, mounts):
        return list(self.disks)


class FakeProvider:
    """Sıradaki script öğesini döndürür: Exception -> fırlatır, dict -> submit_diagnosis çağrısı, str -> metin."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def chat(self, system_prompt, history, tools):
        self.calls.append({"system": system_prompt, "history": history, "tools": tools})
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, Exception):
            raise item
        if isinstance(item, tuple) and item[0] == "search":   # ("search", sorgu): web araması isteği
            return ChatResult(text="", tool_calls=[ToolCall(id="s", name="search_web", arguments={"query": item[1]})])
        if isinstance(item, tuple) and item[0] == "tool":      # ("tool", ad, argümanlar)
            return ChatResult(text="", tool_calls=[ToolCall(id="t", name=item[1], arguments=item[2])])
        if isinstance(item, dict):
            return ChatResult(text="", tool_calls=[ToolCall(id="1", name="submit_diagnosis", arguments=item)])
        return ChatResult(text=item, tool_calls=[])

    tool_outputs = None

    def append_tool_results(self, history, assistant_msg, tool_calls, results):
        self.tool_outputs = (self.tool_outputs or []) + list(results)
        history.append({"role": "assistant", "content": "(araç çağrısı)"})
        history.append({"role": "user", "content": "\n".join(results)})


def diag(actions=None, summary="Servis çöktü", severity="critical"):
    return {"summary": summary, "root_cause": "bellek yetersiz", "severity": severity, "confidence": 0.8, "actions": actions or []}


def log_entry(msg, prio=3):
    return {"ts": 1, "priority": prio, "ident": "app", "unit": "app.service", "message": msg}


class DaemonCase(unittest.TestCase):
    """Her test için geçici durum dizini + sahte platform + sahte saat."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="limon-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.clock = FakeClock()
        self.services, self.logs, self.probe = FakeServices(), FakeLogs(), FakeProbe()
        self.platform = Platform(self.services, self.logs, self.probe)
        self.paths = Paths("user", os.path.join(self.tmp, "state"), os.path.join(self.tmp, "run"))
        self.daemons = []

    def make_cfg(self, **kw):
        base = dict(mode="report", verify_delay=0, cooldown=600, poll_interval=30)
        base.update(kw)
        return DaemonConfig(**base)

    def make_daemon(self, provider, **cfg_kw):
        d = LimonDaemon(self.make_cfg(**cfg_kw), self.paths, self.platform, lambda: provider,
                        clock=self.clock, sleep=self.clock.sleep, enable_ipc=False)
        d.start()
        self.daemons.append(d)
        self.addCleanup(self._close, d)
        return d

    @staticmethod
    def _close(d):
        try:
            d.store.close()
        except Exception:
            pass

    def fail_unit(self, unit="app.service"):
        if unit not in self.services.failed:
            self.services.failed.append(unit)
        self.services.healthy[unit] = False
        self.logs.entries[unit] = [log_entry("Out of memory: killed process")]
