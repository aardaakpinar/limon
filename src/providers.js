/**
 * AI Sağlayıcıları
 */

const history = [];

function buildSystemPrompt(workDir) {
    return `Sen Limon adinda bir AI asistanissin. Yalnizca su calisma dizininde islem yapabilirsin: ${workDir}

ZORUNLU KURAL: Her yanitinda YALNIZCA gecerli bir JSON objesi dondur.

Komut gerekmiyorsa:
{"message": "Kullaniciya Turkce yanit", "command": null}

Dosya olusturmak icin:
{"message": "Aciklama", "command": {"type": "file", "action": "write", "path": "./dosya.py", "content": "icerik"}}

Dosya okumak icin:
{"message": "Aciklama", "command": {"type": "file", "action": "read", "path": "./dosya.py"}}

Dosya silmek icin:
{"message": "Aciklama", "command": {"type": "file", "action": "delete", "path": "./dosya.py"}}

Shell komutu icin:
{"message": "Aciklama", "command": {"type": "shell", "action": "Kisa aciklama", "exec": "komut"}}

ONEMLI: Dosya yollarinda calisma dizininin (${workDir}) disina cikma. ../ kullanma.
Her zaman Turkce yanit ver. Sadece JSON dondur.`;
}

async function askGemini(userMessage, apiKey, workDir) {
    history.push({ role: "user", parts: [{ text: userMessage }] });
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=${apiKey}`;
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            system_instruction: { parts: [{ text: buildSystemPrompt(workDir) }] },
            contents: history,
            generationConfig: { temperature: 0.3 },
        }),
    });
    if (!res.ok) {
        if (res.status === 429) throw new Error("Gemini kota aşıldı. Biraz bekleyin.");
        if (res.status === 400 || res.status === 401) throw new Error("Gemini API key geçersiz.");
        throw new Error("Gemini hatası (" + res.status + ")");
    }
    const data = await res.json();
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text || "";
    history.push({ role: "model", parts: [{ text }] });
    return parseResponse(text);
}

async function askClaude(userMessage, apiKey, workDir) {
    history.push({ role: "user", content: userMessage });
    const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-api-key": apiKey, "anthropic-version": "2023-06-01" },
        body: JSON.stringify({
            model: "claude-3-5-haiku-20241022",
            max_tokens: 1024,
            system: buildSystemPrompt(workDir),
            messages: history,
        }),
    });
    if (!res.ok) throw new Error("Claude hatası (" + res.status + ")");
    const data = await res.json();
    const text = data.content?.[0]?.text || "";
    history.push({ role: "assistant", content: text });
    return parseResponse(text);
}

async function askOpenAI(userMessage, apiKey, workDir) {
    if (!history.length || history[0].role !== "system")
        history.unshift({ role: "system", content: buildSystemPrompt(workDir) });
    history.push({ role: "user", content: userMessage });
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
        body: JSON.stringify({ model: "gpt-4o-mini", messages: history, temperature: 0.3 }),
    });
    if (!res.ok) throw new Error("OpenAI hatası (" + res.status + ")");
    const data = await res.json();
    const text = data.choices?.[0]?.message?.content || "";
    history.push({ role: "assistant", content: text });
    return parseResponse(text);
}

function parseResponse(text) {
    let cleaned = text
        .replace(/```json\s*/g, "")
        .replace(/```\s*/g, "")
        .trim();
    try {
        const j = JSON.parse(cleaned);
        if (j.message !== undefined) return { message: j.message, command: j.command || null };
    } catch {}
    const match = cleaned.match(/\{[\s\S]*"message"[\s\S]*\}/);
    if (match) {
        try {
            const j = JSON.parse(match[0]);
            if (j.message !== undefined) return { message: j.message, command: j.command || null };
        } catch {}
    }
    return { message: cleaned || text, command: null };
}

function clearHistory() {
    history.length = 0;
}

module.exports = {
    askGemini,
    askClaude,
    askOpenAI,
    parseResponse,
    clearHistory,
    buildSystemPrompt,
};