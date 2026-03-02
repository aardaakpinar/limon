/**
 * Komut Yürütücü
 */

const { exec } = require("child_process");
const fs = require("fs");
const path = require("path");
const { checkBlockedCommand, BlockedError, isPathSafe } = require("./security");

class CommandExecutor {
    constructor(workDir, securityEnabled) {
        this.workDir = workDir;
        const { DEFAULT_BLOCKED } = require("./security");
        this.blocked = securityEnabled ? DEFAULT_BLOCKED : [];
    }

    execute(cmd) {
        switch (cmd.type) {
            case "shell":
                return this.shell(cmd);
            case "file":
                return this.file(cmd);
            case "api":
                return this.apiCall(cmd);
            default:
                throw new Error("Bilinmeyen tip: " + cmd.type);
        }
    }

    shell({ exec: rawCmd }) {
        const blocked = checkBlockedCommand(rawCmd, this.blocked);
        if (blocked) throw new BlockedError(`"${blocked}" kategorisi engellendi.`);
        return new Promise((res, rej) =>
            exec(rawCmd, { timeout: 30000, cwd: this.workDir }, (err, out, serr) =>
                err ? rej(new Error(serr || err.message)) : res(out || "✓ Tamamlandı.")
            )
        );
    }

    file({ action, path: rawPath, content }) {
        if (!isPathSafe(rawPath, this.workDir)) throw new BlockedError("Sandbox dışı erişim engellendi: " + rawPath);
        const absPath = path.resolve(this.workDir, rawPath);
        if (action === "write") {
            fs.mkdirSync(path.dirname(absPath), { recursive: true });
            fs.writeFileSync(absPath, content || "", "utf8");
            return Promise.resolve("Yazıldı: " + absPath);
        }
        if (action === "read") return Promise.resolve(fs.readFileSync(absPath, "utf8"));
        if (action === "delete") {
            fs.unlinkSync(absPath);
            return Promise.resolve("Silindi: " + absPath);
        }
        return Promise.reject(new Error("Bilinmeyen dosya işlemi: " + action));
    }

    async apiCall({ url, method = "GET", body, headers = {} }) {
        const r = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json", ...headers },
            body: body ? JSON.stringify(body) : undefined,
        });
        return "HTTP " + r.status + "\n" + (await r.text());
    }
}

module.exports = { CommandExecutor };