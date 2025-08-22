# Sphere-PGHS — 프로젝트 설계 & Agents.md (v1)

> 코드 크래프터 연말 발표회용 통합 웹앱: **분실물 게시판 + 급식(텍스트/AI 이미지) + 총괄 AI 에이전트**

---

## 0) TL;DR (한눈에 보기)
- **핵심 목표:** 학생의 터치 최소화. 에이전트가 “말과 클릭”만으로 페이지 이동·검색·수정·알림까지 수행.
- **기술 스택(제안):**
  - FE: **React + Vite + TypeScript + Tailwind** (모바일 퍼스트, PWA 옵션)
  - BE: **FastAPI + SQLAlchemy + PostgreSQL** (Cloudtype 배포 친화)
  - Auth: **JWT + (선택) 학교 SSO/구글 OAuth**
  - 파일: **Object Storage(S3 호환)** 또는 Cloudtype 제공 스토리지
  - 검색: **PostgreSQL FTS**(한국어 형태소 보완으로 trigram/tsvector 혼용)
  - 에이전트: **ReAct + Tool-Calling**(FastAPI function schema 노출) + **RAG**(학교 규정/교실 위치 등)
  - 이미지 생성: **메뉴→프롬프트 변환→이미지 생성 API**(모델 교체 가능 구조)
- **보안:** 업로드 파일 검사, 권한 계층(RBAC), 감사 로그, 개인정보 최소 수집, 학교 규정 준수.

---

## 1) 기능 범위 & 사용자 스토리
### 1.1 사용자 유형
- **게스트**: 읽기, 검색은 가능 (학교 정책에 따라 글 열람 범위 제한 가능)
- **학생/교사(로그인)**: 글 등록/수정(본인), 댓글, 연락처 공유(Opt-in), “내가 등록한 글” 보기
- **관리자**(담당 교사/자치회 임원): 전체 글 수정·삭제, 상태 변경, 신고 처리, 공지 고정

### 1.2 주요 유즈케이스
- **분실물**: 사진＋제목＋설명＋상태(분실됨/보관중) 등록 → 목록 카드뷰 → 상세 → 댓글/연락처로 연결 → 상태 변경 → 종료
- **급식**: NEIS(나이스) 급식 API → 일/주간 텍스트 표시 → **AI 급식판 이미지 생성**(“오늘 급식 미리보기”)
- **AI 에이전트**: “체육관 가는 길 알려줘”, “3층 2반 어디야?”, “내 분실물 글 보여줘”, “오늘 급식 이미지 보여줘”, “학생생활규정 벌점 기준 요약해줘” 등 **대화로 모든 액션** 실행.

---

## 2) 시스템 아키텍처(개요)
```
[React(PWA) + Tailwind]  ←→  [FastAPI(ASGI)]  ←→  [PostgreSQL]
        │                           │
        │(file upload)              ├─[Object Storage(S3 호환)]  ← 원본 이미지
        │                           ├─[RAG Vector Store]        ← 학교 규정/지도/교무실
        │                           └─[AI Providers]            ← 이미지 생성/LLM
```
- **PWA**로 오프라인 캐시(목록/정적 자원), 알림(Firebase Cloud Messaging 가능) 지원.
- **RAG**를 위한 메타데이터: 문서 출처(규정 PDF/학교 안내문), 교실 좌표, 층 정보, 교무실 위치.

---

## 3) 데이터 모델 (초안)
> SQLAlchemy 기준, 실제 마이그레이션은 Alembic 사용 권장

### 3.1 Users
- `id (PK)`, `role (enum: guest/student/teacher/admin)`, `email`, `display_name`, `phone (nullable)`, `password_hash (nullable if OAuth)`, `created_at`.

### 3.2 LostItem(분실물)
- `id (PK)`, `title`, `description`, `status (enum: LOST, KEEPING, RESOLVED)`, `owner_id (FK Users)`, `created_at`, `updated_at`.

### 3.3 LostItemImage
- `id (PK)`, `lost_item_id (FK)`, `url`, `width`, `height`, `uploaded_by (FK Users)`.

### 3.4 Comment
- `id (PK)`, `lost_item_id (FK)`, `author_id (FK Users)`, `content`, `created_at`.

### 3.5 ContactBridge(연락교환 요청)
- `id (PK)`, `lost_item_id (FK)`, `finder_id (FK Users)`, `owner_id (FK Users)`, `message`, `status(enum: OPEN, CONNECTED, CLOSED)`, `created_at`.

### 3.6 AuditLog
- `id`, `actor_id`, `action`, `target_type`, `target_id`, `ip`, `ua`, `created_at`.

### 3.7 Meal
- `id`, `date`, `raw_text`, `calorie (nullable)`, `allergens (nullable)`, `source(meta)`.

### 3.8 MealImageGen
- `id`, `date`, `prompt`, `image_url`, `model_name`, `status(enum: PENDING, DONE, FAIL)`, `created_at`.

### 3.9 NavigationMap(교실/교무실 정보)
- `id`, `type(enum: CLASSROOM, OFFICE, FACILITY)`, `name`, `floor`, `building`, `coords(json)`, `notes`.

---

## 4) API 스펙 (요약)
### 4.1 Auth
- `POST /api/auth/signup` — 학생/교사 가입(정책상 초대코드/교내메일 제한 가능)
- `POST /api/auth/login` — JWT 발급
- `GET  /api/auth/me` — 내 정보

### 4.2 Lost & Found
- `POST /api/lost` — 분실물 등록(제목/설명/상태)
- `POST /api/lost/{id}/images` — 이미지 업로드(멀티파트)
- `GET  /api/lost` — 목록(페이지네이션, `q`, `status`, `sort=latest|status`)
- `GET  /api/lost/{id}` — 상세
- `PATCH /api/lost/{id}` — 작성자 또는 관리자 수정
- `DELETE /api/lost/{id}` — 관리자/작성자(정책)
- `POST /api/lost/{id}/comments`
- `GET  /api/lost/{id}/comments`
- `POST /api/lost/{id}/status` — 상태 변경(관리자 우선)
- `GET  /api/lost/mine` — 내가 등록한 글

### 4.3 Meals
- `GET  /api/meals?date=YYYY-MM-DD` — 텍스트 급식
- `POST /api/meals/{date}/image` — 이미지 생성 트리거(관리자/스케줄러)
- `GET  /api/meals/{date}/image` — 생성 결과 조회

### 4.4 Map/Rules
- `GET  /api/map/search?q=교무실/교실명`
- `GET  /api/rules?q=벌점/지각` — 규정 RAG 답변(출처 포함)

### 4.5 Agent Tools (서버 함수)
- `POST /api/agent/invoke` — 에이전트 오케스트레이터 엔드포인트
- (내부) 툴: `navigate(page)`, `lost.search`, `lost.update`, `meals.get`, `meals.genImage`, `user.update`, `map.find`, `rules.ask`, `notify.push`

---

## 5) 프론트엔드 라우팅 & UI (Daangn 스타일)
- `/` 홈: 상단 탭(분실물｜급식｜도움말) + **에이전트 플로팅 버튼**(음성/텍스트)
- `/lost` 카드 목록: 큰 썸네일 + 짧은 제목/상태 뱃지, 무한 스크롤
- `/lost/new` 등록 폼: 모바일 1열, 이미지 드래그&드롭/카메라
- `/lost/:id` 상세: 큰 이미지 캐러셀, 설명, 댓글, 연락 버튼
- `/meals` 캘린더 탭: 오늘/주간 텍스트 + “이미지 보기” 토글
- `/map` 간단 검색: “2층 1반”, “수학과 교무실” → 결과 핀/텍스트
- 공통: **오렌지(#FF7800)+화이트** 베이스, 라운디드 카드, 상단 고정 검색바

### 컴포넌트 가이드
- Card/LargeImageCard, Badge(status), BottomSheet(Action), FloatingAgentButton, Toast/Confirm, EmptyState

---

## 6) 검색 & 정렬
- PostgreSQL `tsvector`(한국어: ngram 기반) + `pg_trgm` 인덱스
- 필드 가중치: `title^3 + description^1`
- 상태/최신 정렬 조합, **쿼리 캐시**(10~30초)

---

## 7) 보안·개인정보·운영 정책
- **이미지 스캔**(확장자/EXIF/간단한 유해성 필터), **용량 제한**(예: 5~10MB)
- **RBAC**: 관리자만 일괄 삭제/상태 변경, 일반 사용자는 본인 글만 수정/삭제
- **연락처 공유 Opt-in**: 연락 교환은 양자 동의 후 메시지 브리지에서만 노출
- **감사 로그**: 삭제/상태 변경/권한 행위 전부 기록
- **속도 제한**: 글 등록/댓글 스팸 방지
- **신고 기능**: 부적절한 사진/글 신고 → 관리자 큐
- **법적/학교 규정 준수**: 학생 사진 처리 시 동의 정책 명시

---

## 8) 급식 파이프라인 (텍스트→이미지)
1) **데이터 수집**: NEIS 급식 API로 날짜별 메뉴/알레르기 수집
2) **정제**: 메뉴 텍스트 정규화(이모지/괄호 제거), 카테고리 묶기(국/반찬/디저트)
3) **프롬프트 생성**: 예) `"한국 고등학교 급식판, 스테인리스 식판 5칸, 밥(흰쌀밥), 김치, 미역국, 불고기, 멸치볶음, 포도. 촬영 각도: 45도. 학교 급식 느낌, 과장되지 않은 현실적인 조명."`
4) **이미지 생성**: 외부 API 호출(모델·해상도는 환경변수로 분리)
5) **검증/캐싱**: 생성 실패 시 텍스트만 노출, 성공 시 CDN 캐시

---

## 9) 총괄 AI 에이전트 설계 (Agents.md)
### 9.1 오케스트레이터 개요
- **패턴**: ReAct(Reason+Act) + Tool-Calling
- **목표**: 대화 의도→도구 호출→검증→UI 반응(네비게이션/토스트/모달)

### 9.2 시스템 프롬프트(요약)
```
역할: Sphere-PGHS 웹의 음성/채팅 에이전트. 학생의 터치를 최소화한다.
원칙:
- 사실 우선, 출처 제시(규정/지도)
- 위험 행위, 개인정보 노출 금지
- 실패 시 솔직한 사과와 대안 제시
행동 지침:
- 페이지 이동은 navigate(page) 도구 사용
- 분실물 검색/수정은 lost.* 도구
- 급식 텍스트/이미지는 meals.* 도구
- 규정/지도/교무실은 rules.ask, map.find 도구
- 사용자 의도 모호 → 1문장 재확인 후 기본값 실행
응답 스타일:
- 한국어, 간결한 문장 + 즉시 실행 버튼/딥링크 제시
```

### 9.3 툴 스키마(예시)
```json
{
  "navigate": {
    "description": "앱 내 특정 페이지로 이동",
    "params": {"page": "home|lost|lost_new|meals|map|profile|admin"}
  },
  "lost.search": {
    "description": "분실물 검색",
    "params": {"q": "string", "status": "LOST|KEEPING|RESOLVED", "sort": "latest|status"}
  },
  "lost.update": {
    "description": "분실물 상태/내용 업데이트",
    "params": {"id": "number", "patch": "object"}
  },
  "meals.get": {
    "description": "특정 날짜 급식 가져오기",
    "params": {"date": "YYYY-MM-DD"}
  },
  "meals.genImage": {
    "description": "급식 이미지 생성 트리거",
    "params": {"date": "YYYY-MM-DD"}
  },
  "user.update": {
    "description": "회원 정보 수정",
    "params": {"fields": "object"}
  },
  "map.find": {
    "description": "교실/교무실 위치 검색",
    "params": {"q": "string"}
  },
  "rules.ask": {
    "description": "학생생활규정 질의응답(RAG)",
    "params": {"q": "string"}
  },
  "notify.push": {
    "description": "푸시/알림 트리거",
    "params": {"user_id": "number", "title": "string", "body": "string"}
  }
}
```

### 9.4 예시 대화 플로우
- 사용자: “내가 올린 글 보여줘” → `lost.search({owner=me})` → 결과 카드 3개 + “상세 열기” 버튼
- 사용자: “2층 1반 어디야?” → `map.find({q:"2층 1반"})` → 층/건물/좌표 출력 + “지도로 보기” 버튼
- 사용자: “오늘 급식 사진 보여줘” → `meals.get` → 없으면 `meals.genImage` 트리거 후 텍스트 우선 표시

### 9.5 안전장치
- **개인연락처 자동 차단**(채팅 내 노출 금지, ContactBridge로만 교환)
- **삭제/상태변경 전 재확인**(confirm) + 감사로그 기록
- **규정 답변 시 출처 스니펫 제공**(문장+문서명+절 번호)

### 9.6 평가(오프라인 테스트 시나리오)
- 20개 대표 시나리오(네비게이션/검색/수정/규정/RAG/실패복구) **성공률 ≥ 95%**
- 라운드트립 시간(요청→UI 반응) 목표: 체감 1.5초 이내(네트워크 상황 제외)

---

## 10) RAG 데이터 구축
- **소스**: 학생생활규정, 교무실/교실 배치도, 행사 안내문, 자주 묻는 질문(FAQ)
- **전처리**: PDF→텍스트, 문단/조항 단위 chunk(512~1024 tokens), 메타데이터(조항번호/페이지)
- **인덱스**: cosine-sim + rerank, 최신본 스냅샷 버전 태깅
- **UI**: 답변 하단에 “출처 펼치기” 버튼으로 근거 2~3개 노출

---

## 11) 배포/운영
- **환경변수**: `DATABASE_URL`, `STORAGE_BUCKET`, `JWT_SECRET`, `MEAL_API_KEY`, `IMG_API_KEY` 등
- **CI/CD**: GitHub Actions → Cloudtype 자동 배포, 마이그레이션 단계 포함
- **모니터링**: Sentry(프론트/백), 헬스체크 `/healthz`
- **백업**: DB 일일 스냅샷, 오브젝트 스토리지 수명주기(예: 180일 뒤 아카이브)

---

## 12) 성능 & 접근성
- 이미지 **자동 리사이즈/웹프**(서버/에지) + LQIP
- 리스트 **IntersectionObserver**로 무한 스크롤, 요청 병합
- **a11y**: 키보드 포커스, 색 대비(오렌지 대비 확보), 스크린리더 라벨

---

## 13) QA 체크리스트(발표 전)
- [ ] 비로그인 열람 범위/정책 점검
- [ ] 업로드 제한/부적절 콘텐츠 신고 테스트
- [ ] 관리자 삭제/상태 변경 감사로그 확인
- [ ] 에이전트 도구별 실패 케이스(네트워크/권한) 복구 메시지
- [ ] 급식 이미지 생성 실패 시 우아한 폴백
- [ ] 모바일 Safari/Chrome, 저대역폭 테스트

---

## 14) 구현 스니펫(요약)
### 14.1 SQLAlchemy 모델(발췌)
```python
class LostItem(Base):
    __tablename__ = "lost_items"
    id = Column(Integer, primary_key=True)
    title = Column(String(120), index=True, nullable=False)
    description = Column(Text)
    status = Column(Enum("LOST","KEEPING","RESOLVED", name="lost_status"), default="LOST")
    owner_id = Column(ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

### 14.2 FastAPI Router(발췌)
```python
@router.get("/lost")
async def list_lost(q: str = "", status: str | None = None, sort: str = "latest", page: int = 1):
    # FTS + 정렬 조합, 페이지네이션
    ...
```

### 14.3 에이전트 툴 선언(발췌)
```python
Tool(
  name="lost.search",
  description="분실물 검색",
  args_schema=LostSearchArgs,
  func=lost_search_handler,
)
```

---

## 15) 마일스톤(권장 순서)
1) 스캐폴딩(라우팅/디자인 토큰/인증) → 2) 분실물 CRUD + 업로드 → 3) 검색/정렬 → 4) 급식 텍스트 → 5) 에이전트 MVP(네비/검색) → 6) 규정 RAG → 7) 급식 이미지 생성 → 8) 관리자/감사로그 → 9) PWA/알림 → 10) QA/발표 데모 시나리오

---

## 16) 데모 시나리오(발표용)
- **시작**: 홈에서 “에이전트 버튼” 터치 없이 음성: “오늘 급식 보여줘” → 텍스트/이미지
- **분실물**: “어제 올린 회색 후드티 찾아줘” → 카드 1~2개 → “상태를 보관중으로 바꿔줘”
- **내비게이션**: “수학과 교무실로 이동” → `/map` 결과 표시 → “즐겨찾기 등록”
- **규정**: “모자 착용 규정 요약” → 2문장 요약 + 출처 버튼

---

### 부록 A) UI 톤앤매너
- 배경 화이트, 포인트 오렌지(#FF7800), 액션 버튼은 솔리드/둥근 모서리
- 카드의 썸네일 비율 4:3, 제목 1줄 ellipsis, 상태 뱃지 색상: LOST=red, KEEPING=blue, RESOLVED=gray

### 부록 B) 용어 규칙
- “분실됨/보관중/종결” 통일, 연락처는 “연락 교환”으로 표기

### 부록 C) 발표 체크(문구)
- “Sphere-PGHS는 **에이전트-우선** UX로, 학생의 터치 없이 **말로 하는 웹**을 지향합니다.”

