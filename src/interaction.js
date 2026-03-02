/**
 * Etkileşim & Komut Onayı
 */

const path = require("path");
const { c, hr } = require("./ui");
const { question } = require("./setup");

async function requestApproval(cmd, rl, workDir) {
    console.log();
    console.log(`  ${c.yellow}⚡ KOMUT ONAY GEREKTİRİYOR${c.reset}`);
    console.log("  " + hr("·"));
    console.log(`  ${c.yellow}Tip   :${c.reset} ${c.white}${cmd.type}${c.reset}`);
    console.log(`  ${c.yellow}İşlem :${c.reset} ${c.white}${cmd.action || "-"}${c.reset}`);
    if (cmd.exec) console.log(`  ${c.yellow}Komut :${c.reset} ${c.cyan}${cmd.exec}${c.reset}`);
    if (cmd.path) console.log(`  ${c.yellow}Yol   :${c.reset} ${c.white}${path.resolve(workDir, cmd.path)}${c.reset}`);
    if (cmd.content) {
        const lines = cmd.content.split("\n");
        console.log(`  ${c.yellow}İçerik:${c.reset}`);
        lines.slice(0, 4).forEach((l) => console.log(`  ${c.gray}│${c.reset} ${c.white}${l}${c.reset}`));
        if (lines.length > 4) console.log(`  ${c.gray}│ ... (${lines.length - 4} satır daha)${c.reset}`);
    }
    console.log("  " + hr("·"));
    console.log();
    const ans = await question(
        rl,
        `  ${c.yellow}🍋${c.reset} ${c.white}Onaylıyor musunuz?${c.reset} ${c.gray}[e / h]${c.reset}  `
    );
    return ["e", "evet", "y", "yes"].includes(ans.toLowerCase().trim());
}

module.exports = {
    requestApproval,
};