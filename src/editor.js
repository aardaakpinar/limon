/**
 * Editor helpers
 */

const { spawn, spawnSync } = require("child_process");

const TERMINAL_EDITORS = new Set(["nano", "vi", "vim"]);

function splitCommand(cmdline) {
    if (!cmdline || typeof cmdline !== "string") return [];
    const parts = [];
    const re = /"([^"]*)"|'([^']*)'|[^\s]+/g;
    let m;
    while ((m = re.exec(cmdline))) {
        const part = m[1] ?? m[2] ?? m[0];
        if (part) parts.push(part);
    }
    return parts;
}

function normalizeCandidates(list) {
    const seen = new Set();
    const out = [];
    for (const item of list) {
        if (!item || typeof item !== "string") continue;
        const trimmed = item.trim();
        if (!trimmed) continue;
        if (seen.has(trimmed)) continue;
        seen.add(trimmed);
        out.push(trimmed);
    }
    return out;
}

function getEditorCandidates() {
    return normalizeCandidates([
        process.env.LIMON_EDITOR,
        process.env.VISUAL,
        process.env.EDITOR,
        "code",
        "notepad",
        "nano",
        "vim",
        "vi",
    ]);
}

function tryOpenTerminalEditor(cmd, args, filePath) {
    const result = spawnSync(cmd, [...args, filePath], {
        stdio: "inherit",
        shell: false,
    });
    return !result.error;
}

function tryOpenGuiEditor(cmd, args, filePath) {
    try {
        const child = spawn(cmd, [...args, filePath], {
            detached: true,
            stdio: "ignore",
            shell: false,
        });
        child.unref();
        return true;
    } catch {
        return false;
    }
}

function openInEditor(filePath) {
    const candidates = getEditorCandidates();
    for (const candidate of candidates) {
        const parts = splitCommand(candidate);
        if (!parts.length) continue;
        const cmd = parts[0];
        const args = parts.slice(1);
        const isTerminal = TERMINAL_EDITORS.has(cmd.toLowerCase());
        const ok = isTerminal ? tryOpenTerminalEditor(cmd, args, filePath) : tryOpenGuiEditor(cmd, args, filePath);
        if (ok) return { ok: true, editor: cmd };
    }
    return { ok: false, editor: "" };
}

module.exports = {
    openInEditor,
    getEditorCandidates,
};
