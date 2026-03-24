/**
 * Limon terminal agent
 */
const readline = require("readline");
const fs = require("fs");
const path = require("path");
const { loadConfig } = require("./config");
const { printBanner, log, c } = require("./ui");
const { setup } = require("./setup");
const { CommandExecutor } = require("./executor");
const { askGemini, askClaude, askOpenAI, askOllama, clearHistory } = require("./providers");
const { requestApproval, shouldRequireApproval } = require("./interaction");
const { openInEditor } = require("./editor");
const { isPathWithin } = require("./security");

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

function resolveApiKey(cfg) {
    if (cfg && typeof cfg.apiKey === "string" && cfg.apiKey.trim()) return cfg.apiKey.trim();
    const envKeyMap = {
        gemini: process.env.LIMON_GEMINI_API_KEY || process.env.GEMINI_API_KEY,
        claude: process.env.LIMON_CLAUDE_API_KEY || process.env.ANTHROPIC_API_KEY,
        openai: process.env.LIMON_OPENAI_API_KEY || process.env.OPENAI_API_KEY,
    };
    const providerKey = cfg && cfg.provider ? envKeyMap[cfg.provider] : null;
    if (providerKey && providerKey.trim()) return providerKey.trim();
    if (process.env.LIMON_API_KEY && process.env.LIMON_API_KEY.trim()) return process.env.LIMON_API_KEY.trim();
    return "";
}

function resolveAgentHome(cfg) {
    if (!cfg || !cfg.workDir) return null;
    let agentHome = cfg.agentHome ? path.resolve(cfg.agentHome) : path.resolve(cfg.workDir);
    if (!isPathWithin(cfg.workDir, agentHome)) {
        agentHome = path.resolve(cfg.workDir);
    }
    fs.mkdirSync(agentHome, { recursive: true });
    cfg.agentHome = agentHome;
    return agentHome;
}

function getAskFn(provider) {
    const askFn = { gemini: askGemini, claude: askClaude, openai: askOpenAI, ollama: askOllama }[provider];
    if (!askFn) throw new Error("Desteklenmeyen provider: " + provider);
    return askFn;
}

async function main() {
    const cli = parseCliArgs(process.argv);
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

    let cfg = loadConfig();
    let runtimeApiKey = resolveApiKey(cfg);
    let askFn = null;
    let executor = null;
    if (cli.forceSetup || !cfg.provider || !cfg.workDir || !runtimeApiKey) {
        printBanner();
        cfg = await setup(rl);
        runtimeApiKey = resolveApiKey(cfg);
    }

    resolveAgentHome(cfg);

    if (cli.clearHistoryFlag) clearHistory();

    function refreshRuntime() {
        runtimeApiKey = resolveApiKey(cfg);
        askFn = getAskFn(cfg.provider);
        executor = new CommandExecutor(cfg);
    }

    refreshRuntime();
    printBanner(cfg.workDir);
    const pName = cfg.provider.charAt(0).toUpperCase() + cfg.provider.slice(1);

    log.success(`${pName} ile baglandi.`);
    log.info(`Calisma  : ${c.yellow}${cfg.workDir}${c.reset}`);
    if (cfg.agentHome) log.info(`Ajan alani: ${c.yellow}${cfg.agentHome}${c.reset}`);
    log.info(`Guvenlik : ${cfg.securityEnabled !== false ? c.green + "ACIK" : c.red + "KAPALI"}${c.reset}`);
    log.info(`App acma : ${cfg.allowAppLaunch === true ? c.green + "ACIK" : c.red + "KAPALI"}${c.reset}`);
    log.info(`API cagrilari : ${cfg.allowApiCalls === true ? c.green + "ACIK" : c.red + "KAPALI"}${c.reset}`);
    log.info(`Komutlar : ${c.yellow}--setup${c.reset} | ${c.yellow}--temizle${c.reset} | ${c.yellow}--quit${c.reset}`);
    console.log();

    async function runTurn(raw) {
        const t = (raw || "").trim();
        if (!t) return true;

        if (t === "--quit") {
            log.ai("Gorusmek uzere!", cfg.provider);
            return false;
        }

        if (t === "--setup") {
            clearHistory();
            cfg = await setup(rl);
            resolveAgentHome(cfg);
            refreshRuntime();
            printBanner(cfg.workDir);
            return true;
        }

        if (t === "--clear") {
            clearHistory();
            log.success("Gecmis temizlendi.");
            console.log();
            return true;
        }

        try {
            log.info("Dusunuyor...");
            let result;
            if (cfg.provider === "ollama") {
                result = await askFn(t, cfg, cfg.workDir);
            } else {
                result = await askFn(t, runtimeApiKey, cfg.workDir);
            }
            const { message, command } = result;

            if (message) log.ai(message, cfg.provider);

            if (command) {
                const needsApproval = shouldRequireApproval(command, cfg.workDir, cfg.agentHome);
                const ok = needsApproval
                    ? await requestApproval(command, rl, cfg.workDir, cfg.agentHome, cfg.allowAppLaunch === true)
                    : true;
                if (ok) {
                    try {
                        log.info("Calistiriliyor...");
                        const out = await executor.execute(command);
                        if (command.type === "file" && command.action === "read" && cfg.allowAppLaunch === true) {
                            const absPath = path.resolve(cfg.workDir, command.path);
                            const opened = openInEditor(absPath);
                            if (opened.ok) {
                                console.log(`\n  ${c.green}Sonuc:${c.reset}`);
                                console.log(`  ${c.gray}|${c.reset} Editor acildi: ${absPath}`);
                                console.log();
                            } else {
                                console.log(`\n  ${c.green}Sonuc:${c.reset}`);
                                String(out)
                                    .split("\n")
                                    .forEach((l) => console.log(`  ${c.gray}|${c.reset} ${l}`));
                                console.log();
                            }
                        } else {
                            console.log(`\n  ${c.green}Sonuc:${c.reset}`);
                            String(out)
                                .split("\n")
                                .forEach((l) => console.log(`  ${c.gray}|${c.reset} ${l}`));
                            console.log();
                        }
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
        await runTurn(cli.oneShotQuery);
        rl.close();
        return;
    }

    const ask = () => {
        rl.question(`  ${c.green}Siz${c.reset} ${c.gray}>${c.reset} `, async (raw) => {
            const keepGoing = await runTurn(raw);
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
