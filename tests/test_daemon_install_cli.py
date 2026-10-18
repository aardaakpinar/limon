import os
import subprocess
import sys
import time
import unittest
from unittest import mock

from daemon_fakes import DaemonCase, rd
from limon.daemon import install as inst
from limon.daemon.cli import parse_duration
from limon.daemon.config import DEFAULT_PROTECTED, from_cfg
from limon.daemon.proc import ProcResult, run


class UnitFileTests(unittest.TestCase):
    def test_user_unit(self):
        u = inst.render_unit("user", "/home/me/.limon/venv/bin/python")
        for needed in ("Restart=on-failure", "NoNewPrivileges=yes", "WantedBy=default.target", "UMask=0077",
                       "StateDirectory=limon", "RuntimeDirectory=limon", "daemon run --scope user"):
            self.assertIn(needed, u)
        self.assertNotIn("User=", u)                       # kullanıcı oturumunda servis kullanıcısı yok
        self.assertNotIn("ProtectHome", u)                 # kullanıcı yapılandırmasını okuyabilmeli

    def test_system_unit_is_not_root_and_sandboxed(self):
        u = inst.render_unit("system", "/opt/limon/bin/python", allowed_roots=["/etc/myapp", "/bad path"])
        for needed in ("User=limon", "Group=limon", "ProtectSystem=strict", "ProtectHome=yes", "CapabilityBoundingSet=",
                       "SupplementaryGroups=systemd-journal", "ReadWritePaths=/etc/myapp", "WantedBy=multi-user.target",
                       "EnvironmentFile=-/etc/limon/limon.env", "LIMON_CONFIG_DIR=/etc/limon"):
            self.assertIn(needed, u)
        self.assertNotIn("User=root", u)
        self.assertNotIn("/bad path", u)

    def test_no_secret_in_unit(self):
        env = {"ANTHROPIC_API_KEY": "sk-ant-SECRETSECRETSECRET1234", "OPENAI_API_KEY": "sk-SECRETSECRETSECRET1234"}
        with mock.patch.dict(os.environ, env):
            for scope in ("user", "system"):
                u = inst.render_unit(scope, sys.executable)
                self.assertNotIn("SECRET", u)
                self.assertNotIn("API_KEY=", u.replace("EnvironmentFile", ""))

    def test_exec_quoting(self):
        u = inst.render_unit("user", '/p ath/py"th%$')
        self.assertIn('ExecStart="/p ath/py\\"th%%$$"', u)

    def test_polkit_rule_is_narrow(self):
        r = inst.render_polkit_rule(["nginx.service", "app.service", "evil; drop", "../x"])
        self.assertIn('"app.service", "nginx.service"', r)
        self.assertNotIn("evil", r)
        self.assertIn('"restart" || verb === "reset-failed"', r)
        self.assertIn("polkit.Result.NO", r)
        with self.assertRaises(inst.InstallError):
            inst.render_polkit_rule([])
        with self.assertRaises(inst.InstallError):
            inst.render_polkit_rule(["*"])    # joker yok


@unittest.skipUnless(hasattr(os, "geteuid"), "systemd kurulumu yalnızca POSIX")
class InstallerTests(DaemonCase):
    def setUp(self):
        super().setUp()
        self.calls = []
        def runner(argv, timeout=20, max_output=0, env=None):
            self.calls.append(argv)
            return ProcResult(0, "", "")
        self.runner = runner
        env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": os.path.join(self.tmp, "cfg"), "XDG_RUNTIME_DIR": self.tmp})
        env.start(); self.addCleanup(env.stop)
        geteuid = mock.patch("limon.daemon.install.os.geteuid", return_value=1000)
        geteuid.start(); self.addCleanup(geteuid.stop)

    def installer(self, scope="user", **kw):
        return inst.Installer(scope, python_exe=sys.executable, runner=self.runner, say=lambda s: None, check=False, **kw)

    def test_user_install_is_idempotent_and_enables(self):
        out1 = self.installer().install()
        path = inst.unit_path("user")
        self.assertTrue(os.path.exists(path))
        self.assertTrue(any("unit yazıldı" in l for l in out1))
        first = rd(path)
        out2 = self.installer().install()
        self.assertTrue(any("zaten güncel" in l for l in out2))
        self.assertEqual(rd(path), first)
        self.assertIn(["systemctl", "--user", "enable", "limon-daemon.service"], self.calls)
        self.assertNotIn(["systemctl", "--user", "restart", "limon-daemon.service"], self.calls)  # kendiliğinden başlatmaz
        self.assertEqual([f for f in os.listdir(os.path.dirname(path)) if f.startswith(".limon")], [])

    def test_uninstall_removes_unit_but_keeps_state_unless_purged(self):
        self.installer().install()
        state = os.path.join(self.tmp, "state"); os.makedirs(state)
        out = self.installer().uninstall(purge=False, state_dir=state)
        self.assertFalse(os.path.exists(inst.unit_path("user")))
        self.assertTrue(os.path.isdir(state))
        self.assertTrue(any("korundu" in l for l in out))
        self.installer().uninstall(purge=True, state_dir=state)
        self.assertFalse(os.path.exists(state))
        self.installer().uninstall()          # tekrar çalıştırmak hata vermez

    def test_user_scope_refuses_root(self):
        with mock.patch("limon.daemon.install.os.geteuid", return_value=0):
            with self.assertRaises(inst.InstallError):
                self.installer().install()

    def test_system_scope_requires_root_and_readable_python(self):
        with self.assertRaises(inst.InstallError) as cm:
            self.installer("system").install()
        self.assertIn("root", str(cm.exception))
        with mock.patch("limon.daemon.install.os.geteuid", return_value=0):
            i = inst.Installer("system", python_exe="/home/bob/.limon/venv/bin/python", runner=self.runner, check=False)
            with self.assertRaises(inst.InstallError) as cm:
                i.install()
            self.assertIn("/opt/limon", str(cm.exception))

    def test_systemctl_failure_is_reported(self):
        bad = lambda argv, **k: ProcResult(1, "", "Failed to connect to bus")
        i = inst.Installer("user", python_exe=sys.executable, runner=bad, check=False)
        with self.assertRaises(inst.InstallError) as cm:
            i.install()
        self.assertIn("daemon-reload", str(cm.exception))


class PlatformTests(unittest.TestCase):
    def test_clear_error_without_systemd(self):
        from limon.daemon.adapters import UnsupportedPlatformError, check_supported
        with mock.patch("limon.daemon.adapters.sys.platform", "darwin"):
            with self.assertRaises(UnsupportedPlatformError) as cm:
                check_supported()
            self.assertIn("launchd", str(cm.exception))
        with mock.patch("limon.daemon.adapters.sys.platform", "linux"), \
             mock.patch("limon.daemon.adapters.systemd_available", return_value=False):
            with self.assertRaises(UnsupportedPlatformError) as cm:
                check_supported()
            self.assertIn("systemd", str(cm.exception))


class ConfigTests(unittest.TestCase):
    def test_defaults_are_safe(self):
        c = from_cfg({})
        self.assertEqual(c.mode, "report")
        self.assertEqual(c.scope, "user")
        self.assertEqual(c.auto_units, [])
        self.assertEqual(c.allowed_roots, [])

    def test_bad_values_fall_back_and_clamp(self):
        c = from_cfg({"daemon": {"mode": "yolo", "poll_interval": 1, "cooldown": "abc", "disk_warn": 500,
                                 "auto_units": "app", "scope": "root", "auto_max_risk": 99}})
        self.assertEqual(c.mode, "report")
        self.assertEqual(c.poll_interval, 5)
        self.assertEqual(c.cooldown, 3600)
        self.assertLessEqual(c.disk_warn, 99); self.assertGreater(c.disk_crit, c.disk_warn)
        self.assertEqual(c.auto_units, [])
        self.assertEqual(c.scope, "user")
        self.assertLessEqual(c.auto_max_risk, 5)
        self.assertEqual(from_cfg({"daemon": "bozuk"}).mode, "report")

    def test_existing_config_without_daemon_section_works(self):
        from limon import config as cfgmod
        self.assertNotIn("daemon", cfgmod.DEFAULTS)    # mevcut config biçimi değişmedi
        self.assertEqual(from_cfg(dict(cfgmod.DEFAULTS)).mode, "report")


class CliCompatTests(unittest.TestCase):
    def run_cli(self, *args, env=None):
        e = dict(os.environ, **(env or {}))
        e["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return subprocess.run([sys.executable, "-m", "limon", *args], capture_output=True, text=True, env=e, timeout=30)

    def test_existing_commands_still_parse(self):
        self.assertIn("limon", self.run_cli("--version").stdout)
        r = self.run_cli("--help")
        for cmd in ("config", "uninstall", "models", "update", "-p", "daemon", "events", "diagnose", "approvals", "approve", "reject"):
            self.assertIn(cmd, r.stdout)
        self.assertEqual(self.run_cli("models", "--help").returncode, 0)
        self.assertEqual(self.run_cli("update", "--help").returncode, 0)

    def test_daemon_subcommands_have_help(self):
        for args in (("daemon", "start", "-h"), ("daemon", "install", "-h"), ("diagnose", "-h"), ("approve", "-h")):
            self.assertEqual(self.run_cli(*args).returncode, 0, args)
        self.assertNotEqual(self.run_cli("daemon").returncode, 0)    # alt komut zorunlu

    def test_daemon_commands_do_not_trigger_setup_wizard(self):
        with __import__("tempfile").TemporaryDirectory() as d:
            env = {"HOME": d, "XDG_STATE_HOME": d, "XDG_RUNTIME_DIR": d, "LIMON_CONFIG_DIR": os.path.join(d, "c")}
            r = self.run_cli("approvals", env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn("Sağlayıcı seç", r.stdout)
            r = self.run_cli("events", env=env)
            self.assertEqual(r.returncode, 0)

    def test_parse_duration(self):
        self.assertEqual(parse_duration("30m"), 1800)
        self.assertEqual(parse_duration("2h"), 7200)
        self.assertEqual(parse_duration("90s"), 90)
        self.assertEqual(parse_duration("1d"), 86400)
        self.assertEqual(parse_duration("15"), 900)
        for bad in ("", "abc", "-5m", "1.5h", "5x"):
            with self.assertRaises(ValueError): parse_duration(bad)


class ProcTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "posix süreç grubu")
    def test_timeout_kills_process_group(self):
        t = time.time()
        r = run([sys.executable, "-c", "import time; time.sleep(30)"], timeout=1)
        self.assertTrue(r.timed_out)
        self.assertLess(time.time() - t, 8)

    def test_output_is_capped(self):
        r = run([sys.executable, "-c", "print('x'*500000)"], timeout=10, max_output=1000)
        self.assertEqual(len(r.out), 1000)
        self.assertTrue(r.truncated)

    @unittest.skipIf(os.name == "nt", "posix")
    def test_no_shell_and_minimal_env(self):
        r = run([sys.executable, "-c", "import os; print(os.environ.get('ANTHROPIC_API_KEY','yok'))"],
                env=None, timeout=10)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-gizli-deger-123456789"}):
            r = run([sys.executable, "-c", "import os; print(os.environ.get('ANTHROPIC_API_KEY','yok'))"], timeout=10)
        self.assertEqual(r.out.strip(), "yok")                  # API anahtarı alt sürece geçmez
        r = run(["echo", "a; touch /tmp/limon_pwned"], timeout=5)
        self.assertEqual(r.out.strip(), "a; touch /tmp/limon_pwned")
        self.assertFalse(os.path.exists("/tmp/limon_pwned"))
        self.assertEqual(run(["bu-komut-yok-xyz"], timeout=2).rc, 127)


if __name__ == "__main__":
    unittest.main()
