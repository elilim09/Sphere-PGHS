from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates
import httpx
from datetime import date

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/meal")
async def get_meal(meal_date: str = Query(None)):
    if meal_date is None:
        meal_date = date.today().strftime("%Y%m%d")

    url = f"https://open.neis.go.kr/hub/mealServiceDietInfo?Type=json&pIndex=1&pSize=100&ATPT_OFCDC_SC_CODE=J10&SD_SCHUL_CODE=7531255&MLSV_YMD={meal_date}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        return data

@router.get("/meal/view")
async def get_meal_view(request: Request, meal_date: str = Query(None)):
    if meal_date is None:
        meal_date = date.today().strftime("%Y%m%d")

    url = f"https://open.neis.go.kr/hub/mealServiceDietInfo?Type=json&pIndex=1&pSize=100&ATPT_OFCDC_SC_CODE=J10&SD_SCHUL_CODE=7531255&MLSV_YMD={meal_date}"
    
    meal_info_str = ""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        if "mealServiceDietInfo" in data:
            meal_info_list = [item['DDISH_NM'] for item in data['mealServiceDietInfo'][1]['row']]
            meal_info_str = "<br/><br/>".join(meal_info_list)

    return templates.TemplateResponse("meal.html", {"request": request, "meal_date": meal_date, "meal_info": meal_info_str})

@router.post("/meal/image")
async def create_meal_image():
    return {"message": "이미지 보여주"}

@router.get("/meal/display")
async def display_meal():
    return {"message": "Display meal information"}
