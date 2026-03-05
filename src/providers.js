/**
 * AI providers
 */

const history = [];

function buildSystemPrompt(workDir) {
    return `Sen Limon adinda terminal tabanli bir AI asistansin.
Yalnizca su sandbox dizininde islem yapabilirsin: ${workDir}

ZORUNLU: Her yanitinda sadece gecerli bir JSON objesi dondur.

Komut gerekmiyorsa:
{"message":"Kullaniciya Turkce yanit","command":null}

Dosya islemleri:
{"message":"Aciklama","command":{"type":"file","action":"write","path":"./notlar/todo.txt","content":"..."}}
{"message":"Aciklama","command":{"type":"file","action":"append","path":"./notlar/todo.txt","content":"..."}}
{"message":"Aciklama","command":{"type":"file","action":"read","path":"./notlar/todo.txt"}}
{"message":"Aciklama","command":{"type":"file","action":"delete","path":"./notlar/todo.txt"}}
{"message":"Aciklama","command":{"type":"file","action":"mkdir","path":"./notlar"}}
{"message":"Aciklama","command":{"type":"file","action":"list","path":"."}}
{"message":"Aciklama","command":{"type":"file","action":"move","path":"./a.txt","to":"./arsiv/a.txt"}}

Shell komutu:
{"message":"Aciklama","command":{"type":"shell","action":"Kisa aciklama","exec":"ls -la"}}

Uygulama acma:
{"message":"Aciklama","command":{"type":"app","action":"Uygulama ac","app":"firefox","args":[]}}

KURALLAR:
- Turkce yaz.
- Sadece JSON dondur.
- ../ kullanma, sandbox disina cikma.
- Belirsiz durumda command:null don ve once aciklayici mesaj ver.`;
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
            generationConfig: { temperature: 0.2 },
        }),
    });
    if (!res.ok) {
        if (res.status === 429) throw new Error("Gemini kota asildi. Biraz bekleyin.");
        if (res.status === 400 || res.status === 401) throw new Error("Gemini API key gecersiz.");
        throw new Error("Gemini hatasi (" + res.status + ")");
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
    if (!res.ok) throw new Error("Claude hatasi (" + res.status + ")");
    const data = await res.json();
    const text = data.content?.[0]?.text || "";
    history.push({ role: "assistant", content: text });
    return parseResponse(text);
}

async function askOpenAI(userMessage, apiKey, workDir) {
    if (!history.length || history[0].role !== "system") {
        history.unshift({ role: "system", content: buildSystemPrompt(workDir) });
    }
    history.push({ role: "user", content: userMessage });
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
        body: JSON.stringify({ model: "gpt-4o-mini", messages: history, temperature: 0.2 }),
    });
    if (!res.ok) throw new Error("OpenAI hatasi (" + res.status + ")");
    const data = await res.json();
    const text = data.choices?.[0]?.message?.content || "";
    history.push({ role: "assistant", content: text });
    return parseResponse(text);
}

function parseResponse(text) {
    const cleaned = text.replace(/```json\s*/g, "").replace(/```\s*/g, "").trim();

    const parsed = tryParse(cleaned) || tryParseFromBody(cleaned);
    if (!parsed) return { message: cleaned || text, command: null };

    if (parsed.message === undefined) return { message: cleaned || text, command: null };
    return { message: String(parsed.message), command: sanitizeCommand(parsed.command) };
}

function tryParse(raw) {
    try {
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

function tryParseFromBody(raw) {
    const match = raw.match(/\{[\s\S]*"message"[\s\S]*\}/);
    if (!match) return null;
    return tryParse(match[0]);
}

function sanitizeCommand(command) {
    if (!command || typeof command !== "object") return null;
    const allowed = new Set(["shell", "file", "app", "api"]);
    if (!allowed.has(command.type)) return null;
    return command;
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
