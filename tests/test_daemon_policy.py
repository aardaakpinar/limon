import json
import os
import unittest

from daemon_fakes import DaemonCase, wr
from limon.daemon.actions import Action, parse_action
from limon.daemon.approvals import ApprovalError, Approvals
from limon.daemon.policy import APPROVAL, AUTO, DENY, Policy
from limon.daemon.store import Store


def restart(unit="app.service"):
    return Action("restart_service", unit=unit)


class PolicyTests(DaemonCase):
    def setUp(self):
        super().setUp()
        os.makedirs(self.paths.state_dir)
        self.store = Store(self.paths.db)
        self.addCleanup(self.store.close)
        self.event = {"id": 1, "unit": "app.service", "fix_attempts": 0, "kind": "unit_failed"}

    def pol(self, **kw):
        return Policy(self.make_cfg(**kw), self.store, self.clock)

    def test_default_report_mode_never_auto(self):
        d = self.pol().evaluate(restart(), self.event)
        self.assertEqual(d.verdict, APPROVAL)

    def test_auto_requires_explicit_unit_allowlist(self):
        self.assertEqual(self.pol(mode="auto").evaluate(restart(), self.event).verdict, APPROVAL)   # auto_units boş
        d = self.pol(mode="auto", auto_units=["app.service"]).evaluate(restart(), self.event)
        self.assertEqual(d.verdict, AUTO)

    def test_auto_action_type_allowlist(self):
        p = self.pol(mode="auto", auto_units=["app.service"], auto_actions=["reset_failed"])
        self.assertEqual(p.evaluate(restart(), self.event).verdict, APPROVAL)
        self.assertEqual(p.evaluate(Action("reset_failed", unit="app.service"), self.event).verdict, AUTO)

    def test_protected_units_never_auto(self):
        ev = dict(self.event, unit="sshd.service")
        d = self.pol(mode="auto", auto_units=["*"]).evaluate(restart("sshd.service"), ev)
        self.assertEqual(d.verdict, APPROVAL)
        self.assertGreaterEqual(d.risk, 6)

    def test_user_cannot_remove_default_protection(self):
        from limon.daemon.config import from_cfg
        cfg = from_cfg({"daemon": {"protected_units": ["foo.service"]}})
        self.assertIn("sshd*", cfg.protected_units)
        self.assertIn("foo.service", cfg.protected_units)

    def test_daemon_cannot_restart_itself(self):
        ev = dict(self.event, unit="limon-daemon.service")
        self.assertEqual(self.pol().evaluate(restart("limon-daemon.service"), ev).verdict, DENY)

    def test_target_must_relate_to_event(self):
        # log içindeki enjeksiyonun "sshd'yi yeniden başlat" dedirtmesi senaryosu
        d = self.pol(mode="auto", auto_units=["*"]).evaluate(restart("sshd.service"), self.event)
        self.assertEqual(d.verdict, DENY)
        self.assertIn("ilgili", d.describe())

    def test_mode_off_denies_everything_but_report(self):
        p = self.pol(mode="off")
        self.assertEqual(p.evaluate(restart(), self.event).verdict, DENY)
        self.assertEqual(p.evaluate(Action("report_only"), self.event).verdict, AUTO)

    def test_fix_attempt_cap_prevents_loops(self):
        ev = dict(self.event, fix_attempts=3)
        self.assertEqual(self.pol().evaluate(restart(), ev).verdict, DENY)

    def test_hourly_and_daily_caps(self):
        for _ in range(3):
            self.store.record_action("app.service", "restart_service", True, self.clock())
        d = self.pol().evaluate(restart(), self.event)
        self.assertEqual(d.verdict, DENY)
        self.assertIn("saatlik", d.describe())
        self.clock.advance(3700)
        self.assertEqual(self.pol().evaluate(restart(), self.event).verdict, APPROVAL)
        for i in range(20):
            self.store.record_action(f"u{i}.service", "restart_service", True, self.clock())
        self.assertIn("günlük", self.pol().evaluate(restart(), self.event).describe())

    # ---- edit_file ----
    def edit(self, path):
        return Action("edit_file", path=path, old_string="a", new_string="b")

    def test_edit_disabled_by_default(self):
        self.assertEqual(self.pol().evaluate(self.edit(os.path.join(self.tmp, "x.conf")), self.event).verdict, DENY)

    def test_edit_roots_traversal_symlink_and_sensitive(self):
        root = os.path.join(self.tmp, "allowed"); os.makedirs(root)
        outside = os.path.join(self.tmp, "outside"); os.makedirs(outside)
        wr(os.path.join(root, "a.conf"), "a")
        wr(os.path.join(outside, "secret.conf"), "a")
        p = self.pol(allowed_roots=[root], mode="auto", auto_units=["*"], auto_actions=["edit_file"])
        # izinli: yine de ASLA otomatik değil
        self.assertEqual(p.evaluate(self.edit(os.path.join(root, "a.conf")), self.event).verdict, APPROVAL)
        self.assertEqual(p.evaluate(self.edit(os.path.join(outside, "secret.conf")), self.event).verdict, DENY)
        self.assertEqual(p.evaluate(self.edit(os.path.join(root, "..", "outside", "secret.conf")), self.event).verdict, DENY)
        self.assertEqual(p.evaluate(self.edit("/etc/shadow"), self.event).verdict, DENY)
        try:
            os.symlink(os.path.join(outside, "secret.conf"), os.path.join(root, "link.conf"))
        except (OSError, NotImplementedError, AttributeError):
            pass  # simge bağlantısı oluşturulamayan platform (ör. yetkisiz Windows)
        else:
            self.assertEqual(p.evaluate(self.edit(os.path.join(root, "link.conf")), self.event).verdict, DENY)
        ssh = os.path.join(root, ".ssh"); os.makedirs(ssh)
        self.assertEqual(p.evaluate(self.edit(os.path.join(ssh, "authorized_keys")), self.event).verdict, DENY)


class ApprovalTests(DaemonCase):
    def setUp(self):
        super().setUp()
        os.makedirs(self.paths.state_dir)
        self.store = Store(self.paths.db)
        self.addCleanup(self.store.close)
        eid, _ = self.store.record_event(__import__("limon.daemon.events", fromlist=["x"]).Event("unit_failed", "a.service", "critical", "s", "fp", {}), 1, 1)
        self.eid = eid
        self.ap = Approvals(self.store, 3600, self.clock)

    def test_approve_and_reject_flow(self):
        t1 = self.ap.create(self.eid, restart(), 3, "neden")
        t2 = self.ap.create(self.eid, restart("b.service"), 3, "neden")
        self.assertEqual({t["id"] for t in self.ap.pending()}, {t1, t2})
        self.assertEqual(self.ap.approve(t1)["status"], "approved")
        self.assertEqual(self.ap.reject(t2)["status"], "rejected")
        self.assertEqual(self.ap.pending(), [])
        self.assertEqual([t["id"] for t in self.ap.approved()], [t1])

    def test_double_decision_and_unknown_ids(self):
        t = self.ap.create(self.eid, restart(), 3, "")
        self.ap.approve(t)
        with self.assertRaises(ApprovalError): self.ap.approve(t)
        with self.assertRaises(ApprovalError): self.ap.reject(t)
        with self.assertRaises(ApprovalError): self.ap.approve("deadbeef")

    def test_expired_tasks_cannot_be_approved(self):
        t = self.ap.create(self.eid, restart(), 3, "")
        self.clock.advance(3601)
        with self.assertRaises(ApprovalError): self.ap.approve(t)
        self.assertEqual(self.store.get_task(t)["status"], "expired")

    def test_tampered_task_is_refused(self):
        t = self.ap.create(self.eid, restart(), 3, "")
        self.store._db.execute("UPDATE tasks SET action=? WHERE id=?", (json.dumps({"type": "restart_service", "unit": "sshd.service"}), t))
        with self.assertRaises(ApprovalError) as cm: self.ap.approve(t)
        self.assertIn("parmak izi", str(cm.exception))
        self.assertEqual(self.store.get_task(t)["status"], "pending")


if __name__ == "__main__":
    unittest.main()
