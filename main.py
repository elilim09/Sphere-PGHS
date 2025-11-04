from fastapi import FastAPI, APIRouter, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
from datetime import date
import openai
import os
import hashlib
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 발급받은 API 키를 설정합니다.
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()
router = APIRouter()

# 'meal_img' 디렉토리를 정적 파일 경로로 마운트합니다.
app.mount("/static", StaticFiles(directory="meal_img"), name="static")
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def read_root(request: Request, meal_description: str = Query(None)):
    meal_date = date.today().strftime("%Y%m%d")
    url = f"https://open.neis.go.kr/hub/mealServiceDietInfo?Type=json&pIndex=1&pSize=100&ATPT_OFCDC_SC_CODE=J10&SD_SCHUL_CODE=7531255&MLSV_YMD={meal_date}"
    
    meal_info_list = []
    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(url)
        data = response.json()
        if "mealServiceDietInfo" in data:
            meal_info_list = [item['DDISH_NM'] for item in data['mealServiceDietInfo'][1]['row']]

    image_url = None
    if meal_description:
        # 파일명 생성을 위해 해시값 사용
        hasher = hashlib.sha256()
        hasher.update(meal_description.encode('utf-8'))
        filename_base = hasher.hexdigest()[:10]
        filename = f"{meal_date}_{filename_base}.png"
        filepath = os.path.join("meal_img", filename)

        if os.path.exists(filepath):
            image_url = f"/static/{filename}"
        else:
            response = client.images.generate(
                model="dall-e-3",
                prompt=f"{meal_description} 이 음식 리스트를 학교 급식판 안에 그려",
                size="1024x1024",
                quality="standard",
                n=1,
            )
            generated_image_url = response.data[0].url
            
            # 생성된 이미지를 다운로드하여 저장
            async with httpx.AsyncClient() as image_client:
                image_response = await image_client.get(generated_image_url)
                with open(filepath, "wb") as f:
                    f.write(image_response.content)
            
            image_url = f"/static/{filename}"

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "meal_date": meal_date, 
        "meal_list": meal_info_list, 
        "image_url": image_url, 
        "meal_description": meal_description
    })

app.include_router(router)

