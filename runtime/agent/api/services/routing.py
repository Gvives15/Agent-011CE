from __future__ import annotations

from typing import Dict, Tuple

from api.schemas import Attachment, RunOptions


def decide_route(
    *,
    message: str,
    attachments: list[Attachment],
    options: RunOptions,
    models: Dict[str, str],
    enable_ui: bool,
) -> Tuple[str, str]:
    if options.vision == "never":
        return "logic", models["logic"]

    if options.vision == "always":
        return "vision", models["vision"]

    if options.preferred_model == "ui-tars":
        if not enable_ui:
            return "error", ""
        return "ui", models["ui"]

    if any(a.type == "image" for a in attachments):
        return "vision", models["vision"]

    msg_lower = message.lower()
    if "analiz" in msg_lower and "imagen" in msg_lower:
        return "vision", models["vision"]
    if "mirá la imagen" in msg_lower or "mira la imagen" in msg_lower:
        return "vision", models["vision"]

    return "logic", models["logic"]
