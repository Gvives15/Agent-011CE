import readline from "node:readline";

import { loadAttachment, parseAttachments } from "./attachments.mjs";
import { openSse } from "./sse.mjs";
import { defaultState, loadState, saveState } from "./state.mjs";

const workspaceDir = process.env.WORKSPACE_DIR || process.cwd();
const runtimeBase = process.env.RUNTIME_BASE || `http://127.0.0.1:${process.env.RUNTIME_PORT || "8000"}`;
const maxAttachBytes = Number(process.env.MAX_ATTACH_BYTES || "1000000");
const maxAttachLines = Number(process.env.MAX_ATTACH_LINES || "2000");

let state = loadState(workspaceDir);
let activeRunId = null;
let activeEs = null;
let isStreaming = false;

function printFooter() {
  process.stdout.write(
    `\n[route:${state.route || "?"}] [model:${state.model || "?"}] [usage:${state.sessionTokensTotal} tok] [profile:${state.profile}] [runtime:${state.runtime || "?"}]\n`
  );
}

async function postJson(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const t = await r.text();
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${t}`);
  return JSON.parse(t);
}

async function startRun({ message, attachments }) {
  const resp = await postJson(`${runtimeBase}/v1/runs`, {
    input: { message, attachments },
    options: { profile: state.profile, vision: state.vision, preferred_model: state.preferredModel, enable_browser: false },
  });

  activeRunId = resp.id;
  state.lastRunId = resp.id;
  saveState(workspaceDir, state);

  isStreaming = true;
  activeEs = openSse({
    url: `${runtimeBase}${resp.events_url}`,
    lastEventId: state.lastEventId || undefined,
    onEvent: async (type, e) => {
      const raw = e.data;
      if (e.lastEventId) state.lastEventId = e.lastEventId;
      state.eventRing.push(`[${type}] ${raw}`);
      if (state.eventRing.length > 1000) state.eventRing.shift();

      if (type === "status") {
        const d = JSON.parse(raw);
        state.route = d.route;
        state.model = d.model;
        state.runtime = "ok";
        printFooter();
      } else if (type === "token") {
        const d = JSON.parse(raw);
        process.stdout.write(d.text);
      } else if (type === "usage") {
        const d = JSON.parse(raw);
        state.sessionTokensTotal = d.session_tokens_total ?? state.sessionTokensTotal;
        state.sessionCostUsd = d.session_cost_usd ?? state.sessionCostUsd;
      } else if (type === "proposed_action") {
        const d = JSON.parse(raw);
        process.stdout.write(`\nproposed_action (${d.risk}): ${d.command}\n`);
        const approved = await question("Approve? (Y/n) ");
        const ok = approved.trim() === "" || approved.trim().toLowerCase() === "y";
        await postJson(`${runtimeBase}/v1/runs/${d.run_id}/actions/${d.action_id}/approve`, { approved: ok });
      } else if (type === "action_result") {
        const d = JSON.parse(raw);
        process.stdout.write(`\nexit_code=${d.exit_code}\n`);
        if (d.stdout) process.stdout.write(`${d.stdout}\n`);
        if (d.stderr) process.stdout.write(`${d.stderr}\n`);
      } else if (type === "error") {
        const d = JSON.parse(raw);
        process.stdout.write(`\nerror=${d.error_class} ${d.message}\n`);
      } else if (type === "final") {
        isStreaming = false;
        activeEs?.close();
        activeEs = null;
        activeRunId = null;
        saveState(workspaceDir, state);
        process.stdout.write("\n");
        printFooter();
      }
    },
  });
}

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
function question(q) {
  return new Promise((resolve) => rl.question(q, resolve));
}

async function handleCommand(line) {
  const trimmed = line.trim();
  if (!trimmed) return;

  if (trimmed === "/exit") process.exit(0);
  if (trimmed === "/help") {
    process.stdout.write("/help /model <logic|vision|ui-tars|auto> /profile <dev|browser|server> /debug /logs [n] /reset /exit\n");
    return;
  }
  if (trimmed.startsWith("/model ")) {
    const v = trimmed.split(/\s+/)[1] || "auto";
    if (v === "logic") {
      state.preferredModel = "auto";
      state.vision = "never";
    } else if (v === "vision") {
      state.preferredModel = "auto";
      state.vision = "always";
    } else if (v === "ui-tars") {
      state.preferredModel = "ui-tars";
      state.vision = "auto";
    } else {
      state.preferredModel = "auto";
      state.vision = "auto";
    }
    saveState(workspaceDir, state);
    return;
  }
  if (trimmed.startsWith("/profile ")) {
    state.profile = trimmed.split(/\s+/)[1] || "dev";
    saveState(workspaceDir, state);
    return;
  }
  if (trimmed === "/reset") {
    state = { ...defaultState(), profile: state.profile };
    saveState(workspaceDir, state);
    return;
  }
  if (trimmed.startsWith("/logs")) {
    const n = Number(trimmed.split(/\s+/)[1] || "100");
    const tail = state.eventRing.slice(Math.max(0, state.eventRing.length - n));
    for (const e of tail) process.stdout.write(`${e}\n`);
    return;
  }
  if (trimmed === "/debug") {
    const r = await fetch(`${runtimeBase}/v1/health`);
    process.stdout.write(`health=${await r.text()}\n`);
    const tail = state.eventRing.slice(Math.max(0, state.eventRing.length - 100));
    for (const e of tail) process.stdout.write(`${e}\n`);
    return;
  }

  const { message, paths } = parseAttachments(trimmed);
  const attachments = paths.map((p) => loadAttachment({ workspaceDir, relPath: p, maxBytes: maxAttachBytes, maxLines: maxAttachLines }));
  await startRun({ message, attachments });
}

process.on("SIGINT", async () => {
  if (isStreaming && activeRunId) {
    try {
      await postJson(`${runtimeBase}/v1/runs/${activeRunId}/abort`, {});
    } catch {}
    activeEs?.close();
    activeEs = null;
    activeRunId = null;
    isStreaming = false;
    process.stdout.write("\n");
    rl.prompt();
    return;
  }
  process.exit(0);
});

rl.setPrompt("> ");
rl.prompt();
rl.on("line", async (line) => {
  try {
    await handleCommand(line);
  } catch (e) {
    process.stderr.write(`${String(e)}\n`);
  } finally {
    rl.prompt();
  }
});
