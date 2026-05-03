from __future__ import annotations

import time
import uuid
from pathlib import Path

from ninja import Router, Schema
from playwright.sync_api import sync_playwright

router = Router()


class ScreenshotRequest(Schema):
    url: str


@router.get("/health")
def health(request):
    return {"status": "ok", "version": "v1", "browser": {"enabled": True}}


@router.post("/screenshot")
def screenshot(request, payload: ScreenshotRequest):
    out_dir = Path("/workspace/.open-peak/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"screenshot_{int(time.time())}_{uuid.uuid4().hex}.png"
    out_path = out_dir / name

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(payload.url, wait_until="networkidle")
        page.screenshot(path=str(out_path), full_page=True)
        browser.close()

    return {"path": str(out_path), "mime": "image/png"}
