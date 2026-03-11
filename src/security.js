/**
 * Güvenlik Kontrolleri
 */

const path = require("path");
const net = require("net");

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

const SHELL_BLOCKED_SYNTAX = [
    { pattern: /&&|\|\||;/, label: "Komut zincirleme operatoru" },
    { pattern: /\|/, label: "Pipe operatoru" },
    { pattern: /`|\$\(/, label: "Komut ikamesi" },
    { pattern: /(^|\s)[<>]{1,2}\s*/, label: "Yonlendirme operatoru" },
    { pattern: /(^|[\s"'`])\.\.(?:[\\/]|$)/, label: "Path traversal (..)" },
];

function isPathSafe(filePath, workDir) {
    const abs = path.resolve(workDir, filePath);
    const base = path.resolve(workDir);
    return abs === base || abs.startsWith(base + path.sep);
}

function isPathWithin(baseDir, targetPath) {
    const base = path.resolve(baseDir);
    const target = path.resolve(targetPath);
    return target === base || target.startsWith(base + path.sep);
}

function checkBlockedCommand(cmd, blockedList) {
    for (const rule of blockedList) {
        if (rule.pattern.test(cmd)) return rule.label;
    }
    return null;
}

function checkBlockedShellSyntax(cmd) {
    for (const rule of SHELL_BLOCKED_SYNTAX) {
        if (rule.pattern.test(cmd)) return rule.label;
    }
    return null;
}

function validateApiUrl(rawUrl, allowedDomains = []) {
    let url;
    try {
        url = new URL(rawUrl);
    } catch {
        return { ok: false, reason: "Gecersiz URL." };
    }

    if (!["http:", "https:"].includes(url.protocol)) {
        return { ok: false, reason: "Sadece HTTP/HTTPS desteklenir." };
    }

    const host = (url.hostname || "").toLowerCase();
    if (!host) return { ok: false, reason: "Hostname eksik." };
    if (isLocalOrPrivateHost(host)) {
        return { ok: false, reason: "Local/private adreslere erisim engellendi." };
    }

    const normalizedAllowlist = (Array.isArray(allowedDomains) ? allowedDomains : [])
        .map((d) => String(d || "").toLowerCase().trim())
        .filter(Boolean);
    if (normalizedAllowlist.length) {
        const allowed = normalizedAllowlist.some((d) => host === d || host.endsWith("." + d));
        if (!allowed) return { ok: false, reason: "Domain allowlist disi URL." };
    }

    return { ok: true, url };
}

function isLocalOrPrivateHost(hostname) {
    if (hostname === "localhost") return true;
    if (hostname.endsWith(".local")) return true;
    if (hostname === "::1") return true;

    const ipVersion = net.isIP(hostname);
    if (!ipVersion) return false;
    if (ipVersion === 4) {
        if (hostname.startsWith("10.")) return true;
        if (hostname.startsWith("127.")) return true;
        if (hostname.startsWith("192.168.")) return true;
        if (/^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname)) return true;
        if (hostname === "0.0.0.0") return true;
    }
    if (ipVersion === 6) {
        const s = hostname.toLowerCase();
        if (s === "::1" || s.startsWith("fc") || s.startsWith("fd") || s.startsWith("fe80")) return true;
    }
    return false;
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
    isPathWithin,
    checkBlockedCommand,
    checkBlockedShellSyntax,
    validateApiUrl,
    BlockedError,
};
