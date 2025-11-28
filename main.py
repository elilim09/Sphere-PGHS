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
from typing import List, Optional
from pydantic import BaseModel

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


class AgentAction(BaseModel):
    type: str
    target: Optional[str] = None
    message: Optional[str] = None


class AgentRequest(BaseModel):
    message: str
    current_path: Optional[str] = "/"


class AgentResponse(BaseModel):
    reply: str
    actions: List[AgentAction]

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
                prompt=f"당신은 학교 급식 예시 메뉴를 그리는 에이전트이다. 당신이 그려야 할 실제 학교 급식판은 급식판은 스테인리스로 제작된 직사각형 금속 식판으로, 표면은 매끄럽고 은색 광택이 나며 전체적으로 단단하고 위생적인 느낌을 준다. 이 급식판은 여섯 개의 칸으로 구성되어 있는데, 각 칸은 서로 높이가 같은 얕은 오목 형태이며, 금속판을 성형하여 자연스럽게 이어진 구조다. 모서리는 모두 부드럽게 둥글려 있어 사용 시 손에 걸리는 부분이 없도록 처리되어 있다. 가장 큰 칸은 직사각형 형태로 왼쪽 하단에 위치하며, 밥이나 메인 요리를 담기 알맞은 넓이를 갖고 있다. 이 칸은 다른 칸보다 면적이 넓고 단순한 형태다. 오른쪽 하단에는 원형의 깊지 않은 둥근 칸이 자리 잡고 있는데, 국이나 액체가 있는 음식을 담기 좋도록 둘레가 둥글게 처리가 되어 있다. 상단에는 여러 크기의 작은 칸이 나뉘어 있는데, 그중 하나는 좁고 길게 세로로 배열된 직사각형 칸 두 개가 나란히 배치된 형태로 되어 있어 볶음류나 조림류 같은 작은 반찬을 구분하여 담을 수 있게 구성되어 있다. 그 옆에는 정사각형 또는 작은 직사각형 형태의 보조 반찬 칸들이 자리하며, 각각 깊이는 동일하지만 크기가 다르다. 전체적으로 이 급식판은 여러 종류의 반찬과 국, 밥을 한 번에 분리하여 담는 데 최적화된 구조를 가지고 있으며, 칸마다 형태가 미묘하게 다르지만 서로 자연스럽게 이어지는 통일된 금속 일체형 디자인으로 이루어져 있다. 스테인리스 특유의 얇고 단단한 재질 덕분에 무게는 과도하지 않으면서도 강도가 높고, 세척이 용이하도록 모서리와 칸의 경계가 자연스럽게 완만하게 연결되어 있는 것이 특징이다.\n\n 아래 리스트의 음식을 급식판에 실제와 같이 그려라. 단, 항상 실사와 같이 묘사하고 음식은 컬러로 표시하여라.\n {meal_description}",
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


@app.post("/api/agent", response_model=AgentResponse)
async def ai_agent_endpoint(payload: AgentRequest):
    system_prompt = (
        "너는 Sphere-PGHS의 Zero-touch UI 에이전트이다. 사용자의 명령을 이해해 페이지 이동, 필터 설정, 게시글 작성"
        " 흐름 등 UI 제어를 돕는다. 모든 응답은 JSON 형식이어야 하며, 친근한 한국어 `reply`와 함께 실행할 동작을"
        " `actions` 배열로 제공한다.\n\n"
        "동작 타입:\n"
        "- navigate: `target`에 이동할 경로(URL path) 지정.\n"
        "- announce: 화면 상에 안내만 하고 동작 없음.\n"
        "- search_lost: 분실물 검색 페이지로 이동하며 쿼리를 쿼리스트링에 포함.\n"
        "- open_form: 분실물 등록 폼으로 이동.\n"
        "답변 예시: {\"reply\":\"분실물 등록을 열게요\", \"actions\":[{\"type\":\"open_form\", \"target\":\"/lost/new\"}]}."
    )

    user_prompt = (
        f"사용자 메시지: {payload.message}\n"
        f"현재 페이지 경로: {payload.current_path}\n"
        "의도가 분실물 검색이라면 /lost/search?q=키워드 형태로 target을 작성하고, 등록 폼은 /lost/new, 급식 홈은 / 로"
        " 이동하도록 안내한다. 반드시 JSON 객체 하나만 응답한다."
    )

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.5,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    try:
        content = completion.choices[0].message.content
        parsed = json.loads(content)
    except Exception:
        parsed = {"reply": "지금은 요청을 이해하지 못했어요. 다시 한 번 말씀해 주세요!", "actions": [{"type": "announce"}]}

    reply_text = parsed.get("reply", "")
    actions_raw = parsed.get("actions", [])
    actions = []
    for action in actions_raw:
        if isinstance(action, dict) and "type" in action:
            actions.append(AgentAction(type=action.get("type", "announce"), target=action.get("target"), message=action.get("message")))

    if not actions:
        actions = [AgentAction(type="announce", message="확인했어요.")]

    return AgentResponse(reply=reply_text, actions=actions)
