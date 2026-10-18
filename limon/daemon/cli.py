"""`limon daemon|events|diagnose|approvals|approve|reject` komutları.
Ana cli.py yalnızca ayrıştırıcıları ekler ve buraya devreder; mevcut komutlar etkilenmez."""

import datetime
import os
import re
import sys
from typing import Optional

from .. import config as cfgmod

SCOPE_HELP = "kapsam: user (varsayılan, root gerekmez) | system"


def parse_duration(text: str) -> int:
    """'30m', '2h', '1d', '90s' -> saniye."""
    m = re.fullmatch(r"\s*(\d+)\s*([smhd]?)\s*", text or "")
    if not m:
        raise ValueError(f"geçersiz süre: {text!r} (örn. 30m, 2h, 1d)")
    n, unit = int(m.group(1)), m.group(2) or "m"
    return n * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]


def add_parsers(sub) -> None:
    def scope_arg(p):
        p.add_argument("--scope", choices=["user", "system"], help=SCOPE_HELP)

    p = sub.add_parser("daemon", help="Arka plan sistem ajanı (systemd) yönetimi")
    ds = p.add_subparsers(dest="daemon_cmd", required=True)
    for name, h in (("start", "daemon'ı başlat (systemd)"), ("stop", "daemon'ı durdur"), ("status", "daemon durumunu göster"),
                    ("run", "ön planda çalıştır (systemd bu komutu kullanır)")):
        sp = ds.add_parser(name, help=h)
        scope_arg(sp)
    pi = ds.add_parser("install", help="systemd servis dosyasını kur")
    scope_arg(pi)
    pi.add_argument("--system", action="store_true", help="sistem geneli kurulum (ayrı 'limon' kullanıcısı, bir kez root gerekir)")
    pi.add_argument("--python", help="servisin kullanacağı Python (varsayılan: şu anki yorumlayıcı)")
    pi.add_argument("--start", action="store_true", help="kurulumdan sonra başlat")
    pu = ds.add_parser("uninstall", help="systemd servisini kaldır")
    scope_arg(pu)
    pu.add_argument("--system", action="store_true")
    pu.add_argument("--purge", action="store_true", help="durum/audit verisini de sil")

    pe = sub.add_parser("events", help="Daemon'ın kaydettiği sistem olaylarını listele")
    scope_arg(pe)
    pe.add_argument("-n", "--limit", type=int, default=20)
    pd = sub.add_parser("diagnose", help="Son dönemdeki sistem sorunlarını AI ile teşhis et (eylem uygulamaz)")
    scope_arg(pd)
    pd.add_argument("--last", default="30m", help="geriye bakış süresi (örn. 30m, 2h)")
    pa = sub.add_parser("approvals", help="Onay bekleyen işlemleri listele")
    scope_arg(pa)
    for name, h in (("approve", "bekleyen işlemi onayla"), ("reject", "bekleyen işlemi reddet")):
        sp = sub.add_parser(name, help=h)
        scope_arg(sp)
        sp.add_argument("task_id", help="görev kimliği (limon approvals ile görülür)")


def _c():
    from .. import cli as m
    return m


def _ts(t: float) -> str:
    return datetime.datetime.fromtimestamp(t).strftime("%m-%d %H:%M:%S") if t else "-"


def _setup(args, cfg: dict):
    from .config import from_cfg
    from .paths import resolve_paths
    dcfg = from_cfg(cfg)
    scope = getattr(args, "scope", None) or ("system" if getattr(args, "system", False) else None) or dcfg.scope
    dcfg.scope = scope
    return dcfg, resolve_paths(scope)


def make_provider_factory(cfg: dict):
    """Daemon için provider kurucu. cli.build_provider gibi sys.exit ETMEZ: hata fırlatır,
    daemon bunu sınırlı tekrar denemeyle ele alır."""
    from ..providers import create_provider

    def factory():
        name = cfg["provider"]
        key = cfgmod.get_api_key(cfg, name)
        if name != "ollama" and not key:
            raise RuntimeError(f"{name} için API anahtarı bulunamadı (401 yetkisiz): config.json veya ortam dosyasını kontrol edin")
        return create_provider(name, api_key=key, model=cfg["model"], ollama_host=cfg.get("ollama_host", ""))
    return factory


def dispatch(args) -> Optional[int]:
    """Daemon ile ilgili komut ise çalıştırıp çıkış kodu döndürür; değilse None."""
    cmd = args.command
    if cmd not in ("daemon", "events", "diagnose", "approvals", "approve", "reject"):
        return None
    c = _c()
    try:
        cfg = cfgmod.load_config()
        dcfg, paths = _setup(args, cfg)
        if cmd == "daemon":
            return _daemon(args, cfg, dcfg, paths)
        return _client(args, cmd, dcfg, paths)
    except Exception as e:
        from .adapters.base import UnsupportedPlatformError
        from .install import InstallError
        if isinstance(e, (UnsupportedPlatformError, InstallError, ValueError, ConnectionError)):
            print(f"{c.RED}Hata: {e}{c.RESET}")
            return 1
        raise


def _ctl(dcfg, *a):
    from .proc import run
    return run(["systemctl"] + (["--user"] if dcfg.scope == "user" else []) + list(a), timeout=30)


def _daemon(args, cfg, dcfg, paths) -> int:
    from .adapters import check_supported
    from .install import Installer, UNIT_NAME
    from .ipc import request
    c = _c()
    sub = args.daemon_cmd

    if sub == "run":
        return _run_foreground(cfg, dcfg, paths)

    if sub in ("start", "stop"):
        check_supported()
        res = _ctl(dcfg, sub, UNIT_NAME)
        if not res.ok:
            hint = " Önce: limon daemon install" if "not found" in res.err.lower() or "not-found" in res.err.lower() else ""
            print(f"{c.RED}Hata: systemctl {sub} başarısız: {res.err.strip()[:200]}{c.RESET}{hint}")
            return 1
        print(f"{c.GREEN}✓ daemon {'başlatıldı' if sub == 'start' else 'durduruldu'} ({dcfg.scope}){c.RESET}")
        return 0

    if sub == "status":
        active = enabled = "?"
        try:
            check_supported()
            active = (_ctl(dcfg, "is-active", UNIT_NAME).out.strip() or "?")
            enabled = (_ctl(dcfg, "is-enabled", UNIT_NAME).out.strip() or "?")
        except Exception as e:
            print(f"{c.DIM}systemd bilgisi alınamadı: {e}{c.RESET}")
        print(f"{c.BOLD}limon daemon{c.RESET} (kapsam: {dcfg.scope})  servis: {active}  otomatik başlatma: {enabled}")
        try:
            st = request(paths, "status", timeout=5)
            print(f"  mod: {st['mode']} | pid: {st['pid']} | çalışma: {st['uptime']}s | sürüm: {st['version']}")
            print(f"  açık olay: {st['open_events']} | bekleyen onay: {st['pending_approvals']}")
            return 0
        except (ConnectionError, RuntimeError) as e:
            print(f"  {c.YELLOW}IPC yanıt vermiyor: {e}{c.RESET}")
            return 3 if active != "active" else 1

    if sub == "install":
        ins = Installer(dcfg.scope, python_exe=args.python)  # dcfg.scope: --system / --scope / config sırasıyla çözülmüştür
        units = [u for u in dcfg.watch_units + dcfg.auto_units if "*" not in u and "?" not in u]
        for line in ins.install(allowed_roots=dcfg.allowed_roots, polkit_units=units, ipc_group=dcfg.ipc_group, start=args.start):
            print(f"{c.GREEN}✓{c.RESET} {line}")
        print(f"\n{c.DIM}Daemon varsayılan olarak 'report' modundadır: teşhis eder ama kendiliğinden bir şey uygulamaz.")
        if ins.scope == "user":
            print("Oturum kapalıyken de çalışması için (isteğe bağlı): loginctl enable-linger $USER")
        else:
            print(f"API anahtarını /etc/limon/limon.env dosyasına (0640 root:limon) yazın, örn. ANTHROPIC_API_KEY=...; ayarlar için /etc/limon/config.json")
        print(f"Başlatmak için: limon daemon start{c.RESET}")
        return 0

    if sub == "uninstall":
        ins = Installer(dcfg.scope)
        for line in ins.uninstall(purge=args.purge, state_dir=paths.state_dir):
            print(f"{c.GREEN}✓{c.RESET} {line}")
        return 0
    return 1


def _run_foreground(cfg, dcfg, paths) -> int:
    from .adapters import detect_platform
    from .service import LimonDaemon
    c = _c()
    platform = detect_platform(dcfg)
    try:
        if os.path.exists(cfgmod.CONFIG_PATH) and os.stat(cfgmod.CONFIG_PATH).st_mode & 0o077:
            print(f"Uyarı: {cfgmod.CONFIG_PATH} izinleri gevşek (API anahtarı içerebilir); chmod 600 önerilir.", file=sys.stderr)
    except OSError:
        pass
    from .websearch import build_backend
    backend, warn = build_backend(dcfg, cfg)
    if warn:
        print(f"Uyarı: {warn}", file=sys.stderr)
    daemon = LimonDaemon(dcfg, paths, platform, make_provider_factory(cfg), search_backend=backend)
    if backend:
        print(f"internet araması etkin ({backend.name}): sorgular temizlenip bu hizmete gönderilir; kayıt: audit günlüğü", flush=True)
    print(f"limon daemon çalışıyor (kapsam={dcfg.scope}, mod={dcfg.mode}, durum={paths.state_dir})", flush=True)
    daemon.run_forever()
    return 0


def _client(args, cmd, dcfg, paths) -> int:
    from .ipc import request
    c = _c()

    def call(op, params=None, timeout=20):
        return request(paths, op, params, timeout=timeout)

    if cmd == "events":
        try:
            events = call("events", {"limit": args.limit})["events"]
        except ConnectionError:
            events = _offline_events(paths, args.limit)
            if events is None:
                print(f"{c.YELLOW}Daemon çalışmıyor ve kayıtlı olay yok.{c.RESET}")
                return 0
            print(f"{c.DIM}(daemon çalışmıyor; kayıtlı veriler gösteriliyor){c.RESET}")
        if not events:
            print("Kayıtlı olay yok.")
            return 0
        for e in events:
            col = c.RED if e["severity"] == "critical" else c.YELLOW if e["severity"] == "warning" else c.DIM
            print(f"{col}#{e['id']:<4}{c.RESET} {_ts(e['last_seen'])}  {col}{e['severity']:<8}{c.RESET} {e['status']:<18} x{e['count']:<3} {e['summary']}")
            if e.get("diagnosis"):
                print(f"      {c.DIM}teşhis: {e['diagnosis']}{c.RESET}")
        return 0

    if cmd == "diagnose":
        window = parse_duration(args.last)
        print(f"{c.DIM}Son {window // 60} dakika için teşhis isteniyor (sağlayıcıya yalnızca süzülmüş log/durum bilgisi gider)...{c.RESET}")
        try:
            r = call("diagnose", {"window": window}, timeout=150)
        except ConnectionError:
            print(f"{c.RED}Daemon çalışmıyor.{c.RESET} Teşhis daemon üzerinden yapılır: limon daemon start")
            return 1
        if r.get("error") or "summary" not in r:
            print(f"{c.RED}Teşhis alınamadı:{c.RESET} {r.get('error') or r.get('status')}\n{c.DIM}Olay kayıtlı; daemon sınırlı sayıda otomatik tekrar deneyecek (limon events).{c.RESET}")
            return 1
        print(f"\n{c.BOLD}{r['summary']}{c.RESET}  [{r['severity']}, güven {r['confidence']:.0%}]")
        if r["root_cause"]:
            print(f"  Olası neden: {r['root_cause']}")
        for t in r["tasks"]:
            st = {"pending": f"{c.YELLOW}onay bekliyor{c.RESET}: limon approve {t['id']}", "denied": f"{c.RED}politika reddetti{c.RESET}",
                  "executed": f"{c.GREEN}uygulandı{c.RESET}"}.get(t["status"], t["status"])
            print(f"  • {t['action']['type']} {t['action'].get('unit') or t['action'].get('path', '')}  (risk {t['risk']}/10) → {st}")
            if t["status"] == "denied":
                print(f"    {c.DIM}{t['reasons']}{c.RESET}")
        for rej in r["rejected"]:
            print(f"  {c.DIM}atılan geçersiz öneri: {rej}{c.RESET}")
        return 0

    if cmd == "approvals":
        try:
            items = call("approvals")["approvals"]
        except ConnectionError:
            items = _offline_approvals(paths)
            print(f"{c.DIM}(daemon çalışmıyor; kayıtlı kuyruk gösteriliyor){c.RESET}")
        if not items:
            print("Onay bekleyen işlem yok.")
            return 0
        for t in items:
            bar = "█" * t["risk"] + "░" * (10 - t["risk"])
            a = t["action"]
            print(f"{c.BOLD}{t['id']}{c.RESET}  [{bar}] {t['risk']}/10  {a['type']} {a.get('unit') or a.get('path', '')}")
            print(f"    olay: {t['event']}\n    neden: {t['reasons']}")
            if a["type"] == "edit_file":
                print(f"    {c.DIM}- {a['old_string'][:200]!r}\n    + {a['new_string'][:200]!r}{c.RESET}")
            print(f"    son geçerlilik: {_ts(t['expires'])}\n    → limon approve {t['id']}   |   limon reject {t['id']}")
        return 0

    if cmd in ("approve", "reject"):
        try:
            r = call(cmd, {"id": args.task_id})
        except ConnectionError:
            r = _offline_decide(paths, dcfg, cmd, args.task_id)
            print(f"{c.YELLOW}Daemon çalışmıyor: karar kuyruğa yazıldı, daemon başlayınca işlenecek.{c.RESET}")
        except RuntimeError as e:
            print(f"{c.RED}Hata: {e}{c.RESET}")
            return 1
        print(f"{c.GREEN}✓ {args.task_id}: {r['status']}{c.RESET}" + (" (daemon yürütecek; sonuç: limon events)" if cmd == "approve" else ""))
        return 0
    return 1


# ---- daemon çalışmıyorken doğrudan (yalnızca aynı kullanıcı, dosya izinleri koruması) -------------------

def _open_store(paths):
    from .store import Store
    return Store(paths.db) if os.path.exists(paths.db) else None


def _offline_events(paths, limit):
    st = _open_store(paths)
    if st is None:
        return None
    import json
    out = []
    for e in st.list_events(limit):
        d = {}
        try:
            d = json.loads(e["diagnosis"]) if e["diagnosis"] else {}
        except ValueError:
            pass
        out.append({**{k: e[k] for k in ("id", "kind", "unit", "severity", "summary", "status", "count", "first_seen", "last_seen", "note")},
                    "diagnosis": d.get("summary", ""), "root_cause": d.get("root_cause", "")})
    st.close()
    return out


def _offline_approvals(paths):
    st = _open_store(paths)
    if st is None:
        return []
    import json
    from .approvals import Approvals
    out = []
    for t in Approvals(st, 0).pending():
        ev = st.get_event(t["event_id"]) or {}
        out.append({"id": t["id"], "action": json.loads(t["action"]), "risk": t["risk"], "reasons": t["reasons"],
                    "event": ev.get("summary", ""), "expires": t["expires"], "created": t["created"]})
    st.close()
    return out


def _offline_decide(paths, dcfg, cmd, task_id):
    from .approvals import ApprovalError, Approvals
    st = _open_store(paths)
    if st is None:
        raise ConnectionError("durum veritabanı yok; bekleyen işlem bulunamadı")
    try:
        a = Approvals(st, dcfg.approval_ttl)
        try:
            t = a.approve(task_id) if cmd == "approve" else a.reject(task_id)
        except ApprovalError as e:
            raise ValueError(str(e))
        return {"id": t["id"], "status": t["status"]}
    finally:
        st.close()
