from fastapi import APIRouter

router = APIRouter()

@router.get("/meal")
async def get_meal():
    return {"message": "Get meal data from API"}

@router.post("/meal/image")
async def create_meal_image():
    return {"message": "Create meal image with AI"}

@router.get("/meal/display")
async def display_meal():
    return {"message": "Display meal information"}
