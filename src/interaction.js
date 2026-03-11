/**
 * Interaction and approval flow
 */

const path = require("path");
const fs = require("fs");
const { spawnSync } = require("child_process");
const { c, hr } = require("./ui");
const { question } = require("./setup");
const { isPathWithin } = require("./security");

function isInAgentHome(absPath, agentHome) {
    if (!agentHome || !absPath) return false;
    return isPathWithin(agentHome, absPath);
}

function shouldRequireApproval(cmd, workDir, agentHome) {
    if (!cmd || cmd.type !== "file") return true;
    if (!agentHome) return true;

    const absPath = cmd.path ? path.resolve(workDir, cmd.path) : null;
    if (cmd.action === "move") {
        const absTo = cmd.to ? path.resolve(workDir, cmd.to) : null;
        return !(isInAgentHome(absPath, agentHome) && isInAgentHome(absTo, agentHome));
    }

    return !isInAgentHome(absPath, agentHome);
}

function tryPager(pager, text) {
    const result = spawnSync(pager, [], {
        input: text,
        stdio: ["pipe", "inherit", "inherit"],
    });
    return !result.error;
}

function previewWithPager(text) {
    const pagers = [process.env.PAGER, "less", "more"].filter(Boolean);
    for (const pager of pagers) {
        if (tryPager(pager, text)) return true;
    }
    return false;
}

function previewApprovalContent(cmd, absPath) {
    let text = "";
    if (cmd && typeof cmd.content === "string" && cmd.content.length) {
        text = cmd.content;
    } else if (absPath && fs.existsSync(absPath)) {
        text = fs.readFileSync(absPath, "utf8");
    }
    if (!text) return false;
    return previewWithPager(text);
}

async function requestApproval(cmd, rl, workDir, agentHome) {
    console.log();
    console.log(`  ${c.yellow}KOMUT ONAY GEREKTIRIYOR${c.reset}`);
    console.log("  " + hr("."));
    console.log(`  ${c.yellow}Tip   :${c.reset} ${c.white}${cmd.type}${c.reset}`);
    console.log(`  ${c.yellow}Islem :${c.reset} ${c.white}${cmd.action || "-"}${c.reset}`);

    if (cmd.exec) console.log(`  ${c.yellow}Komut :${c.reset} ${c.cyan}${cmd.exec}${c.reset}`);
    if (cmd.app) console.log(`  ${c.yellow}Uygulama:${c.reset} ${c.cyan}${cmd.app}${c.reset}`);
    if (Array.isArray(cmd.args) && cmd.args.length) {
        console.log(`  ${c.yellow}Arguman:${c.reset} ${c.white}${cmd.args.join(" ")}${c.reset}`);
    }
    const absPath = cmd.path ? path.resolve(workDir, cmd.path) : null;
    if (cmd.path) console.log(`  ${c.yellow}Yol   :${c.reset} ${c.white}${absPath}${c.reset}`);
    if (cmd.to) console.log(`  ${c.yellow}Hedef :${c.reset} ${c.white}${path.resolve(workDir, cmd.to)}${c.reset}`);
    if (cmd.url) console.log(`  ${c.yellow}URL   :${c.reset} ${c.white}${cmd.url}${c.reset}`);
    if (cmd.method) console.log(`  ${c.yellow}Method:${c.reset} ${c.white}${cmd.method}${c.reset}`);

    if (cmd.content) {
        const lines = String(cmd.content).split("\n");
        console.log(`  ${c.yellow}Icerik:${c.reset}`);
        lines.slice(0, 4).forEach((l) => console.log(`  ${c.gray}|${c.reset} ${c.white}${l}${c.reset}`));
        if (lines.length > 4) console.log(`  ${c.gray}| ... (${lines.length - 4} satir daha)${c.reset}`);
    }

    if (cmd.type === "file" && absPath && !isInAgentHome(absPath, agentHome)) {
        console.log(`  ${c.yellow}Onizleme:${c.reset} ${c.gray}(less/more)${c.reset}`);
        const ok = previewApprovalContent(cmd, absPath);
        if (!ok) {
            let fallbackText = "";
            if (cmd.content) fallbackText = String(cmd.content);
            else if (absPath && fs.existsSync(absPath)) fallbackText = fs.readFileSync(absPath, "utf8");
            const lines = (fallbackText || "").split("\n");
            if (lines.length) {
                console.log(`  ${c.gray}|${c.reset} ${c.white}${lines[0]}${c.reset}`);
                lines.slice(1, 4).forEach((l) => console.log(`  ${c.gray}|${c.reset} ${c.white}${l}${c.reset}`));
                if (lines.length > 4) console.log(`  ${c.gray}| ... (${lines.length - 4} satir daha)${c.reset}`);
            }
        }
        console.log();
    }

    console.log("  " + hr("."));
    console.log();
    const ans = await question(rl, `  ${c.yellow}Onayliyor musunuz?${c.reset} ${c.gray}[e / h]${c.reset}  `);
    return ["e", "evet", "y", "yes"].includes(ans.toLowerCase().trim());
}

module.exports = {
    requestApproval,
    shouldRequireApproval,
};
