/**
 * Setup & Kurulum
 */

const fs = require("fs");
const path = require("path");
const os = require("os");
const { saveConfig } = require("./config");
const { DEFAULT_BLOCKED } = require("./security");
const { log, c, hr } = require("./ui");
const { askGemini, askClaude, askOpenAI, clearHistory } = require("./providers");

async function setup(rl) {
    console.log(`  ${c.yellow}🍋 Limon Kurulumu${c.reset}`);
    console.log("  " + hr());
    console.log();

    // Çalışma dizini
    const defaultDir = path.join(os.homedir(), "limon-workspace");
    console.log(`  ${c.white}Çalışma dizini (sandbox) — AI yalnızca bu klasörde işlem yapabilir.${c.reset}`);
    console.log(`  ${c.gray}Varsayılan: ${defaultDir}${c.reset}\n`);
    const dirInput = await question(rl, `  ${c.yellow}Dizin [Enter = varsayılan]:${c.reset} `);
    const workDir = path.resolve(dirInput.trim() || defaultDir);
    fs.mkdirSync(workDir, { recursive: true });
    log.success(`Sandbox dizini: ${workDir}`);
    console.log();

    // Güvenlik
    console.log(`  ${c.white}Güvenlik engelleri — yüksek riskli komutlar:${c.reset}`);
    DEFAULT_BLOCKED.forEach((r, i) => console.log(`  ${c.gray}${String(i + 1).padStart(2)}. ${r.label}${c.reset}`));
    console.log();
    const disableSec = await question(rl, `  ${c.yellow}Engelleri kapat? (önerilmez) [e/H]:${c.reset} `);
    const securityEnabled = !["e", "evet"].includes(disableSec.toLowerCase().trim());
    log.success(`Güvenlik engelleri: ${securityEnabled ? c.green + "AÇIK" : c.red + "KAPALI"}${c.reset}`);
    console.log();

    // AI sağlayıcı
    console.log(`  ${c.white}AI Sağlayıcısı:${c.reset}`);
    console.log(`  ${c.blue}[1]${c.reset} Google Gemini   ${c.gray}(Ücretsiz tier)${c.reset}`);
    console.log(`  ${c.magenta}[2]${c.reset} Anthropic Claude ${c.gray}(claude-3-5-haiku)${c.reset}`);
    console.log(`  ${c.green}[3]${c.reset} OpenAI ChatGPT  ${c.gray}(gpt-4o-mini)${c.reset}\n`);
    const pInput = await question(rl, `  ${c.yellow}Seçiminiz [1/2/3]:${c.reset} `);
    const provider = { 1: "gemini", 2: "claude", 3: "openai" }[pInput.trim()];
    if (!provider) {
        log.error("Geçersiz seçim.");
        return setup(rl);
    }

    const keyLinks = {
        gemini: "https://aistudio.google.com/app/apikey",
        claude: "https://console.anthropic.com/settings/keys",
        openai: "https://platform.openai.com/api-keys",
    };
    console.log();
    log.info(`API key: ${c.cyan}${keyLinks[provider]}${c.reset}\n`);
    const apiKey = await question(rl, `  ${c.yellow}API Key:${c.reset} `);
    if (!apiKey.trim()) {
        log.error("API key boş olamaz.");
        return setup(rl);
    }

    log.info("Test ediliyor...");
    try {
        const fns = { gemini: askGemini, claude: askClaude, openai: askOpenAI };
        await fns[provider]('{"message":"hazir","command":null} dondur.', apiKey.trim(), workDir);
        clearHistory();
        log.success("API key geçerli!");
    } catch (e) {
        clearHistory();
        if (e.message.includes("kota")) {
            log.warn(e.message + " — devam ediliyor.");
        } else {
            log.error("API key geçersiz: " + e.message);
            return setup(rl);
        }
    }

    const cfg = { provider, apiKey: apiKey.trim(), workDir, securityEnabled };
    saveConfig(cfg);
    const { CONFIG_FILE } = require("./config");
    log.success(`Kaydedildi → ${CONFIG_FILE}\n`);
    return cfg;
}

function question(rl, prompt) {
    return new Promise((res) => rl.question(prompt, res));
}

module.exports = {
    setup,
    question,
};