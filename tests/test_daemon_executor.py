import os
import stat
import unittest
from unittest import mock

from daemon_fakes import DaemonCase, rd, wr
from limon.daemon.actions import Action
from limon.daemon.executor import Executor


class ExecutorTests(DaemonCase):
    def setUp(self):
        super().setUp()
        self.root = os.path.join(self.tmp, "etc-app"); os.makedirs(self.root)
        self.conf = os.path.join(self.root, "app.conf")
        wr(self.conf, "port=80\nmem=64M\n")
        os.chmod(self.conf, 0o640)
        os.makedirs(self.paths.state_dir)
        self.ex = Executor(self.make_cfg(allowed_roots=[self.root]), self.paths, self.services)

    def edit(self, old="mem=64M", new="mem=256M", path=None):
        return Action("edit_file", path=path or self.conf, old_string=old, new_string=new)

    def read(self):
        return rd(self.conf)

    def test_edit_makes_backup_and_writes_atomically(self):
        r = self.ex.execute(self.edit())
        self.assertTrue(r.ok, r.message)
        self.assertEqual(self.read(), "port=80\nmem=256M\n")
        self.assertEqual(rd(r.rollback["backup"]), "port=80\nmem=64M\n")
        self.assertEqual(os.path.dirname(r.rollback["backup"]), self.paths.backups)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(os.stat(self.conf).st_mode), 0o640)       # izinler korunur
            self.assertEqual(stat.S_IMODE(os.stat(r.rollback["backup"]).st_mode), 0o600)
        self.assertEqual([f for f in os.listdir(self.root) if f.startswith(".limon-")], [])  # geçici dosya kalmaz

    def test_failed_write_leaves_original_untouched(self):
        with mock.patch("limon.daemon.executor.os.replace", side_effect=OSError("disk dolu")):
            r = self.ex.execute(self.edit())
        self.assertFalse(r.ok)
        self.assertEqual(self.read(), "port=80\nmem=64M\n")
        self.assertEqual([f for f in os.listdir(self.root) if f.startswith(".limon-")], [])

    def test_ambiguous_or_missing_match_is_refused(self):
        self.assertFalse(self.ex.execute(self.edit(old="zzz")).ok)
        wr(self.conf, "a\na\n")
        r = self.ex.execute(self.edit(old="a", new="b"))
        self.assertFalse(r.ok)
        self.assertIn("2 kez", r.message)
        self.assertEqual(self.read(), "a\na\n")

    def test_paths_outside_roots_and_symlinks_are_refused(self):
        outside = os.path.join(self.tmp, "outside.conf"); wr(outside, "mem=64M")
        self.assertFalse(self.ex.execute(self.edit(path=outside)).ok)
        self.assertFalse(self.ex.execute(self.edit(path=os.path.join(self.root, "..", "outside.conf"))).ok)
        try:
            os.symlink(outside, os.path.join(self.root, "ln.conf"))
        except (OSError, NotImplementedError, AttributeError):
            pass
        else:
            self.assertFalse(self.ex.execute(self.edit(path=os.path.join(self.root, "ln.conf"))).ok)
        self.assertEqual(rd(outside), "mem=64M")

    def test_disabled_without_allowed_roots(self):
        ex = Executor(self.make_cfg(), self.paths, self.services)
        self.assertFalse(ex.execute(self.edit()).ok)

    def test_rollback_restores_and_validates_backup_location(self):
        r = self.ex.execute(self.edit())
        rb = self.ex.rollback(r.rollback)
        self.assertTrue(rb.ok, rb.message)
        self.assertEqual(self.read(), "port=80\nmem=64M\n")
        evil = os.path.join(self.tmp, "evil.bak"); wr(evil, "pwn")
        self.assertFalse(self.ex.rollback({"path": self.conf, "backup": evil}).ok)
        self.assertFalse(self.ex.rollback({"path": "/etc/hosts", "backup": r.rollback["backup"]}).ok)

    def test_service_actions_use_adapter_only(self):
        self.assertTrue(self.ex.execute(Action("restart_service", unit="app.service")).ok)
        self.assertTrue(self.ex.execute(Action("reset_failed", unit="app.service")).ok)
        self.assertEqual(self.services.calls, [("restart", "app.service"), ("reset_failed", "app.service")])
        self.assertFalse(self.ex.execute(Action("run_command")).ok)  # bilinmeyen tür


if __name__ == "__main__":
    unittest.main()
