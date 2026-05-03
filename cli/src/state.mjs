import fs from "node:fs";
import path from "node:path";

export function defaultState() {
  return {
    profile: "dev",
    preferredModel: "auto",
    vision: "auto",
    lastRunId: null,
    lastEventId: null,
    sessionTokensTotal: 0,
    sessionCostUsd: 0,
    route: null,
    model: null,
    runtime: null,
    eventRing: [],
  };
}

export function loadState(workspaceDir) {
  const p = path.join(workspaceDir, ".open-peak", "last_session.json");
  try {
    return JSON.parse(fs.readFileSync(p, "utf-8"));
  } catch {
    return defaultState();
  }
}

export function saveState(workspaceDir, state) {
  const dir = path.join(workspaceDir, ".open-peak");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "last_session.json"), JSON.stringify({ ...state, last_updated_at: new Date().toISOString() }, null, 2));
}

