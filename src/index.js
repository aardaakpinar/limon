#!/usr/bin/env node

/**
 * Limon terminal agent
 */

const readline = require("readline");
const { loadConfig } = require("./config");
const { printBanner, log, c } = require("./ui");
const { setup } = require("./setup");
const { CommandExecutor } = require("./executor");
const { askGemini, askClaude, askOpenAI, clearHistory } = require("./providers");
const { requestApproval } = require("./interaction");

function parseCliArgs(argv) {
    const args = argv.slice(2);
    const queryIndex = args.findIndex((a) => a === "--query" || a === "-q");
    let oneShotQuery = null;

    if (queryIndex >= 0 && args[queryIndex + 1]) {
        oneShotQuery = args[queryIndex + 1];
    } else {
        const positional = args.filter((a) => !a.startsWith("-"));
        if (positional.length) oneShotQuery = positional.join(" ");
    }

    return {
        forceSetup: args.includes("--setup"),
        clearHistoryFlag: args.includes("--temizle") || args.includes("--clear"),
        oneShotQuery,
    };
}

async function main() {
    const cli = parseCliArgs(process.argv);
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

    let cfg = loadConfig();
    if (cli.forceSetup || !cfg.provider || !cfg.apiKey || !cfg.workDir) {
        printBanner();
        cfg = await setup(rl);
    }

    if (cli.clearHistoryFlag) clearHistory();

    printBanner(cfg.workDir);

    const askFn = { gemini: askGemini, claude: askClaude, openai: askOpenAI }[cfg.provider];
    if (!askFn) throw new Error("Desteklenmeyen provider: " + cfg.provider);

    const executor = new CommandExecutor(cfg.workDir, cfg.securityEnabled !== false);
    const pName = cfg.provider.charAt(0).toUpperCase() + cfg.provider.slice(1);

    log.success(`${pName} ile baglandi.`);
    log.info(`Sandbox  : ${c.yellow}${cfg.workDir}${c.reset}`);
    log.info(`Guvenlik : ${cfg.securityEnabled !== false ? c.green + "ACIK" : c.red + "KAPALI"}${c.reset}`);
    log.info(`Komutlar : ${c.yellow}--setup${c.reset} | ${c.yellow}--temizle${c.reset} | ${c.yellow}cik${c.reset}`);
    console.log();

    async function runTurn(raw, allowControlCommands = true) {
        const t = (raw || "").trim();
        if (!t) return true;

        if (allowControlCommands && ["cik", "exit", "quit"].includes(t.toLowerCase())) {
            log.ai("Gorusmek uzere!", cfg.provider);
            return false;
        }

        if (allowControlCommands && t === "--setup") {
            clearHistory();
            cfg = await setup(rl);
            printBanner(cfg.workDir);
            return true;
        }

        if (allowControlCommands && (t === "--temizle" || t === "--clear")) {
            clearHistory();
            log.success("Gecmis temizlendi.");
            console.log();
            return true;
        }

        try {
            log.info("Dusunuyor...");
            const { message, command } = await askFn(t, cfg.apiKey, cfg.workDir);

            if (message) log.ai(message, cfg.provider);

            if (command) {
                const ok = await requestApproval(command, rl, cfg.workDir);
                if (ok) {
                    try {
                        log.info("Calistiriliyor...");
                        const out = await executor.execute(command);
                        console.log(`\n  ${c.green}Sonuc:${c.reset}`);
                        String(out)
                            .split("\n")
                            .forEach((l) => console.log(`  ${c.gray}|${c.reset} ${l}`));
                        console.log();
                        log.success("Tamamlandi.");
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
        return true;
    }

    if (cli.oneShotQuery) {
        await runTurn(cli.oneShotQuery, false);
        rl.close();
        return;
    }

    const ask = () => {
        rl.question(`  ${c.green}Siz${c.reset} ${c.gray}>${c.reset} `, async (raw) => {
            const keepGoing = await runTurn(raw, true);
            if (!keepGoing) {
                rl.close();
                return;
            }
            ask();
        });
    };

    ask();
}

main().catch((e) => {
    console.error("\n  HATA:", e.message);
    process.exit(1);
});
