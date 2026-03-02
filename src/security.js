/**
 * Güvenlik Kontrolleri
 */

const path = require("path");

// Yasaklı komut kalıpları
const DEFAULT_BLOCKED = [
    { pattern: /\brm\s+-rf\s+\//, label: "Kök dizin silme (rm -rf /)" },
    { pattern: /\bformat\b.*[cC]:\b/, label: "Disk formatlama" },
    { pattern: /\bdiskpart\b/i, label: "Diskpart" },
    { pattern: /\bdd\b.*\bof=\/dev\//, label: "Ham disk yazma (dd)" },
    { pattern: /\bmkfs\b/, label: "Dosya sistemi oluşturma" },
    { pattern: /\b(del|rm)\b.*\b(system32|windows|boot)\b/i, label: "Sistem dosyası silme" },
    { pattern: /\breg(edit)?\b.*\b(delete|add)\b/i, label: "Registry değiştirme" },
    { pattern: /\b(nc|netcat)\b.*-e\b/, label: "Reverse shell" },
    { pattern: /\b(wget|curl)\b.*\|\s*(bash|sh|cmd)/i, label: "Remote script çalıştırma" },
    { pattern: /\bpowershell\b.*\bIEX\b/i, label: "PowerShell remote exec" },
    { pattern: /\b(msfconsole|msfvenom)\b/i, label: "Metasploit" },
    { pattern: /\bnet\s+user\b.*\/add/i, label: "Kullanıcı ekleme" },
    { pattern: /\buseradd\b/, label: "Kullanıcı ekleme (Linux)" },
    { pattern: /\b(shutdown|reboot|halt|poweroff)\b/i, label: "Sistemi kapatma" },
    { pattern: /\bsc\s+(stop|delete)\b/i, label: "Windows servis durdurma/silme" },
];

function isPathSafe(filePath, workDir) {
    const abs = path.resolve(workDir, filePath);
    return abs.startsWith(path.resolve(workDir));
}

function checkBlockedCommand(cmd, blockedList) {
    for (const rule of blockedList) {
        if (rule.pattern.test(cmd)) return rule.label;
    }
    return null;
}

class BlockedError extends Error {
    constructor(msg) {
        super(msg);
        this.isBlocked = true;
    }
}

module.exports = {
    DEFAULT_BLOCKED,
    isPathSafe,
    checkBlockedCommand,
    BlockedError,
};