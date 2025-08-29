from __future__ import annotations

from typing import Any, Dict

from .base import BaseAgent


class OpsAgent(BaseAgent):
    """Collect operational metrics."""

    def __init__(self) -> None:
        super().__init__("ops")

    async def handle(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        return {"message": "ops placeholder"}

    async def report_metric(self, name: str, value: Any) -> Dict[str, Any]:
        return {"name": name, "value": value}
