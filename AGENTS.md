# AGENTS.md — Sphere‑PGHS

코드 크래프터(PGHS) 연말 발표회용 통합 웹 **Sphere‑PGHS**의 인공지능(멀티‑에이전트) 설계 문서.

> 목표: \*\*학생의 터치 최소화(Zero‑UI 지향)\*\*로 급식 확인(텍스트+AI 이미지), 분실물 관리, 학교 전반 Q/A·내비게이션을 하나의 서비스에서 해결.

---

## 0) 전체 아키텍처 요약

* **클라이언트(UI)**: 반응형 웹(PC/모바일), 카드형 목록(오렌지+화이트, 당근마켓 스타일).
* **백엔드**: API 게이트웨이(FastAPI 권장) + DB(PostgreSQL) + 객체스토리지(이미지 업로드, e.g., S3 호환) + 캐시(Redis).
* **AI 계층(멀티 에이전트)**: 오케스트레이터(라우터) + 기능별 전문 에이전트(분실물, 급식, 학교 지식, 내비, 계정/권한, 모더레이션, 비전 QA, 운영/분석).
* **외부 연동**: NEIS 급식 OpenAPI, 학교 문서/규정 PDF·공지 RAG, (선택) 시간표 변동 데이터 소스.
* **시간대**: `Asia/Seoul` 고정. NEIS 캐시 프리페치: 매일 06:00/11:00 KST.

```
사용자 ↔ UI Copilot(내비) ↔ 오케스트레이터 ↔ [분실물/급식/지식/계정/모더레이션/비전QA/운영] 에이전트 ↔ 도구(DB, API, 파일, 캐시)
```

---

## 1) 비전(Goals) & 비범위(Non‑Goals)

**Goals**

1. 대화/음성/텍스트 명령 중심으로 사이트 전 영역 제어(페이지 이동/검색/정렬/상세 열람/상태 변경 등).
2. **급식**: NEIS 텍스트 출력 + **실제 급식판 느낌의 AI 이미지** 자동 생성(알레르기 표기 포함).
3. **분실물**: 학생이 직접 등록·검색·조회, 관리자는 전체 수정·삭제. 댓글/연락처 연결.
4. **학교 지식**: 생활규정, 교무실·교실 위치, 시간표 변동, 캠퍼스 내 길찾기/층수 안내.

**Non‑Goals**

* 학사행정 승인·공식 민원 처리(링크 안내까지만).
* 얼굴 인식 식별(개인 식별 비전은 사용하지 않음).

---

## 2) 에이전트 라인업(역할/책임)

### 2.1 오케스트레이터(Orchestrator)

* **역할**: 사용자의 발화를 \*\*의도(Intent)\*\*로 분류하고, 적절한 기능 에이전트에 라우팅. 실패 시 재프롬프트/백오프.
* **입력**: 사용자 발화(자연어), 대화 상태(Session), UI 컨텍스트(현재 페이지·선택 필터 등).
* **출력**: `intent`, `tool_call` 또는 `response`.
* **핵심 로직**: 우선 규칙 → 통계적 라우팅(의도 스코어) → 컨텍스트 결합(RAG) → 함수호출.

### 2.2 UI Copilot(내비게이터) 에이전트

* **역할**: "\~페이지로 이동", "정렬 바꿔", "내 글 모아봐" 등 UI 지시 수행.
* **도구**: `goto_page`, `set_filter`, `set_sort`, `open_item`, `open_profile`, `open_admin_panel` 등.
* **결과**: UI 상태 변경과 함께 간단 피드백(무엇을 바꿨는지).

### 2.3 분실물(Lost\&Found) 에이전트

* **역할**: 등록/검색/조회/상태변경/댓글/신고.
* **도구**: `create_item`, `search_items`, `get_item`, `update_item`, `update_item_status`, `delete_item`, `add_comment`, `list_user_items`, `upload_image`.
* **정책**:

  * 전화번호는 자동 마스킹(예: 010‑1234‑\*\*\*\*).
  * 개인정보/욕설 모더레이션 통과 필요.

### 2.4 급식(Meals) 에이전트

* **역할**: 날짜별 급식 텍스트 + **AI 이미지 생성**(식판 레이아웃, 반찬/국/밥 시각화, 알레르기 마크).
* **도구**: `get_meals(date|range)`, `generate_meal_tray_image(menu_json)`, `parse_allergen_codes`.
* **정책**: 알레르기 1\~19 표기, 영양정보 표는 옵션. 캐싱.

### 2.5 학교 지식(KB/RAG) 에이전트

* **역할**: 생활규정, 교무실/교실 위치, 층 안내, 시간표 변동 Q/A.
* **지식원**: PDF/문서/공지/배치도 → 텍스트 추출 → 청소·가공 → 임베딩 인덱스(Vector DB).
* **도구**: `kb_search(query)`, `kb_get(section)`, `get_timetable(date)`, `get_timetable_changes(date)`.
* **정책**: 답변 시 \*\*출처(문서명/개정일)\*\*를 UI에 표시.

### 2.6 계정/권한(Auth/RBAC) 에이전트

* **역할**: 로그인/프로필 수정, 역할 부여(관리자), 세션 관리.
* **정책**: RBAC(학생=기본, 관리자=교사/자치회 임원). 관리자 전용 버튼 노출.

### 2.7 모더레이션(Moderation) 에이전트

* **역할**: 이미지/텍스트 욕설, 개인정보 과다 노출, 스팸 감지.
* **행동**: 경고→가림 표시→관리자 알림→차단까지 단계적.

### 2.8 비전 QA(Vision‑QA) 에이전트

* **역할**: 분실물 사진 품질 검사(흔들림/어둠/낮은 해상도), 자동 보정 제안, 카테고리 추출(예: 가방/필통/옷).

### 2.9 운영/분석(Ops/Analytics) 에이전트

* **역할**: 쿼리 실패율, 도구 호출 지연, 인기 검색어, 신고 빈도 등 대시보드 제공.

---

## 3) 의도(Intent) 정의 & 예시 발화

> 다국어 가능하나 **기본 한국어**. 정규식/룰 기반 프리필터 + 분류기(softmax) 혼합.

| Intent             | 설명     | 예시 발화(학생)               | 라우팅        |
| ------------------ | ------ | ----------------------- | ---------- |
| `NAV.GOTO_PAGE`    | 페이지 이동 | "분실물 목록 보여줘", "급식 페이지로" | UI Copilot |
| `LOST.CREATE`      | 분실물 등록 | "지갑 잃어버렸어, 등록할래"        | 분실물        |
| `LOST.SEARCH`      | 검색/필터  | "파란 필통 찾아줘", "보관중만"     | 분실물        |
| `LOST.DETAIL`      | 상세 열람  | "두 번째 카드 열어"            | 분실물+UI     |
| `LOST.STATUS`      | 상태 변경  | "이건 보관중으로 바꿔"           | 분실물        |
| `MEAL.TODAY/DATE`  | 급식 조회  | "오늘 점심 뭐야?", "26일 급식"   | 급식         |
| `MEAL.IMAGE`       | 급식 이미지 | "급식 사진으로 만들어줘"          | 급식         |
| `KB.RULES`         | 생활규정   | "교복 규정 알려줘"             | KB/RAG     |
| `KB.MAP`           | 위치/층   | "국어과 교무실 어디야?"          | KB/RAG+내비  |
| `TIMETABLE.CHANGE` | 시간표 변동 | "내일 시간표 바뀌었어?"          | KB/RAG     |
| `ACCOUNT.UPDATE`   | 프로필 수정 | "닉네임 바꿔줘"               | Auth       |
| `ADMIN.MOD`        | 삭제/차단  | "욕설 댓글 삭제"              | 모더레이션      |

의도 스키마(요약):

```json
{
  "intent": "MEAL.TODAY",
  "slots": {"date": "2025-08-23"},
  "confidence": 0.91,
  "context": {"page": "home", "userRole": "student"}
}
```

---

## 4) 도구(툴)·함수 호출 명세

> 모든 툴 호출은 **JSON Schema** 명세와 타입 검증 필수. 실패 시 재시도(max 2) 후 친절한 오류 메시지.

### 4.1 UI 제어

```ts
function goto_page(name: "home"|"lost"|"meals"|"agent"|"admin", params?: object): void
function set_sort(list: "lost", key: "latest"|"status", order?: "asc"|"desc"): void
function set_filter(list: "lost", filter: {status?: "보관중"|"분실됨", q?: string}): void
function open_item(itemId: string): void
```

### 4.2 분실물 CRUD

```ts
function create_item(input: {
  title: string; description: string; images: string[];
  status: "보관중"|"분실됨"; place?: string;
  lostFoundDate?: string; contact?: string; category?: string;
}): {id: string}

function search_items(query: {q?: string; status?: "보관중"|"분실됨"; page?: number; size?: number}): {
  total: number; items: Array<{id:string; title:string; thumb:string; status:string; createdAt:string}>
}

function get_item(id: string): {
  id: string; title: string; description: string; images: string[]; status: string;
  place?: string; reporter:{id:string; nickname:string}; contactMasked?: string;
  comments: Array<{id:string; author:string; text:string; createdAt:string}>
}

function update_item(id: string, patch: Partial<{
  title: string; description: string; images: string[]; status: "보관중"|"분실됨"|"해결";
  place?: string; contact?: string; category?: string;
}>): {ok: boolean}

function update_item_status(id: string, status: "보관중"|"분실됨"|"해결"): {ok:boolean}
function delete_item(id: string): {ok:boolean}
function add_comment(itemId: string, text: string): {id:string}
function list_user_items(userId: string): {items: Array<{id:string; title:string; status:string; createdAt:string}>}
function upload_image(fileB64: string): {url: string, width:number, height:number}
```

### 4.3 급식 & 이미지 생성

```ts
function get_meals(input: {date?: string; from?: string; to?: string}): {
  date: string; menu: Array<{name:string; allergens?: number[]}>; calories?: number; nutrition?: Record<string,string>
}

function generate_meal_tray_image(menu: {
  date: string; items: Array<{name:string; slot:"rice"|"soup"|"main"|"side"|"dessert"; allergens?: number[]}>;
  style?: "photoreal"|"illustration"; notes?: string
}): {imageUrl: string}

function parse_allergen_codes(raw: string): Array<{name:string; allergens:number[]}> // NEIS 문자열 → 구조화
```

### 4.4 학교 지식(RAG) & 시간표

```ts
function kb_search(q: string, k?: number): Array<{chunk:string; source:string; page?:number; updatedAt?:string}>
function kb_get(section: string): {text:string; source:string; updatedAt?:string}
function get_timetable(date: string): {classes: Array<{period:number; subject:string; room:string; teacher?:string}>}
function get_timetable_changes(date: string): {changes: Array<{class:string; period:number; change:string; note?:string}>}
```

### 4.5 계정/권한

```ts
function get_profile(): {id:string; nickname:string; role:"student"|"admin"}
function update_profile(patch: Partial<{nickname:string; contact:string}>): {ok:boolean}
function ensure_admin(): {ok:boolean} // 실패 시 에러 throw
```

### 4.6 모더레이션/품질

```ts
function moderate_text(text: string): {ok:boolean; reason?:string}
function moderate_image(url: string): {ok:boolean; reason?:string}
function image_quality(url: string): {score:number; tips?:string[]}
```

---

## 5) 데이터 모델(DB)

### 5.1 테이블

* `users(id, nickname, email, role, created_at)`
* `lost_items(id, title, description, status, place, category, contact_encrypted, reporter_id, created_at, updated_at)`
* `lost_images(id, item_id, url, w, h)`
* `lost_comments(id, item_id, author_id, text, created_at)`
* `audit_logs(id, actor_id, action, target_type, target_id, payload_json, created_at)`
* `meals_cache(date, json, created_at)`
* `kb_sources(id, name, type, url, hash, updated_at)`

### 5.2 인덱싱/검색

* `lost_items(title, description, category)` 풀텍스트 인덱스(KR 형태소 추천).
* 상태/최신순 정렬 컬럼별 인덱스 추가.

### 5.3 개인정보 처리

* 연락처는 **암호화 저장** 후 뷰 계층에서 마스킹.
* 로그에 PII 금지.

---

## 6) RBAC(권한)

| 액션            |   학생(기본) |   관리자 |
| ------------- | -------: | ----: |
| 분실물 등록/조회/검색  |        ✅ |     ✅ |
| 본인 글 수정/삭제    |        ✅ | ✅(모두) |
| 상태 변경         |  ✅(본인 글) | ✅(모두) |
| 댓글 작성/삭제      | ✅(본인 댓글) | ✅(모두) |
| 욕설/개인정보 노출 삭제 |        ❌ |     ✅ |
| 사용자 차단        |        ❌ |     ✅ |

---

## 7) 급식 파이프라인(NEIS) & 이미지 생성

1. **쿼리 빌드**: 날짜·학교코드(시도교육청코드 + 표준학교코드), Type=json.
2. **정규화**: `메뉴명[알레르기번호]` → 구조화(`parse_allergen_codes`).
3. **캐시**: `meals_cache`에 저장(당일·익일 프리페치).
4. **UI**: 텍스트 카드 + 알레르기 배지(1\~19).
5. **이미지 생성**: 식판 슬롯 매핑(밥/국/메인/반찬/후식). 동적 캡션(예: "2025‑08‑22 PGHS 점심").
6. **안전**: 모델 출력에 과장/허위 방지(텍스트 원문·출처 병기).

알레르기 번호(요약): 1 난류, 2 우유, 3 메밀, 4 땅콩, 5 대두, 6 밀, 7 고등어, 8 게, 9 새우, 10 돼지고기, 11 복숭아, 12 토마토, 13 아황산류, 14 호두, 15 닭고기, 16 쇠고기, 17 오징어, 18 조개류, 19 잣.

---

## 8) 학교 지식(KB/RAG) 구축

* **수집**: 생활규정 PDF, 캠퍼스 맵, 교무실·교실 안내, 학사일정/시간표 변동 공지.
* **정제**: OCR→클린징(페이지·항목 헤더 보존), 민감정보 제거.
* **임베딩**: 문단 단위(300\~800자) + 메타(문서명/개정일/페이지).
* **검색**: top‑k(5) + 재랭킹.
* **답변**: 출처 카드를 항상 함께 노출.
* **예시 질의**: "체육복 허용 요일?", "과학실 몇 층?", "국어과 교무실 어디?", "오늘 1학년 시간표 변경?".

---

## 9) 프롬프트 설계(핵심 가드 포함)

### 9.1 오케스트레이터 System Prompt(발췌)

* 당신은 Sphere‑PGHS의 **라우터**입니다.
* 사용자 의도를 아래 집합에서 선택하고, **가능하면 도구 호출**로 해결하세요.
* 학교 관련 정보가 확실하지 않으면 `KB` 먼저 조회 후 답하세요.
* 미성년자 서비스이므로 **개인정보·욕설**을 엄격히 제한합니다.
* 출력 포맷:

```json
{"intent":"<INTENT>", "reason":"<짧게>", "tool_call": {"name":"<tool>", "args":{...}}}
```

### 9.2 분실물 에이전트 Developer Prompt(발췌)

* 제목은 20\~40자 권장, **핵심 특징**(색상/브랜드/특징) 자동 제안.
* 이미지 품질이 낮으면 업로드 직후 `image_quality`를 호출해 개선 팁을 보여주세요.
* 댓글 내 연락처는 자동 마스킹합니다.
* 관리자만 타인 글 삭제/상태 강제 변경 가능합니다.

### 9.3 급식 에이전트 Developer Prompt(발췌)

* `get_meals` 결과를 그대로 요약하지 말고 **메뉴 분류** 후 보기 좋게 정리.
* 알레르기 배지(숫자→한글명)와 **원문 출처** 링크를 함께 표시.
* 이미지 생성 시 **없는 메뉴를 창작하지 말 것**. 원문 JSON만 시각화.

### 9.4 KB 에이전트 Developer Prompt(발췌)

* 답변마다 `source`(문서명/개정일/페이지)를 UI에 명시.
* 위치 질의는 **층/동/방향**까지 구체.

---

## 10) 오류 처리 & 회복

* 툴 호출 실패: 즉시 재시도(지수 백오프)→대체 경로(캐시/최근 조회)→사과+가이드.
* 권한 오류: 이유와 함께 로그인/권한 요청 흐름 제시.
* RAG 무매칭: 유사 항목·연관 문서 제시.
* 이미지 생성 실패: 텍스트 카드만 우선 표시, 이미지 재생성 버튼 제공.

---

## 11) UX 지침(브랜드/컴포넌트)

* **메인 컬러**: 오렌지(#FF7A00) + 화이트, 회색 보조.
* **카드**: 큰 썸네일 왼쪽, 오른쪽에 제목/상태 배지/등록일. 모바일 1열, 태블릿 2열, 데스크톱 3열.
* **정렬/필터**: 상단 고정 바(최신순·상태, 검색창).
* **접근성**: 버튼 최소 44px, 색 대비 WCAG AA.
* **알림**: 작업 성공/실패 토스트. 파괴적 액션(삭제)은 모달 확인.

---

## 12) 대화 플로우(샘플)

**A) 분실물 등록**

1. 사용자: "검은색 나이키 지갑 분실 등록해줘. 사진도 올릴게."
2. Orchestrator→`LOST.CREATE` → 분실물 에이전트 `create_item` 호출.
3. 에이전트: 품질검사→요약 태그 자동 생성→카드 생성.

**B) 급식 이미지**

1. 사용자: "내일 급식 사진으로 보여줘"
2. Meals: `get_meals({date:내일})`→`generate_meal_tray_image`→ 텍스트+이미지 카드.

**C) 학교 위치**

1. 사용자: "과학실 어디야?"
2. KB: `kb_search`→ 층/동/호수 안내 + 지도 카드.

---

## 13) 테스트 전략

* **단위**: 툴 스키마 검증, 파서(알레르기), RBAC 가드.
* **통합**: 의도→툴 호출 경로(시나리오), 실패 재시도/백오프.
* **회귀**: NEIS 스키마 변경 감지 테스트(주 1회).
* **프롬프트 평가**: synthetic 발화 300문장 세트(오탑/줄임말 포함)로 정밀도/재현율 체크.

---

## 14) 배포·운영 체크리스트

* 환경변수: `NEIS_API_KEY`, `PGHS_ATPT_CODE`, `PGHS_SCHUL_CODE`, `DB_URL`, `STORAGE_BUCKET`, `EMBEDDING_MODEL`, `IMAGE_MODEL` 등.
* 캐시 TTL: 급식 24h, KB 12h, 검색 5m.
* 레이트리밋: 사용자 60 req/min, 이미지생성 3 req/min.
* 감사로그: 관리자 액션 필수 기록.
* 백업: DB 일 1회, 이미지 스토리지 주 1회.

---

## 15) 예시 API 계약(OpenAPI 스타일 발췌)

```yaml
GET /api/lost?status=보관중&q=필통&page=1&size=20
200: { total: 13, items: [{id, title, thumb, status, createdAt}] }

POST /api/lost
body: {title, description, images[], status}
201: {id}

GET /api/meals?date=2025-08-22
200: {date, menu:[{name, allergens[]}], calories, nutrition}
```

---

## 16) 보안·윤리

* 미성년자 대상 서비스: 개인정보 최소 수집, 연락처 마스킹, 위치정보 공유 금지.
* 이미지·텍스트 모더레이션 필수 패스 후 공개.
* RAG 답변은 **출처 표시**로 허위 방지.

---

## 17) To‑Do(초기 스프린트)

1. NEIS 키 발급 및 학교코드 환경변수 세팅.
2. DB 스키마 마이그레이션 + 업로드 파이프라인.
3. 오케스트레이터 의도 분류기 v1(룰+소프트맥스) 탑재.
4. 급식 파서/이미지 생성 템플릿 확정.
5. KB 초기 크롤/임베딩(생활규정·교무실/교실 배치도).
6. UI 카드 리스트 + 내비 에이전트 연결.
7. 모더레이션 가드라인 적용.

---

## 18) 부록 A — 알레르기 배지 매핑 코드 스니펫(의사코드)

```python
ALLERGEN = {1:"난류",2:"우유",3:"메밀",4:"땅콩",5:"대두",6:"밀",7:"고등어",8:"게",9:"새우",10:"돼지고기",11:"복숭아",12:"토마토",13:"아황산류",14:"호두",15:"닭고기",16:"쇠고기",17:"오징어",18:"조개류",19:"잣"}

def parse(raw: str):
    items = []
    for token in raw.split("<br/>"):
        # 예: "닭갈비(5.6.15.16.)"
        name, codes = token.split("(") if "(" in token else (token, "")
        nums = [int(x) for x in codes.replace(")","" ).split(".") if x.isdigit()]
        items.append({"name":name.strip(), "allergens":nums})
    return items
```

---

## 19) 부록 B — UI 상태어휘(샘플)

* 정렬: 최신순/상태순.
* 상태 배지: 보관중/분실됨/해결.
* 필터: 상태, 키워드.
* 접근 키: `/` 검색, `g l` 분실물, `g m` 급식.

---

본 문서는 개발자가 **바이브 코딩**으로 즉시 구현을 시작할 수 있도록, 역할/도구/데이터/정책을 최대한 구체화했습니다. 필요 시 본 문서에 **툴 스키마/프롬프트**를 그대로 복사해 사용하세요.