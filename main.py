from fastapi import FastAPI, Request, Query, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
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

MEAL_CACHE_PATH = "meal_cache.json"
meal_cache = {"meal_date": None, "meal_list": [], "neis_error": None}


def load_cached_meals():
    if not os.path.exists(MEAL_CACHE_PATH):
        return None

    try:
        with open(MEAL_CACHE_PATH, "r", encoding="utf-8") as cache_file:
            cached = json.load(cache_file)
            if {
                "meal_date",
                "meal_list",
                "neis_error",
            }.issubset(cached.keys()):
                return cached
    except Exception as e:
        print(f"[MEAL CACHE] 캐시 파일 로드 실패: {e}")

    return None


def save_meal_cache(data: dict):
    try:
        with open(MEAL_CACHE_PATH, "w", encoding="utf-8") as cache_file:
            json.dump(data, cache_file, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[MEAL CACHE] 캐시 파일 저장 실패: {e}")


async def fetch_meals_from_neis(meal_date: str):
    url = (
        "https://open.neis.go.kr/hub/mealServiceDietInfo"
        f"?Type=json&pIndex=1&pSize=100"
        f"&ATPT_OFCDC_SC_CODE=J10&SD_SCHUL_CODE=7531255&MLSV_YMD={meal_date}"
    )

    meal_info_list = []
    neis_error = None

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.get(url)
                response.raise_for_status()
                data = response.json()

                if "mealServiceDietInfo" in data:
                    meal_info_list = [
                        item["DDISH_NM"]
                        for item in data["mealServiceDietInfo"][1]["row"]
                    ]
                break
        except httpx.ReadTimeout:
            print(f"[NEIS] 급식 정보 요청 타임아웃 발생 (시도 {attempt}/{max_attempts})")
            if attempt == max_attempts:
                neis_error = "급식 정보를 불러오는 중 시간이 초과되었습니다."
        except httpx.HTTPError as e:
            print(f"[NEIS] HTTP 오류 발생: {e}")
            neis_error = "급식 정보를 불러오는 중 오류가 발생했습니다."
            break
        except Exception as e:
            print(f"[NEIS] 알 수 없는 오류: {e}")
            neis_error = "급식 정보를 불러오는 중 알 수 없는 오류가 발생했습니다."
            break

    return meal_info_list, neis_error


@app.on_event("startup")
async def initialize_meal_cache():
    meal_date = date.today().strftime("%Y%m%d")
    cached = load_cached_meals()

    if cached and cached.get("meal_date") == meal_date:
        meal_cache.update(cached)
        return

    meal_list, neis_error = await fetch_meals_from_neis(meal_date)
    updated_cache = {
        "meal_date": meal_date,
        "meal_list": meal_list,
        "neis_error": neis_error,
    }
    meal_cache.update(updated_cache)
    save_meal_cache(updated_cache)


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

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, meal_description: str = Query(None)):
    meal_date = meal_cache.get("meal_date") or date.today().strftime("%Y%m%d")
    meal_info_list = meal_cache.get("meal_list", [])
    neis_error = meal_cache.get("neis_error")

    # =============================
    # 아래부터는 기존 이미지 생성 로직 그대로 활용
    # =============================
    image_url = None
    if meal_description:
        hasher = hashlib.sha256()
        hasher.update(meal_description.encode("utf-8"))
        filename_base = hasher.hexdigest()[:10]
        filename = f"{meal_date}_{filename_base}.png"
        filepath = os.path.join("meal_img", filename)

        if os.path.exists(filepath):
            image_url = f"/static/{filename}"
        else:
            # OpenAI 이미지 생성도 네트워크 호출이라, 여기도 try/except 달아두면 더 안전함
            try:
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=(
                        "당신은 학교 급식 예시 메뉴를 그리는 에이전트이다. 당신이 그려야 할 실제 학교 급식판은 급식판은 스테인리스로 제작된 직사각형 금속 식판으로, 표면은 매끄럽고 은색 광택이 나며 전체적으로 단단하고 위생적인 느낌을 준다. 이 급식판은 여섯 개의 칸으로 구성되어 있는데, 각 칸은 서로 높이가 같은 얕은 오목 형태이며, 금속판을 성형하여 자연스럽게 이어진 구조다. 모서리는 모두 부드럽게 둥글려 있어 사용 시 손에 걸리는 부분이 없도록 처리되어 있다. 가장 큰 칸은 직사각형 형태로 왼쪽 하단에 위치하며, 밥이나 메인 요리를 담기 알맞은 넓이를 갖고 있다. 이 칸은 다른 칸보다 면적이 넓고 단순한 형태다. 오른쪽 하단에는 원형의 깊지 않은 둥근 칸이 자리 잡고 있는데, 국이나 액체가 있는 음식을 담기 좋도록 둘레가 둥글게 처리가 되어 있다. 상단에는 여러 크기의 작은 칸이 나뉘어 있는데, 그중 하나는 좁고 길게 세로로 배열된 직사각형 칸 두 개가 나란히 배치된 형태로 되어 있어 볶음류나 조림류 같은 작은 반찬을 구분하여 담을 수 있게 구성되어 있다. 그 옆에는 정사각형 또는 작은 직사각형 형태의 보조 반찬 칸들이 자리하며, 각각 깊이는 동일하지만 크기가 다르다. 전체적으로 이 급식판은 여러 종류의 반찬과 국, 밥을 한 번에 분리하여 담는 데 최적화된 구조를 가지고 있으며, 칸마다 형태가 미묘하게 다르지만 서로 자연스럽게 이어지는 통일된 금속 일체형 디자인으로 이루어져 있다. 스테인리스 특유의 얇고 단단한 재질 덕분에 무게는 과도하지 않으면서도 강도가 높고, 세척이 용이하도록 모서리와 칸의 경계가 자연스럽게 완만하게 연결되어 있는 것이 특징이다.\n\n 아래 리스트의 음식을 급식판에 실제와 같이 그려라. 단, 항상 실사와 같이 묘사하고 음식은 컬러로 표시하여라.\n "
                        f"{meal_description}"
                    ),
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                generated_image_url = response.data[0].url

                async with httpx.AsyncClient(timeout=20.0) as image_client:
                    image_response = await image_client.get(generated_image_url)
                    with open(filepath, "wb") as f:
                        f.write(image_response.content)

                image_url = f"/static/{filename}"
            except Exception as e:
                print(f"[IMAGE] 급식 이미지 생성/다운로드 오류: {e}")
                image_url = None

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "meal_date": meal_date,
            "meal_list": meal_info_list,
            "image_url": image_url,
            "meal_description": meal_description,
            "neis_error": neis_error,  # 템플릿에서 필요하면 표시
        },
    )

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
        "- search_lost: 분실물 검색을 실행. target에는 검색어를 채우고, 검색 페이지로 이동이 필요하면 /lost/search?q=키워드로 이동.\n"
        "- open_form 또는 open_lost_form: 분실물 등록 폼으로 이동.\n"
        "- fill_field: target에 item_name/item_description을 넣고 message에는 채울 값을 넣어 필드를 완성.\n"
        "- submit_lost_form: 작성된 폼을 제출. 필요 시 open_form→fill_field→submit_lost_form 순서를 붙인다.\n"
        "- focus_search: 검색창을 포커스.\n"
        "- toggle_overlay: target에 open/close를 넣어 AI 오버레이를 열거나 닫음.\n"
        "- open_meal_image: 급식 카드의 '보기' 버튼을 클릭해 이미지를 띄움. target에 급식 메뉴 텍스트를 포함.\n"
        "답변 예시: {\"reply\":\"분실물 등록을 열게요\", \"actions\":[{\"type\":\"open_form\", \"target\":\"/lost/new\"},{\"type\":\"fill_field\",\"target\":\"item_name\",\"message\":\"검은색 지갑\"}]}"
    )

    user_prompt = (
        f"사용자 메시지: {payload.message}\n"
        f"현재 페이지 경로: {payload.current_path}\n"
        "- 분실물 검색 의도는 search_lost로 target에 검색 키워드를 담아라.\n"
        "- 급식 이미지를 열어달라는 요청은 open_meal_image로 대응하고 target은 급식 메뉴 텍스트로 작성하라.\n"
        "- 페이지 이동은 navigate로, 등록 폼 이동은 open_form으로 표시한다. 폼 입력은 fill_field와 submit_lost_form을 사용한다. 반드시 JSON 객체 하나만 응답한다."
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