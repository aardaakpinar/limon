"""
limon.tools
-----------
AI'nin çağırabileceği somut araçlar (tools). Her araç fonksiyonu bir
(sonuç_metni, ekstra_bilgi) döndürür. Tehlikeli işlemler burada DEĞİL,
agent.py içindeki onay akışında ele alınır - burada sadece uygulama var.
"""

import datetime
import os
import shutil
import subprocess

BACKUP_DIR_NAME = ".limon_backups"


def get_current_datetime(_args: dict) -> str:
    now = datetime.datetime.now()
    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    return (
        f"{now.strftime('%Y-%m-%d %H:%M:%S')} "
        f"({gunler[now.weekday()]}, {now.day} "
        f"{['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'][now.month-1]} "
        f"{now.year})"
    )


def read_file(args: dict) -> str:
    path = os.path.expanduser(args["path"])
    if not os.path.exists(path):
        return f"HATA: dosya bulunamadı: {path}"
    if os.path.getsize(path) > 2_000_000:
        return f"HATA: dosya çok büyük (>2MB), okunamadı: {path}"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return f"HATA: dosya okunamadı: {e}"
    return f"--- {path} ({len(content)} karakter) ---\n{content}"


def list_dir(args: dict) -> str:
    path = os.path.expanduser(args.get("path", "."))
    if not os.path.isdir(path):
        return f"HATA: dizin bulunamadı: {path}"
    entries = sorted(os.listdir(path))
    lines = []
    for e in entries:
        full = os.path.join(path, e)
        tag = "/" if os.path.isdir(full) else ""
        lines.append(f"{e}{tag}")
    return f"--- {path} içeriği ---\n" + "\n".join(lines) if lines else f"{path} boş."


def _make_backup(path: str) -> str:
    os.makedirs(os.path.join(os.path.dirname(path) or ".", BACKUP_DIR_NAME), exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{os.path.basename(path)}.{ts}.bak"
    backup_path = os.path.join(os.path.dirname(path) or ".", BACKUP_DIR_NAME, backup_name)
    shutil.copy2(path, backup_path)
    return backup_path


def write_file(args: dict) -> str:
    path = os.path.expanduser(args["path"])
    content = args.get("content", "")
    existed = os.path.exists(path)
    backup_msg = ""
    if existed:
        try:
            backup_path = _make_backup(path)
            backup_msg = f" 💾 Yedek alındı: {backup_path}"
        except Exception as e:
            backup_msg = f" (Yedek alınamadı: {e})"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return f"HATA: dosya yazılamadı: {e}"
    return f"OK: {path} yazıldı ({len(content)} karakter).{backup_msg}"


def delete_file(args: dict) -> str:
    path = os.path.expanduser(args["path"])
    if not os.path.exists(path):
        return f"HATA: dosya bulunamadı: {path}"
    try:
        backup_path = _make_backup(path)
        os.remove(path)
    except Exception as e:
        return f"HATA: silinemedi: {e}"
    return f"OK: {path} silindi. 💾 Yedek: {backup_path}"


def run_command(args: dict) -> str:
    command = args["command"]
    timeout = args.get("timeout", 60)
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return f"HATA: komut {timeout} saniyede zaman aşımına uğradı."
    except Exception as e:
        return f"HATA: komut çalıştırılamadı: {e}"

    output = f"$ {command}\nçıkış kodu: {result.returncode}\n"
    if result.stdout:
        output += f"--- stdout ---\n{result.stdout[-4000:]}\n"
    if result.stderr:
        output += f"--- stderr ---\n{result.stderr[-4000:]}\n"
    return output.strip()


# Sağlayıcılara aktarılacak, sağlayıcıdan-bağımsız tool tanımları
# (JSON Schema tarzı - her sağlayıcı kendi formatına çevirir)
TOOL_DEFINITIONS = [
    {
        "name": "get_current_datetime",
        "description": "Sistemin güncel tarih ve saatini döndürür. Kullanıcı tarih/saat sorduğunda kullan.",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "danger": "none",
    },
    {
        "name": "read_file",
        "description": "Verilen yoldaki bir dosyanın içeriğini okur.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Dosya yolu"}},
            "required": ["path"],
        },
        "danger": "none",
    },
    {
        "name": "list_dir",
        "description": "Verilen dizindeki dosya ve klasörleri listeler.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Dizin yolu (varsayılan: .)"}},
            "required": [],
        },
        "danger": "none",
    },
    {
        "name": "write_file",
        "description": "Verilen yola dosya yazar. Dosya zaten varsa üzerine yazmadan önce otomatik yedek alınır.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Dosya yolu"},
                "content": {"type": "string", "description": "Dosyaya yazılacak TAM içerik"},
            },
            "required": ["path", "content"],
        },
        "danger": "file_write",
    },
    {
        "name": "delete_file",
        "description": "Bir dosyayı siler (öncesinde yedek alır).",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Dosya yolu"}},
            "required": ["path"],
        },
        "danger": "file_delete",
    },
    {
        "name": "run_command",
        "description": (
            "Linux kabuğunda (bash) bir komut çalıştırır ve stdout/stderr/çıkış kodunu döndürür. "
            "Dosya arama, paket kurma, sistem bilgisi alma, script çalıştırma vb. için kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Çalıştırılacak bash komutu"},
                "timeout": {"type": "integer", "description": "Saniye cinsinden zaman aşımı (varsayılan 60)"},
            },
            "required": ["command"],
        },
        "danger": "command",
    },
]

TOOL_IMPLEMENTATIONS = {
    "get_current_datetime": get_current_datetime,
    "read_file": read_file,
    "list_dir": list_dir,
    "write_file": write_file,
    "delete_file": delete_file,
    "run_command": run_command,
}
