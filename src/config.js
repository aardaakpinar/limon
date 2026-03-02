/**
 * Config Yönetimi
 */

const fs = require("fs");
const path = require("path");
const os = require("os");

const CONFIG_DIR = path.join(os.homedir(), ".limon");
const CONFIG_FILE = path.join(CONFIG_DIR, "config.json");

function loadConfig() {
    try {
        return JSON.parse(fs.readFileSync(CONFIG_FILE, "utf8"));
    } catch {
        return {};
    }
}

function saveConfig(cfg) {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
    fs.writeFileSync(CONFIG_FILE, JSON.stringify(cfg, null, 2), "utf8");
}

module.exports = {
    CONFIG_DIR,
    CONFIG_FILE,
    loadConfig,
    saveConfig,
};