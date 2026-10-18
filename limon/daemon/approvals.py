"""Onay bekleyen işlemler. Etkileşimli terminal yoktur: görevler kalıcı kuyruğa konur,
kullanıcı başka bir terminalden `limon approve <id>` ile onaylar. Onay, eylemin parmak
iziyle (digest) bağlıdır; kayıt değiştirilirse yürütülmez."""

import json
import time
from typing import Callable, List, Optional

from .actions import Action, ActionError, parse_action
from .store import Store


class ApprovalError(Exception):
    pass


class Approvals:
    def __init__(self, store: Store, ttl: int, clock: Callable[[], float] = time.time):
        self.store, self.ttl, self.clock = store, ttl, clock

    def create(self, event_id: int, action: Action, risk: int, reasons: str) -> str:
        return self.store.add_task(
            event_id, action.to_dict(), action.digest(), risk, reasons, "pending", self.ttl, self.clock()
        )

    def pending(self) -> List[dict]:
        self.store.expire_tasks(self.clock())
        return self.store.list_tasks(["pending"])

    def approve(self, task_id: str) -> dict:
        self.store.expire_tasks(self.clock())
        t = self.store.get_task(task_id)
        if not t:
            raise ApprovalError(f"görev bulunamadı: {task_id}")
        if t["status"] != "pending":
            raise ApprovalError(f"görev bekleyen durumda değil (durum: {t['status']})")
        try:
            if parse_action(json.loads(t["action"])).digest() != t["digest"]:
                raise ApprovalError("görev kaydı değiştirilmiş (parmak izi uyuşmuyor); onaylanamaz")
        except (ActionError, ValueError):
            raise ApprovalError("görevdeki eylem geçersiz; onaylanamaz")
        if not self.store.transition_task(task_id, "pending", "approved", self.clock()):
            raise ApprovalError("görev başka bir istekle zaten işlendi")
        return self.store.get_task(task_id)

    def reject(self, task_id: str) -> dict:
        t = self.store.get_task(task_id)
        if not t:
            raise ApprovalError(f"görev bulunamadı: {task_id}")
        if not self.store.transition_task(task_id, "pending", "rejected", self.clock()):
            raise ApprovalError(f"görev bekleyen durumda değil (durum: {t['status']})")
        return self.store.get_task(task_id)

    def approved(self) -> List[dict]:
        return self.store.list_tasks(["approved"])
