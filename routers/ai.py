from fastapi import APIRouter

router = APIRouter()

@router.get("/help")
async def get_ai_help():
    return {"message": "AI Assistant provides overall help"}
