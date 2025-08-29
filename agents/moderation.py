from __future__ import annotations

from typing import Any, Dict

from .base import BaseAgent


class ModerationAgent(BaseAgent):
    """Perform text and image moderation."""

    def __init__(self) -> None:
        super().__init__("moderation")

    async def handle(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        return {"message": "moderation placeholder"}

    async def moderate_text(self, text: str) -> Dict[str, Any]:
        return {"text": text, "flagged": False}

    async def moderate_image(self, image_url: str) -> Dict[str, Any]:
        return {"image_url": image_url, "flagged": False}
