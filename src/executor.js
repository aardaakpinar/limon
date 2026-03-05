/**
 * Command runtime
 */

const { exec, spawn } = require("child_process");
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
            case "app":
                return this.app(cmd);
            case "api":
                return this.apiCall(cmd);
            default:
                throw new Error("Bilinmeyen tip: " + cmd.type);
        }
    }

    shell({ exec: rawCmd }) {
        if (!rawCmd || typeof rawCmd !== "string") throw new Error("Gecersiz shell komutu.");
        if (rawCmd.length > 500) throw new BlockedError("Komut cok uzun, guvenlik nedeniyle engellendi.");

        const blocked = checkBlockedCommand(rawCmd, this.blocked);
        if (blocked) throw new BlockedError(`"${blocked}" kategorisi engellendi.`);

        return new Promise((res, rej) =>
            exec(rawCmd, { timeout: 30000, cwd: this.workDir, maxBuffer: 1024 * 1024 }, (err, out, serr) =>
                err ? rej(new Error((serr || err.message || "Komut hatasi").trim())) : res((out || "OK").trim())
            )
        );
    }

    file({ action, path: rawPath, content, to }) {
        if (!rawPath || typeof rawPath !== "string") throw new Error("Dosya yolu eksik.");
        if (!isPathSafe(rawPath, this.workDir)) throw new BlockedError("Sandbox disi erisim engellendi: " + rawPath);

        const absPath = path.resolve(this.workDir, rawPath);

        if (action === "write") {
            fs.mkdirSync(path.dirname(absPath), { recursive: true });
            fs.writeFileSync(absPath, content || "", "utf8");
            return Promise.resolve("Yazildi: " + absPath);
        }

        if (action === "append") {
            fs.mkdirSync(path.dirname(absPath), { recursive: true });
            fs.appendFileSync(absPath, content || "", "utf8");
            return Promise.resolve("Eklendi: " + absPath);
        }

        if (action === "read") {
            if (!fs.existsSync(absPath)) throw new Error("Dosya bulunamadi: " + absPath);
            return Promise.resolve(fs.readFileSync(absPath, "utf8"));
        }

        if (action === "delete") {
            if (!fs.existsSync(absPath)) throw new Error("Silinecek yol bulunamadi: " + absPath);
            fs.rmSync(absPath, { recursive: true, force: false });
            return Promise.resolve("Silindi: " + absPath);
        }

        if (action === "mkdir") {
            fs.mkdirSync(absPath, { recursive: true });
            return Promise.resolve("Klasor olusturuldu: " + absPath);
        }

        if (action === "list") {
            const items = fs.readdirSync(absPath, { withFileTypes: true });
            const lines = items.map((i) => `${i.isDirectory() ? "[DIR]" : "[FILE]"} ${i.name}`);
            return Promise.resolve(lines.join("\n") || "Bos");
        }

        if (action === "move") {
            if (!to || typeof to !== "string") throw new Error("Hedef yol (to) eksik.");
            if (!isPathSafe(to, this.workDir)) throw new BlockedError("Sandbox disi hedef engellendi: " + to);
            const absTo = path.resolve(this.workDir, to);
            fs.mkdirSync(path.dirname(absTo), { recursive: true });
            fs.renameSync(absPath, absTo);
            return Promise.resolve(`Tasindi: ${absPath} -> ${absTo}`);
        }

        return Promise.reject(new Error("Bilinmeyen dosya islemi: " + action));
    }

    app({ app, args = [] }) {
        if (!app || typeof app !== "string") throw new Error("Uygulama adi eksik.");
        if (!/^[a-zA-Z0-9._-]+$/.test(app)) throw new BlockedError("Gecersiz uygulama adi: " + app);
        if (!Array.isArray(args) || args.some((a) => typeof a !== "string" || a.length > 200)) {
            throw new BlockedError("Gecersiz uygulama argumanlari.");
        }

        try {
            const child = spawn(app, args, {
                cwd: this.workDir,
                detached: true,
                stdio: "ignore",
                shell: false,
            });
            child.unref();
            return Promise.resolve(`Baslatildi: ${app}${args.length ? " " + args.join(" ") : ""}`);
        } catch (e) {
            throw new Error("Uygulama baslatilamadi: " + e.message);
        }
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
