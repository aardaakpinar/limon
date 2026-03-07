/**
 * Interaction and approval flow
 */

const path = require("path");
const { c, hr } = require("./ui");
const { question } = require("./setup");

async function requestApproval(cmd, rl, workDir) {
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
    if (cmd.path) console.log(`  ${c.yellow}Yol   :${c.reset} ${c.white}${path.resolve(workDir, cmd.path)}${c.reset}`);
    if (cmd.to) console.log(`  ${c.yellow}Hedef :${c.reset} ${c.white}${path.resolve(workDir, cmd.to)}${c.reset}`);
    if (cmd.url) console.log(`  ${c.yellow}URL   :${c.reset} ${c.white}${cmd.url}${c.reset}`);
    if (cmd.method) console.log(`  ${c.yellow}Method:${c.reset} ${c.white}${cmd.method}${c.reset}`);

    if (cmd.content) {
        const lines = String(cmd.content).split("\n");
        console.log(`  ${c.yellow}Icerik:${c.reset}`);
        lines.slice(0, 4).forEach((l) => console.log(`  ${c.gray}|${c.reset} ${c.white}${l}${c.reset}`));
        if (lines.length > 4) console.log(`  ${c.gray}| ... (${lines.length - 4} satir daha)${c.reset}`);
    }

    console.log("  " + hr("."));
    console.log();
    const ans = await question(rl, `  ${c.yellow}Onayliyor musunuz?${c.reset} ${c.gray}[e / h]${c.reset}  `);
    return ["e", "evet", "y", "yes"].includes(ans.toLowerCase().trim());
}

module.exports = {
    requestApproval,
};
