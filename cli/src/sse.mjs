import EventSource from "eventsource";

export function openSse({ url, lastEventId, onEvent }) {
  const es = new EventSource(url, {
    headers: lastEventId ? { "Last-Event-ID": lastEventId } : undefined,
  });

  const types = ["status", "token", "message", "usage", "proposed_action", "action_result", "error", "final"];
  for (const t of types) {
    es.addEventListener(t, (e) => onEvent(t, e));
  }
  es.onerror = (e) => onEvent("error", { data: JSON.stringify({ message: "SSE_ERROR", raw: String(e) }) });
  return es;
}
