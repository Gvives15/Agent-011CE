from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from ninja import Schema


AttachmentType = Literal["text", "image"]


class Attachment(Schema):
    type: AttachmentType
    path: str
    content: Optional[str] = None
    truncated: Optional[bool] = None
    mime: Optional[str] = None


class RunInput(Schema):
    message: str
    attachments: List[Attachment] = []


class RunOptions(Schema):
    profile: str = "dev"
    vision: str = "auto"
    preferred_model: str = "auto"
    enable_browser: bool = False


class CreateRunRequest(Schema):
    input: RunInput
    options: RunOptions


class CreateRunResponse(Schema):
    id: str
    events_url: str


class AbortResponse(Schema):
    id: str
    accepted: bool


class ApproveActionRequest(Schema):
    approved: bool


class ApproveActionResponse(Schema):
    action_id: str
    accepted: bool
