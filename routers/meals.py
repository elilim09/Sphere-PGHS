from fastapi import APIRouter

from agents import MealsAgent

router = APIRouter()
meals_agent = MealsAgent()


@router.get("/meal")
async def get_meal(date: str):
    """Return meal information for a given date."""
    return await meals_agent.get_meals(date)


@router.post("/meal/image")
async def create_meal_image(menu: list[dict]):
    """Generate a meal tray image from menu data."""
    url = await meals_agent.generate_meal_tray_image(menu)
    return {"image_url": url}
