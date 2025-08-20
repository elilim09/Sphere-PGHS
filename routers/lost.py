from fastapi import APIRouter

router = APIRouter()

@router.post("/upload")
async def upload_lost_item():
    return {"message": "Upload a picture of a lost item"}

@router.get("/items")
async def get_lost_items():
    return {"message": "Display lost items"}
