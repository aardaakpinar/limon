/**
 * Setup & Kurulum
 */

const fs = require("fs");
const path = require("path");
const { saveConfig } = require("./config");
const { DEFAULT_BLOCKED } = require("./security");
const { log, c, hr } = require("./ui");
const { askGemini, askClaude, askOpenAI, askOllama, clearHistory } = require("./providers");

async function setup(rl) {
    console.log(`  ${c.yellow}Limon Kurulumu${c.reset}`);
    console.log("  " + hr());
    console.log();

    const workDir = path.resolve("/home/limon");
    console.log(`  ${c.white}Calisma dizini - Limon tum dosyalari bu alanda olusturur/duzenler.${c.reset}`);
    console.log(`  ${c.gray}Sabit: ${workDir}${c.reset}\n`);
    fs.mkdirSync(workDir, { recursive: true });
    log.success(`Calisma dizini: ${workDir}`);
    console.log();

    console.log(`  ${c.white}Guvenlik engelleri - yuksek riskli komutlar:${c.reset}`);
    DEFAULT_BLOCKED.forEach((r, i) => console.log(`  ${c.gray}${String(i + 1).padStart(2)}. ${r.label}${c.reset}`));
    console.log();
    const disableSec = await question(rl, `  ${c.yellow}Engelleri kapat? (onerilmez) [e/H]:${c.reset} `);
    const securityEnabled = !["e", "evet"].includes(disableSec.toLowerCase().trim());
    log.success(`Guvenlik engelleri: ${securityEnabled ? c.green + "ACIK" : c.red + "KAPALI"}${c.reset}`);
    console.log();

    const appInput = await question(rl, `  ${c.yellow}Uygulama baslatma komutlarini ac? [e/H]:${c.reset} `);
    const allowAppLaunch = ["e", "evet"].includes(appInput.toLowerCase().trim());
    log.success(`Uygulama baslatma: ${allowAppLaunch ? c.green + "ACIK" : c.red + "KAPALI"}${c.reset}`);
    console.log();

    const apiInput = await question(rl, `  ${c.yellow}API cagrisi komutlarini ac? [e/H]:${c.reset} `);
    const allowApiCalls = ["e", "evet"].includes(apiInput.toLowerCase().trim());
    let allowedApiDomains = [];
    if (allowApiCalls) {
        const domains = await question(rl, `  ${c.yellow}Izinli domainler (virgulle, bos = tum public domainler):${c.reset} `);
        allowedApiDomains = domains
            .split(",")
            .map((d) => d.trim().toLowerCase())
            .filter(Boolean)
            .filter((d, i, arr) => arr.indexOf(d) === i);
    }
    log.success(`API cagrilari: ${allowApiCalls ? c.green + "ACIK" : c.red + "KAPALI"}${c.reset}`);
    console.log();

    console.log(`  ${c.white}AI Saglayicisi:${c.reset}`);
    console.log(`  ${c.blue}[1]${c.reset} Google Gemini   ${c.gray}(ucretsiz tier)${c.reset}`);
    console.log(`  ${c.magenta}[2]${c.reset} Anthropic Claude ${c.gray}(claude-3-5-haiku)${c.reset}`);
    console.log(`  ${c.green}[3]${c.reset} OpenAI ChatGPT  ${c.gray}(gpt-4o-mini)${c.reset}`);
    console.log(`  ${c.cyan}[4]${c.reset} Ollama          ${c.gray}(lokal, offline)${c.reset}\n`);
    const pInput = await question(rl, `  ${c.yellow}Seciminiz [1/2/3/4]:${c.reset} `);
    const provider = { 1: "gemini", 2: "claude", 3: "openai", 4: "ollama" }[pInput.trim()];
    if (!provider) {
        log.error("Gecersiz secim.");
        return setup(rl);
    }

    const keyLinks = {
        gemini: "https://aistudio.google.com/app/apikey",
        claude: "https://console.anthropic.com/settings/keys",
        openai: "https://platform.openai.com/api-keys",
    };

    let ollamaPort, ollamaModel, apiKey;

    if (provider === "ollama") {
        console.log();
        const portInput = await question(
            rl,
            `  ${c.yellow}Ollama Port (varsayilan: 11434):${c.reset} `
        );
        ollamaPort = parseInt(portInput.trim()) || 11434;
        log.success(`Ollama Port: ${ollamaPort}`);

        const modelInput = await question(
            rl,
            `  ${c.yellow}Model adi (ornegi: llama2, neural-chat, etc):${c.reset} `
        );
        ollamaModel = modelInput.trim();
        if (!ollamaModel) {
            log.error("Model adi bos olamaz.");
            return setup(rl);
        }
        log.success(`Model: ${ollamaModel}`);

        log.info("Ollama'ya baglaniyor...");
        try {
            const { askOllama } = require("./providers");
            await askOllama(
                '{"message":"hazir","command":null} dondur.',
                { ollamaPort, ollamaModel },
                workDir
            );
            clearHistory();
            log.success("Ollama baglantisi basarili!");
        } catch (e) {
            clearHistory();
            log.error(
                "Ollama baglantisi hatasi: " + e.message
            );
            return setup(rl);
        }
        apiKey = ""; // Ollama için API key gerekli değil
    } else {
        console.log();
        log.info(`API key: ${c.cyan}${keyLinks[provider]}${c.reset}\n`);
        apiKey = await question(rl, `  ${c.yellow}API Key:${c.reset} `);
        if (!apiKey.trim()) {
            log.error("API key bos olamaz.");
            return setup(rl);
        }

        log.info("Test ediliyor...");
        try {
            const fns = { gemini: askGemini, claude: askClaude, openai: askOpenAI };
            await fns[provider]('{"message":"hazir","command":null} dondur.', apiKey.trim(), workDir);
            clearHistory();
            log.success("API key gecerli!");
        } catch (e) {
            clearHistory();
            if (e.message.includes("kota")) {
                log.warn(e.message + " - devam ediliyor.");
            } else {
                log.error("API key gecersiz: " + e.message);
                return setup(rl);
            }
        }
    }

    const saveKeyInput = provider !== "ollama" ? await question(rl, `  ${c.yellow}API key config dosyasina kaydedilsin mi? [e/H]:${c.reset} `) : "";
    const persistApiKey = provider !== "ollama" && ["e", "evet"].includes(saveKeyInput.toLowerCase().trim());

    const runtimeCfg = {
        provider,
        apiKey: apiKey.trim(),
        workDir,
        agentHome: workDir,
        securityEnabled,
        allowAppLaunch,
        allowApiCalls,
        allowedApiDomains,
    };

    // Ollama parametrelerini ekle
    if (provider === "ollama") {
        runtimeCfg.ollamaPort = ollamaPort;
        runtimeCfg.ollamaModel = ollamaModel;
    }

    const saveCfg = { ...runtimeCfg, apiKey: persistApiKey ? runtimeCfg.apiKey : "" };
    saveConfig(saveCfg);
    const { CONFIG_FILE } = require("./config");
    log.success(`Kaydedildi -> ${CONFIG_FILE}\n`);

    if (!persistApiKey && provider !== "ollama") {
        log.info("Not: Sonraki acilislar icin LIMON_API_KEY veya provider bazli env degiskeni kullanin.");
    }

    return runtimeCfg;
}

function question(rl, prompt) {
    return new Promise((res) => rl.question(prompt, res));
}

module.exports = {
    setup,
    question,
};