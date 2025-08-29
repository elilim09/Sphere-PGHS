from __future__ import annotations

from typing import Any, Dict, List

from .base import BaseAgent


class KnowledgeBaseAgent(BaseAgent):
    """Answer questions from school documents and timetables."""

    def __init__(self) -> None:
        super().__init__("knowledge_base")

    async def handle(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        return {"message": "knowledge base placeholder"}

    async def kb_search(self, query: str) -> List[Dict[str, Any]]:
        return []

    async def kb_get(self, section: str) -> Dict[str, Any]:
        return {"section": section, "content": ""}

    async def get_timetable(self, date: str) -> Dict[str, Any]:
        return {"date": date, "entries": []}

    async def get_timetable_changes(self, date: str) -> List[Dict[str, Any]]:
        return []
