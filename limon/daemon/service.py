"""Sürekli çalışan arka plan servisi: tara -> kaydet/tekilleştir -> teşhis -> politika ->
onay/yürütme -> doğrulama -> raporla. Tüm kalıcı durum store'dadır; yeniden başlatma güvenlidir."""

import json
import os
import signal
import threading
import time
from typing import Callable, Dict, List, Optional

from .. import __version__
from ..errors import ProviderError, humanize_provider_error
from .actions import ActionError, parse_action
from .approvals import ApprovalError, Approvals
from .config import DaemonConfig
from .diagnostics import Diagnoser, Diagnosis, DiagnosisError, _fmt_logs, collect_context
from .events import AUTO_RESOLVED_KINDS, KIND_MANUAL, Event, EventCollector, make_fingerprint
from .executor import Executor
from .ipc import IPCServer
from .paths import Paths, ensure_private_dir
from .policy import APPROVAL, AUTO, DENY, Policy
from .redact import safe
from .store import AuditLog, Store

MAX_DIAGNOSES_PER_TICK = 5


class Notifier:
    """Bildirim arayüzü. İlk sürümde yalnızca audit günlüğü; masaüstü bildirimi
    (notify-send, D-Bus) bu sınıftan türetilerek sonradan eklenebilir."""

    def notify(self, title: str, body: str, level: str = "info") -> None:
        pass


class AuditNotifier(Notifier):
    def __init__(self, audit: AuditLog):
        self.audit = audit

    def notify(self, title, body, level="info"):
        self.audit.write("notify", level=level, title=title, body=body)


class LimonDaemon:
    def __init__(self, cfg: DaemonConfig, paths: Paths, platform, provider_factory: Callable[[], object],
                 clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep,
                 notifier: Optional[Notifier] = None, enable_ipc: bool = True, search_backend=None):
        self.cfg, self.paths, self.platform = cfg, paths, platform
        self.provider_factory = provider_factory
        self.clock, self._sleep = clock, sleep
        self._provider = None
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._work_lock = threading.RLock()
        self._started = clock()
        self._last_purge = 0.0
        self._enable_ipc = enable_ipc
        self.store: Optional[Store] = None
        self.ipc: Optional[IPCServer] = None

        ensure_private_dir(paths.state_dir)
        self.store = Store(paths.db)
        self.audit = AuditLog(paths.audit, cfg.audit_max_bytes, cfg.audit_backups)
        self.notifier = notifier or AuditNotifier(self.audit)
        self.policy = Policy(cfg, self.store, clock)
        self.approvals = Approvals(self.store, cfg.approval_ttl, clock)
        self.executor = Executor(cfg, paths, platform.services)
        self.collector = EventCollector(cfg, platform, self.store, clock)
        self.searcher = None
        if search_backend is not None and cfg.web_search != "off" and cfg.web_search_max_rounds > 0:
            from .websearch import WebSearcher
            self.searcher = WebSearcher(search_backend, cfg, self.store, self.audit, clock)

    # ---- yaşam döngüsü -------------------------------------------------------------
    def start(self) -> None:
        rec = self.store.recover_after_restart()
        self.audit.write("daemon_start", version=__version__, mode=self.cfg.mode, scope=self.cfg.scope, recovered=rec)
        if self._enable_ipc:
            self.ipc = IPCServer(self.paths, self.handle_ipc, group=self.cfg.ipc_group)
            self.ipc.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def shutdown(self) -> None:
        if self.ipc:
            self.ipc.stop()
        self.audit.write("daemon_stop")
        if self.store:
            self.store.close()

    def run_forever(self) -> None:
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, lambda *_: self.stop())
        self.start()
        try:
            while not self._stop.is_set():
                try:
                    self.tick()
                except Exception as e:  # tek bir turdaki hata daemon'ı düşürmez
                    self.audit.write("tick_error", error=repr(e))
                self._wake.wait(self.cfg.poll_interval)
                self._wake.clear()
        finally:
            self.shutdown()

    # ---- bir tarama turu -----------------------------------------------------------
    def tick(self) -> None:
        now = self.clock()
        with self._work_lock:
            self.store.expire_tasks(now)
            self._scan(now)
            self._diagnose_due(now)
            self._run_approved()
            if now - self._last_purge > 3600:
                self.store.purge(self.cfg.retention_days, self.cfg.max_events, now)
                self._last_purge = now

    def _scan(self, now: float) -> None:
        try:
            events = self.collector.collect()
        except Exception as e:
            self.audit.write("collect_error", error=str(e))
            return  # kaynak okunamadıysa 'resolved' kararı VERME (yanlış çözüm işareti olmasın)
        active = set()
        for ev in events:
            active.add(ev.fingerprint)
            eid, process = self.store.record_event(ev, self.cfg.cooldown, now)
            if process:
                self.audit.write("event_new", id=eid, kind=ev.kind, unit=ev.unit, summary=ev.summary)
        n = self.store.resolve_missing(AUTO_RESOLVED_KINDS, active, now)
        if n:
            self.audit.write("events_resolved", count=n)

    def _diagnose_due(self, now: float) -> None:
        due = self.store.due_for_diagnosis(now)[:MAX_DIAGNOSES_PER_TICK]
        for row in due:
            if self.cfg.mode == "off":
                self.store.update_event(row["id"], status="reported", note="mod 'off': teşhis yapılmadı", last_processed=now)
                continue
            self.process_event(row["id"])

    # ---- teşhis ---------------------------------------------------------------------
    def _diagnoser(self) -> Diagnoser:
        if self._provider is None:
            self._provider = self.provider_factory()
        return Diagnoser(self._provider, self.searcher)

    @staticmethod
    def _targets(event: dict) -> List[str]:
        t = [event["unit"]] if event.get("unit") else []
        try:
            t += [u for u in json.loads(event.get("detail") or "{}").get("targets", []) if isinstance(u, str)]
        except ValueError:
            pass
        return t

    def process_event(self, event_id: int) -> Optional[Diagnosis]:
        with self._work_lock:
            if not self.store.claim_event(event_id):
                return None
            now = self.clock()
            self.store.update_event(event_id, last_processed=now)
            event = self.store.get_event(event_id)
            context = None
            if event["kind"] == KIND_MANUAL:  # elle teşhiste bağlam olay oluşturulurken hazırlanmıştır
                try:
                    context = json.loads(event.get("detail") or "{}").get("context")
                except ValueError:
                    pass
            if not context:
                context = collect_context(event, self.platform, self.cfg)
            try:
                diag = self._diagnoser().diagnose(context)
            except DiagnosisError as e:
                self._diagnosis_failed(event, f"AI yanıtı geçersiz: {e}", None)
                return None
            except Exception as e:  # sağlayıcı/ağ/anahtar hataları: olay kaybolmaz, sınırlı tekrar
                pe = e if isinstance(e, ProviderError) else humanize_provider_error(e)
                self._provider = None  # bir sonraki denemede istemciyi yeniden kur
                self._diagnosis_failed(event, str(pe), pe.retry_after)
                return None
            self._apply_plan(event_id, diag)
            return diag

    def _diagnosis_failed(self, event: dict, message: str, retry_after: Optional[float]) -> None:
        attempts = event["diag_attempts"] + 1
        now = self.clock()
        if attempts >= self.cfg.max_diagnosis_attempts:
            self.store.update_event(event["id"], status="diagnosis_failed", diag_attempts=attempts, note=message[:300])
            self.audit.write("diagnosis_gave_up", id=event["id"], attempts=attempts, error=message)
            self.notifier.notify("limon: teşhis yapılamadı", f"{event['summary']} — {message}", "warning")
            return
        backoff = max(retry_after or 0, min(3600, 30 * 2 ** (attempts - 1)))
        self.store.update_event(event["id"], status="pending_diagnosis", diag_attempts=attempts,
                                next_retry=now + backoff, note=message[:300])
        self.audit.write("diagnosis_retry", id=event["id"], attempts=attempts, retry_in=int(backoff), error=message)

    # ---- plan -> politika -> onay / yürütme ---------------------------------------------
    def _apply_plan(self, event_id: int, diag: Diagnosis) -> None:
        self.store.update_event(event_id, diagnosis=diag.to_json(), severity=diag.severity, diag_attempts=0)
        self.audit.write("diagnosis", id=event_id, summary=diag.summary, actions=[a.describe() for a in diag.actions],
                         rejected=diag.rejected)
        auto_tasks = []
        for action in diag.actions:
            if action.type == "report_only":
                continue
            event = self.store.get_event(event_id)
            d = self.policy.evaluate(action, event, self._targets(event))
            self.audit.write("policy", id=event_id, action=action.describe(), verdict=d.verdict, risk=d.risk, reasons=d.reasons)
            if d.verdict == DENY:
                self.store.add_task(event_id, action.to_dict(), action.digest(), d.risk, d.describe(), "denied", self.cfg.approval_ttl, self.clock())
            elif d.verdict == AUTO:
                auto_tasks.append(self.store.add_task(event_id, action.to_dict(), action.digest(), d.risk, d.describe(), "approved", self.cfg.approval_ttl, self.clock()))
            else:
                tid = self.approvals.create(event_id, action, d.risk, d.describe())
                self.notifier.notify("limon: onay bekliyor", f"{tid}: {action.describe()} (risk {d.risk}/10). Onay: limon approve {tid}", "warning")
        for tid in auto_tasks:
            self._execute_task(tid)
        self._finalize_event(event_id)

    def _run_approved(self) -> None:
        for t in self.approvals.approved():
            self._execute_task(t["id"])

    def _execute_task(self, task_id: str) -> None:
        with self._work_lock:
            if not self.store.transition_task(task_id, "approved", "executing", self.clock()):
                return
            task = self.store.get_task(task_id)
            event = self.store.get_event(task["event_id"])
            try:
                action = parse_action(json.loads(task["action"]))
                if action.digest() != task["digest"]:
                    raise ActionError("parmak izi uyuşmuyor")
            except (ActionError, ValueError) as e:
                self.store.update_task(task_id, status="blocked", result=f"eylem doğrulanamadı: {e}")
                return
            # Politika yürütme anında yeniden değerlendirilir; yalnızca kesin ret (DENY) engeller,
            # APPROVAL kararı zaten kullanıcı onayıyla karşılanmıştır.
            d = self.policy.evaluate(action, event, self._targets(event))
            if d.verdict == DENY:
                self.store.update_task(task_id, status="blocked", result="; ".join(d.reasons))
                self.audit.write("task_blocked", task=task_id, reasons=d.reasons)
                self._finalize_event(event["id"])
                return
            res = self.executor.execute(action)
            self.store.record_action(action.unit or action.path, action.type, res.ok, self.clock())
            self.store.update_event(event["id"], fix_attempts=event["fix_attempts"] + 1)
            self.store.update_task(task_id, status="executed" if res.ok else "failed", result=res.message[:500],
                                   rollback=json.dumps(res.rollback) if res.rollback else "")
            self.audit.write("task_executed", task=task_id, action=action.describe(), ok=res.ok, message=res.message)
            if res.ok and action.type == "restart_service" and self.cfg.verify_delay:
                self._sleep(self.cfg.verify_delay)
            self._finalize_event(event["id"])

    def _finalize_event(self, event_id: int) -> None:
        """Olayın tüm görevleri bittiyse sonucu doğrular; başarısızsa dosya değişikliklerini geri alır."""
        tasks = self.store.list_tasks(event_id=event_id)
        if any(t["status"] == "pending" for t in tasks):
            self.store.update_event(event_id, status="awaiting_approval")
            return
        if any(t["status"] in ("approved", "executing") for t in tasks):
            return
        executed = [t for t in tasks if t["status"] == "executed"]
        event = self.store.get_event(event_id)
        if not executed:
            self.store.update_event(event_id, status="reported")
            return
        unit = event.get("unit") or ""
        healthy = True
        if unit:
            try:
                healthy = self.platform.services.is_healthy(unit)
            except Exception as e:
                self.audit.write("verify_error", id=event_id, error=str(e))
                healthy = False
        if healthy:
            self.store.update_event(event_id, status="fixed")
            self.audit.write("event_fixed", id=event_id)
            self.notifier.notify("limon: düzeltildi", event["summary"], "info")
            return
        rolled = []
        for t in sorted(executed, key=lambda x: x["created"], reverse=True):
            if t["rollback"]:
                r = self.executor.rollback(json.loads(t["rollback"]))
                rolled.append(r.message)
                if r.ok:
                    self.store.update_task(t["id"], status="rolled_back", result=t["result"] + " | geri alındı")
        gave_up = event["fix_attempts"] >= self.cfg.max_fix_attempts_per_event
        self.store.update_event(event_id, status="gave_up" if gave_up else "fix_failed",
                                note=("; ".join(rolled) or "düzeltme sonrası servis hâlâ sağlıksız")[:300])
        self.audit.write("event_fix_failed", id=event_id, rolled_back=rolled, gave_up=gave_up)
        self.notifier.notify(
            "limon: düzeltme başarısız",
            f"{event['summary']}. " + ("Daha fazla otomatik deneme yapılmayacak; lütfen elle inceleyin." if gave_up else "Tekrar denenebilir."),
            "critical",
        )

    # ---- elle teşhis ---------------------------------------------------------------------
    def manual_diagnose(self, window: int) -> dict:
        """`limon diagnose --last 30m`: son pencerede hata veren birimleri ve sistem durumunu toplayıp
        normal teşhis hattına sokar (planlanan eylemler politika/onay kurallarına tabidir)."""
        failed, errors = [], {}
        try:
            failed = self.platform.services.list_failed()
        except Exception:
            pass
        try:
            errors = self.platform.logs.error_counts(window)
        except Exception:
            pass
        targets = sorted(set(failed) | set(errors))[:8]
        parts = [f"Elle teşhis isteği: son {window // 60} dakika.", f"Başarısız servisler: {failed or 'yok'}"]
        for u in targets:
            try:
                props = self.platform.services.show(u)
                logs = self.platform.logs.tail(u, min(self.cfg.journal_lines, 30), window)
                parts.append(f"--- {u} (Active={props.get('ActiveState')}, Sub={props.get('SubState')}, Result={props.get('Result')}) ---\n<veri>\n"
                             + _fmt_logs(logs, 1500).replace("</veri>", "") + "\n</veri>")
            except Exception as e:
                parts.append(f"--- {u}: bağlam alınamadı ({str(e)[:100]})")
        try:
            parts.append("Disk: " + ", ".join(f"{d['mount']} %{d['percent']}" for d in self.platform.probe.disk_usage(self.cfg.disk_mounts)))
        except Exception:
            pass
        context = safe("\n".join(parts), self.cfg.context_max_chars, keep_tail=False)
        ev = Event(KIND_MANUAL, "", "info", f"Elle teşhis (son {window // 60} dk)",
                   make_fingerprint(KIND_MANUAL, "", str(self.clock())), {"targets": targets, "context": context})
        eid, _ = self.store.record_event(ev, 0, self.clock())
        diag = self.process_event(eid)
        event = self.store.get_event(eid)
        if diag is None:
            return {"event_id": eid, "status": event["status"], "error": event["note"] if event["status"] != "diagnosing" else ""}
        return {
            "event_id": eid, "status": event["status"], "summary": diag.summary, "root_cause": diag.root_cause,
            "severity": diag.severity, "confidence": diag.confidence,
            "actions": [a.describe() for a in diag.actions], "rejected": diag.rejected,
            "tasks": [{"id": t["id"], "status": t["status"], "action": json.loads(t["action"]), "risk": t["risk"], "reasons": t["reasons"]}
                      for t in self.store.list_tasks(event_id=eid)],
        }

    # ---- IPC ------------------------------------------------------------------------------
    def handle_ipc(self, op: str, p: dict) -> dict:
        if op == "ping":
            return {"pong": True}
        if op == "status":
            open_ev = len([e for e in self.store.list_events(200) if e["status"] in ("new", "pending_diagnosis", "diagnosing", "awaiting_approval")])
            return {
                "version": __version__, "pid": os.getpid(), "mode": self.cfg.mode, "scope": self.cfg.scope,
                "uptime": int(self.clock() - self._started), "open_events": open_ev,
                "pending_approvals": len(self.approvals.pending()),
            }
        if op == "events":
            out = []
            for e in self.store.list_events(p.get("limit", 20)):
                diag = {}
                if e["diagnosis"]:
                    try:
                        diag = json.loads(e["diagnosis"])
                    except ValueError:
                        pass
                out.append({k: e[k] for k in ("id", "kind", "unit", "severity", "summary", "status", "count", "first_seen", "last_seen", "note")}
                           | {"diagnosis": diag.get("summary", ""), "root_cause": diag.get("root_cause", "")})
            return {"events": out}
        if op == "approvals":
            res = []
            for t in self.approvals.pending():
                ev = self.store.get_event(t["event_id"]) or {}
                res.append({"id": t["id"], "action": json.loads(t["action"]), "risk": t["risk"], "reasons": t["reasons"],
                            "event": ev.get("summary", ""), "expires": t["expires"], "created": t["created"]})
            return {"approvals": res}
        if op in ("approve", "reject"):
            try:
                t = self.approvals.approve(p["id"]) if op == "approve" else self.approvals.reject(p["id"])
            except ApprovalError as e:
                raise RuntimeError(str(e))
            self.audit.write("user_" + op, task=p["id"])
            if op == "approve":
                self._wake.set()  # ana döngü hemen yürütsün
            return {"id": t["id"], "status": t["status"]}
        if op == "diagnose":
            return self.manual_diagnose(p.get("window", 1800))
        raise RuntimeError("desteklenmeyen işlem")
