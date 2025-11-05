from fastapi import FastAPI, Request, Query, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
from datetime import date, datetime
import openai
import os
import hashlib
from dotenv import load_dotenv
import json
import shutil

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 발급받은 API 키를 설정합니다.
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# 'meal_img' 디렉토리를 정적 파일 경로로 마운트합니다.
app.mount("/static", StaticFiles(directory="meal_img"), name="static")
# 'lost_and_found_images' 디렉토리를 정적 파일 경로로 마운트합니다.
app.mount("/lost_images", StaticFiles(directory="lost_and_found_images"), name="lost_images")

templates = Jinja2Templates(directory="templates")

@app.get("/")
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

@app.get("/lost")
async def get_lost_items(request: Request):
    if not os.path.exists("lost_items.json") or os.path.getsize("lost_items.json") == 0:
        lost_items = []
    else:
        with open("lost_items.json", "r") as f:
            lost_items = json.load(f)
    return templates.TemplateResponse("lost_list.html", {"request": request, "lost_items": lost_items})

@app.get("/lost/new")
async def new_lost_item_form(request: Request):
    return templates.TemplateResponse("lost_form.html", {"request": request})

@app.post("/lost/new")
async def create_lost_item(request: Request, item_name: str = Form(...), item_description: str = Form(...), image: UploadFile = File(...)):
    # 이미지 저장
    image_filename = f"{date.today().strftime('%Y%m%d')}_{image.filename}"
    image_path = os.path.join("lost_and_found_images", image_filename)
    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # JSON 파일에 데이터 추가
    if not os.path.exists("lost_items.json") or os.path.getsize("lost_items.json") == 0:
        lost_items = []
    else:
        with open("lost_items.json", "r") as f:
            lost_items = json.load(f)
            
    new_item = {
        "name": item_name, 
        "description": item_description, 
        "image_url": f"/lost_images/{image_filename}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    lost_items.append(new_item)
    
    with open("lost_items.json", "w") as f:
        json.dump(lost_items, f, indent=4)

    return templates.TemplateResponse("lost_list.html", {"request": request, "lost_items": lost_items})

@app.get("/lost/search")
async def search_lost_items(request: Request, query: str = Query(None)):
    if not os.path.exists("lost_items.json") or os.path.getsize("lost_items.json") == 0:
        lost_items = []
    else:
        with open("lost_items.json", "r") as f:
            lost_items = json.load(f)
    
    if query:
        search_results = [item for item in lost_items if query.lower() in item['name'].lower() or query.lower() in item['description'].lower()]
    else:
        search_results = lost_items
        
    return templates.TemplateResponse("lost_search.html", {"request": request, "lost_items": search_results, "query": query})
