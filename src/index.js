#!/usr/bin/env node

/**
 * 🍋 LiMON AI Ajan v2.1 - Modüler Versiyon
 * Desteklenen modeller: Google Gemini, Anthropic Claude, OpenAI ChatGPT
 */

const readline = require("readline");
const { loadConfig } = require("./config");
const { printBanner, log, c } = require("./ui");
const { setup, question } = require("./setup");
const { CommandExecutor } = require("./executor");
const { askGemini, askClaude, askOpenAI, clearHistory } = require("./providers");
const { requestApproval } = require("./interaction");

async function main() {
    printBanner();
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

    let cfg = loadConfig();
    if (!cfg.provider || !cfg.apiKey || !cfg.workDir) {
        cfg = await setup(rl);
    }

    printBanner(cfg.workDir);

    const askFn = { gemini: askGemini, claude: askClaude, openai: askOpenAI }[cfg.provider];
    const executor = new CommandExecutor(cfg.workDir, cfg.securityEnabled !== false);
    const pName = cfg.provider.charAt(0).toUpperCase() + cfg.provider.slice(1);

    log.success(`${pName} ile bağlandı.`);
    log.info(`Sandbox  : ${c.yellow}${cfg.workDir}${c.reset}`);
    log.info(`Güvenlik : ${cfg.securityEnabled !== false ? c.green + "AÇIK" : c.red + "KAPALI"}${c.reset}`);
    log.info(`Komutlar : ${c.yellow}--setup${c.reset} | ${c.yellow}--temizle${c.reset} | ${c.yellow}çık${c.reset}`);
    console.log();

    const ask = () => {
        rl.question(`  ${c.green}Siz${c.reset} ${c.gray}›${c.reset} `, async (raw) => {
            const t = raw.trim();
            if (!t) {
                ask();
                return;
            }

            // Çıkış
            if (["çık", "exit", "quit"].includes(t.toLowerCase())) {
                log.ai("Görüşmek üzere! 🍋", cfg.provider);
                rl.close();
                return;
            }

            // Setup
            if (t === "--setup") {
                clearHistory();
                cfg = await setup(rl);
                printBanner(cfg.workDir);
                ask();
                return;
            }

            // Tarih temizle
            if (t === "--temizle" || t === "--clear") {
                clearHistory();
                log.success("Geçmiş temizlendi.");
                console.log();
                ask();
                return;
            }

            try {
                log.info("Düşünüyor...");
                const { message, command } = await askFn(t, cfg.apiKey, cfg.workDir);

                if (message) log.ai(message, cfg.provider);

                if (command) {
                    const ok = await requestApproval(command, rl, cfg.workDir);
                    if (ok) {
                        try {
                            log.info("Çalıştırılıyor...");
                            const out = await executor.execute(command);
                            console.log(`\n  ${c.green}Sonuç:${c.reset}`);
                            out.split("\n").forEach((l) => console.log(`  ${c.gray}│${c.reset} ${l}`));
                            console.log();
                            log.success("Tamamlandı.");
                        } catch (e) {
                            if (e.isBlocked) log.blocked(e.message);
                            else log.error(e.message);
                        }
                    } else {
                        log.warn("Komut iptal edildi.");
                    }
                }
            } catch (e) {
                log.error(e.message);
            }

            console.log();
            ask();
        });
    };

    ask();
}

main().catch((e) => {
    console.error("\n  HATA:", e.message);
    process.exit(1);
});