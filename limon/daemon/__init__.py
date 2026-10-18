"""
limon.daemon
------------
Arka planda çalışan, sistem olaylarına (systemd/journald) tepki veren AI sistem ajanı.

Tasarım ilkeleri:
  - Provider katmanından bağımsız gözlem/yürütme (adapters/), AI yalnızca teşhis üretir.
  - AI çıktısı asla doğrudan kabuğa gitmez: tipli eylemler (actions.py) -> politika (policy.py)
    -> onay (approvals.py) -> yürütücü (executor.py).
  - Varsayılan mod "report": hiçbir şey kendiliğinden uygulanmaz.
"""
