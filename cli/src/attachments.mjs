import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const IMAGE_EXT = new Set([".png", ".jpg", ".jpeg", ".webp"]);

export function parseAttachments(inputLine) {
  const parts = inputLine.split(/\s+/);
  const paths = [];
  const rest = [];
  for (const p of parts) {
    if (p.startsWith("@")) paths.push(p.slice(1));
    else rest.push(p);
  }
  return { message: rest.join(" "), paths };
}

export function loadAttachment({ workspaceDir, relPath, maxBytes, maxLines }) {
  const full = path.resolve(workspaceDir, relPath);
  const ext = path.extname(full).toLowerCase();
  const buf = fs.readFileSync(full);

  if (IMAGE_EXT.has(ext)) {
    const mime = ext === ".jpg" ? "image/jpeg" : `image/${ext.slice(1)}`;
    return { type: "image", path: `workspace/${relPath}`, mime };
  }

  const text = buf.toString("utf-8");
  const lines = text.split("\n");
  const truncated = buf.byteLength > maxBytes || lines.length > maxLines;
  if (!truncated) return { type: "text", path: `workspace/${relPath}`, content: text, truncated: false };

  const head = lines.slice(0, 200);
  const tail = lines.slice(Math.max(0, lines.length - 50));
  const sha256 = crypto.createHash("sha256").update(buf).digest("hex");
  const content = [
    `TRUNCATED attachment`,
    `path=${relPath}`,
    `total_lines=${lines.length}`,
    `bytes=${buf.byteLength}`,
    `sha256=${sha256}`,
    ``,
    ...head,
    ``,
    `...`,
    ``,
    ...tail,
  ].join("\n");
  return { type: "text", path: `workspace/${relPath}`, content, truncated: true };
}

