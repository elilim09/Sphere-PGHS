from __future__ import annotations

from typing import Any, Dict, List

from .base import BaseAgent


class MealsAgent(BaseAgent):
    """Provide meal information and generate meal tray images."""

    def __init__(self) -> None:
        super().__init__("meals")

    async def handle(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - simple stub
        return {"message": "meals placeholder"}

    async def get_meals(self, date: str) -> Dict[str, Any]:
        return {"date": date, "menu": []}

    async def generate_meal_tray_image(self, menu_json: List[Dict[str, Any]]) -> str:
        return "https://example.com/meal.png"

    async def parse_allergen_codes(self, raw: str) -> List[int]:
        return [int(x) for x in raw.split(".") if x.isdigit()]
