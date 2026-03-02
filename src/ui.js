/**
 * UI / Terminal Stil ve Renkler
 */

const c = {
    reset: "\x1b[0m",
    yellow: "\x1b[38;2;252;196;29m",
    green: "\x1b[1m\x1b[32m",
    cyan: "\x1b[36m",
    white: "\x1b[97m",
    gray: "\x1b[90m",
    red: "\x1b[1m\x1b[31m",
    blue: "\x1b[34m",
    magenta: "\x1b[35m",
};

const W = Math.min(process.stdout.columns || 72, 80);

const hr = (ch = "─") => c.gray + ch.repeat(W) + c.reset;

function printBanner(workDir) {
    console.clear();
    console.log();
    [
        `  ${c.yellow}██╗     ██╗███╗   ███╗ ██████╗ ███╗   ██╗${c.reset}`,
        `  ${c.yellow}██║     ██║████╗ ████║██╔═══██╗████╗  ██║${c.reset}`,
        `  ${c.yellow}██║     ██║██╔████╔██║██║   ██║██╔██╗ ██║${c.reset}`,
        `  ${c.yellow}██║     ██║██║╚██╔╝██║██║   ██║██║╚██╗██║${c.reset}`,
        `  ${c.yellow}███████╗██║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║${c.reset}`,
        `  ${c.yellow}╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝${c.reset}`,
    ].forEach((l) => console.log(l));
    console.log();
    console.log(`  ${c.gray}◈  Yapay Zeka Ajanı   ◈  Komutlar onayınız olmadan çalışmaz  ◈${c.reset}`);
    if (workDir) console.log(`  ${c.gray}◈  Sandbox: ${c.yellow}${workDir}${c.reset}`);
    console.log();
    console.log("  " + hr());
    console.log();
}

const log = {
    info: (m) => console.log(`  ${c.cyan}◆${c.reset} ${c.white}${m}${c.reset}`),
    success: (m) => console.log(`  ${c.green}✓${c.reset} ${c.green}${m}${c.reset}`),
    warn: (m) => console.log(`  ${c.yellow}⚠${c.reset} ${c.yellow}${m}${c.reset}`),
    error: (m) => console.log(`  ${c.red}✗${c.reset} ${c.red}${m}${c.reset}`),
    blocked: (m) => console.log(`  ${c.red}🚫 ENGELLENDİ:${c.reset} ${c.red}${m}${c.reset}`),
    ai: (m, provider) => {
        const badges = { gemini: `${c.blue}[Gemini]`, claude: `${c.magenta}[Claude]`, openai: `${c.green}[ChatGPT]` };
        const badge = (badges[provider] || "") + c.reset;
        console.log(`  ${c.yellow}🍋 Limon${c.reset} ${badge}  ${c.gray}${"─".repeat(Math.max(0, W - 20))}${c.reset}`);
        m.split("\n").forEach((l) => console.log(`  ${c.white}${l}${c.reset}`));
        console.log("  " + hr());
        console.log();
    },
};

module.exports = {
    c,
    W,
    hr,
    printBanner,
    log,
};