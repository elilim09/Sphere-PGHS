from __future__ import annotations

from typing import Any, Dict

from .base import BaseAgent


class VisionQAgent(BaseAgent):
    """Inspect images for quality and extract categories."""

    def __init__(self) -> None:
        super().__init__("vision_qa")

    async def handle(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        return {"message": "vision QA placeholder"}

    async def check_image_quality(self, image_url: str) -> Dict[str, Any]:
        return {"image_url": image_url, "quality": "good"}

    async def extract_category(self, image_url: str) -> Dict[str, Any]:
        return {"image_url": image_url, "category": "unknown"}
