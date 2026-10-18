import json
import os
import unittest

from daemon_fakes import DaemonCase, FakeClock, rd
from limon.daemon.events import Event, EventCollector, KIND_UNIT_FAILED, make_fingerprint
from limon.daemon.store import AuditLog, Store


def ev(unit="a.service", kind=KIND_UNIT_FAILED):
    return Event(kind, unit, "critical", f"{unit} başarısız", make_fingerprint(kind, unit), {})


class DedupTests(DaemonCase):
    def setUp(self):
        super().setUp()
        os.makedirs(self.paths.state_dir)
        self.store = Store(self.paths.db)
        self.addCleanup(self.store.close)

    def test_same_event_is_deduplicated_while_open(self):
        eid, process = self.store.record_event(ev(), 600, 100)
        self.assertTrue(process)
        eid2, process2 = self.store.record_event(ev(), 600, 110)
        self.assertEqual(eid, eid2)
        self.assertFalse(process2)
        self.assertEqual(self.store.get_event(eid)["count"], 2)

    def test_cooldown_blocks_reprocessing_then_allows(self):
        eid, _ = self.store.record_event(ev(), 600, 100)
        self.store.update_event(eid, status="reported", last_processed=100)
        _, p = self.store.record_event(ev(), 600, 300)   # cooldown içinde
        self.assertFalse(p)
        eid3, p = self.store.record_event(ev(), 600, 800)  # cooldown geçti
        self.assertTrue(p)
        self.assertNotEqual(eid3, eid)  # geçmiş korunur, yeni kayıt açılır

    def test_resolved_then_quick_recurrence_is_suppressed(self):
        eid, _ = self.store.record_event(ev(), 600, 100)
        self.store.update_event(eid, status="resolved", last_processed=100)
        _, p = self.store.record_event(ev(), 600, 200)
        self.assertFalse(p)
        self.assertEqual(self.store.get_event(eid)["status"], "suppressed")

    def test_different_units_are_independent(self):
        _, p1 = self.store.record_event(ev("a.service"), 600, 100)
        _, p2 = self.store.record_event(ev("b.service"), 600, 100)
        self.assertTrue(p1 and p2)

    def test_resolve_missing_only_closes_cleared_conditions(self):
        a, _ = self.store.record_event(ev("a.service"), 600, 100)
        b, _ = self.store.record_event(ev("b.service"), 600, 100)
        self.store.update_event(a, status="reported")
        self.store.update_event(b, status="reported")
        n = self.store.resolve_missing((KIND_UNIT_FAILED,), {make_fingerprint(KIND_UNIT_FAILED, "b.service")}, 200)
        self.assertEqual(n, 1)
        self.assertEqual(self.store.get_event(a)["status"], "resolved")
        self.assertEqual(self.store.get_event(b)["status"], "reported")


class CollectorTests(DaemonCase):
    def setUp(self):
        super().setUp()
        os.makedirs(self.paths.state_dir)
        self.store = Store(self.paths.db)
        self.addCleanup(self.store.close)

    def collector(self, **kw):
        return EventCollector(self.make_cfg(**kw), self.platform, self.store, self.clock)

    def test_failed_unit_becomes_event(self):
        self.fail_unit("nginx.service")
        events = self.collector().collect()
        self.assertEqual([(e.kind, e.unit) for e in events], [("unit_failed", "nginx.service")])

    def test_ignore_and_watch_filters(self):
        self.fail_unit("a.service"); self.fail_unit("b.service")
        self.assertEqual([e.unit for e in self.collector(ignore_units=["a.*"]).collect()], ["b.service"])
        self.assertEqual([e.unit for e in self.collector(watch_units=["a.service"]).collect()], ["a.service"])

    def test_error_burst_threshold(self):
        self.logs.errors = {"w.service": {"count": 3, "sample": "x"}, "z.service": {"count": 9, "sample": "boom"}}
        events = self.collector(error_burst_threshold=5).collect()
        self.assertEqual([(e.kind, e.unit) for e in events], [("error_burst", "z.service")])

    def test_disk_levels(self):
        self.probe.disks = [{"mount": "/", "percent": 90, "free_bytes": 1}]
        e = self.collector().collect()
        self.assertEqual(e[0].kind, "disk_usage"); self.assertEqual(e[0].severity, "warning")
        self.probe.disks = [{"mount": "/", "percent": 97, "free_bytes": 1}]
        self.assertEqual(self.collector().collect()[0].severity, "critical")
        self.probe.disks = [{"mount": "/", "percent": 50, "free_bytes": 1}]
        self.assertEqual(self.collector().collect(), [])

    def test_flapping_uses_restart_counter_delta(self):
        c = self.collector(watch_units=["x.service"], flap_threshold=3)
        self.services.props["x.service"] = {"ActiveState": "active", "NRestarts": "1"}
        self.assertEqual(c.collect(), [])  # taban değer alınır
        self.services.props["x.service"] = {"ActiveState": "active", "NRestarts": "5"}
        events = c.collect()
        self.assertEqual([e.kind for e in events], ["unit_flapping"])


class RetentionTests(DaemonCase):
    def test_purge_old_events_but_keep_open(self):
        os.makedirs(self.paths.state_dir)
        st = Store(self.paths.db); self.addCleanup(st.close)
        old, _ = st.record_event(ev("old.service"), 1, 100)
        st.update_event(old, status="reported")
        openev, _ = st.record_event(ev("open.service"), 1, 100)   # new = açık
        st.purge(retention_days=1, max_events=1000, now=100 + 5 * 86400)
        self.assertIsNone(st.get_event(old))
        self.assertIsNotNone(st.get_event(openev))

    def test_audit_log_is_size_bounded_and_redacted(self):
        os.makedirs(self.paths.state_dir)
        a = AuditLog(self.paths.audit, max_bytes=2000, backups=2)
        for i in range(200):
            a.write("x", msg=f"satır {i} api_key=sk-ant-ABCDEFGHIJKLMNOPQRSTUV")
        files = [f for f in os.listdir(self.paths.state_dir) if f.startswith("audit.jsonl")]
        self.assertLessEqual(len(files), 3)
        total = sum(os.path.getsize(os.path.join(self.paths.state_dir, f)) for f in files)
        self.assertLess(total, 3 * 2200)
        content = rd(self.paths.audit)
        self.assertNotIn("sk-ant", content)
        if os.name != "nt":
            self.assertEqual(os.stat(self.paths.audit).st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
