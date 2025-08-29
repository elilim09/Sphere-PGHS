from fastapi import APIRouter

from agents import LostFoundAgent

router = APIRouter()
lost_agent = LostFoundAgent()


@router.post("/items")
async def create_lost_item(item: dict):
    """Register a new lost item."""
    return await lost_agent.create_item(item)


@router.get("/items")
async def get_lost_items(q: str | None = None):
    """Search lost items by keyword."""
    if q:
        return await lost_agent.search_items(q)
    return await lost_agent.search_items("")
