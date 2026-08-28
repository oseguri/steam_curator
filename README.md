# Steam Game Curator — RAG + Function Calling 기반 게임 큐레이션 에이전트

> LS_MINI_3 (Steam 인기 판매 데이터 파이프라인)의 **4차 확장 프로젝트**
> 정형 데이터 파이프라인 위에 **비정형 텍스트 레이어 + LLM 오케스트레이션**을 얹는다.

---

## 0. 현재 구현 상태 (2026-08-28)

이 문서의 2~8장은 **목표 설계**이고, 아래가 지금 실제로 있는 것이다.

**구현 완료**

- `src/collect/**` — 수집 파이프라인 전체 (crawl_list → fetch_details → standardize → fetch_reviews)
  · `main.py`로 한 번에 실행한다(10장 참고). 아직 실제 수집은 돌리지 않았다.
- `model.py` — 단계 사이에 주고받는 데이터 인터페이스 (`Game`, `ReviewChunk`, `ReviewMatch`, `GameVibeScore`)
  · 장르·플레이방식·정렬 어휘(enum)도 여기 한 곳에서만 정의한다.
- `src/agent/tools/_common.py`, `_template.py` — 툴 작성용 공용 유틸과 예시

**작성 예정** (담당은 9장 참고)

- `src/agent/tools/*.py` — 툴 5개 (팀원 2명이 3개, 리드가 2개)
- `src/agent/registry.py`, `retrieval.py`, `orchestrator.py` — 툴 등록·RAG·FC 루프
- `src/index/**`, `app/streamlit_app.py`, `src/eval/**`

app_id 목록 크롤링 로직의 원본을 확인해야 하면 3차 프로젝트 저장소
[`github.com/oseguri/LS_MINI_3`](https://github.com/oseguri/LS_MINI_3)를 참고한다.

---

## 1. 문제 정의

3차 프로젝트에서 우리는 Steam 인기 판매 게임 498건의 **정형 데이터**(가격, 할인율, 평가점수, 장르, 언어)를
수집·검증·적재하고 대시보드로 분석했다. 그 결과 알게 된 것:

- 순위를 가르는 건 가격이 아니라 **무료 여부와 평가 수**였다.
- 하지만 "이 게임이 **어떤 게임인지**"는 정형 데이터로 전혀 설명되지 않았다.
  장르가 `액션, 인디`인 게임 200개는 서로 완전히 다른 게임이다.

즉 **"3만원 이하 액션 게임"은 SQL로 찾을 수 있지만,
"친구랑 둘이 낄낄대며 할 만한 협동 게임"은 SQL로 찾을 수 없다.**

이 프로젝트는 그 간극을 메운다.

| 질문 유형 | 예시 | 해결 수단 |
|---|---|---|
| 정형 조건 | "3만원 이하, 할인 중, 평가 8점 이상" | **Function Calling** (pandas 필터) |
| 비정형 의미 | "혼자 조용히 몰입할 수 있는 분위기" | **RAG** (게임 설명 임베딩) |
| 혼합 | "3만원 이하인데 스토리 좋은 게임" | **하이브리드** (메타데이터 필터 + 벡터 검색) |
| 근거 요약 | "이 게임 평가가 왜 갈려?" | **리뷰 RAG** (실제 리뷰 인용) |

---

## 2. 최종 산출물

**Streamlit 웹앱** — 탭 3개

1. **큐레이터 챗봇** — 자연어 질문 → LLM이 스스로 툴 선택 → 추천 + 근거
2. **게임 상세 / 리뷰 근거** — 선택한 게임의 정형 정보 + 리뷰 RAG 요약(원문 인용)
3. **데이터 대시보드** — 수집 현황, 품질 검증, 장르·가격 분포 (3차 프로젝트 계승)

부가 산출물: 툴 라우팅 정확도 리포트, 환각 차단(threshold) 검증 결과

---

## 3. 아키텍처

```
                    [1] 수집                    [2] 표준화            [3] 인덱싱
Steam 검색 페이지  ──crawl_list.py──┐
Steam appdetails API ─fetch_details.py─┼─► data/raw/ ─► standardize.py ─► data/processed/
Steam appreviews API ─fetch_reviews.py─┘                                   ├─ games.csv ──► index_games.py   ──► Chroma: steam_games
                                                                           └─ reviews.csv ─► index_reviews.py ──► Chroma: steam_reviews

                    [4] 에이전트                                    [5] UI
사용자 질문 ─► orchestrator.py
                 ├─ Gemini interactions.create(tools=TOOLS)
                 ├─ pydantic strict 인자 검증  ← 잘못된 인자는 실행 차단
                 ├─ tools.py 실행
                 │    ├ search_games_by_filter   (정형: pandas)
                 │    ├ search_games_by_vibe     (하이브리드: Chroma where + 벡터)
                 │    ├ get_game_detail          (정형)
                 │    ├ ask_about_game_reviews   (리뷰 RAG + threshold)
                 │    └ compare_games            (정형)
                 └─ function_result 반환 → 최종 답변 생성 ──► Streamlit
```

### 강의 내용 매핑

| 강의일 | 내용 | 이 프로젝트에서 |
|---|---|---|
| day1 | 프롬프트 엔지니어링 (RTF/RISEN/COSTAR) | 시스템 프롬프트, RAG 답변 프롬프트 규칙 5개 |
| 8/24 | LLM 활용 기초 | Gemini `interactions` API 래핑 |
| 8/25 | Function Calling | 툴 선언(JSON schema) + 라우팅 |
| 8/26 | FC Loop + pydantic 검증 | 2턴 루프, strict 검증으로 실행 차단 |
| 8/27 | Embedding & VectorDB | Chroma 2개 컬렉션, cosine, 메타데이터 필터 |
| 8/28 | RAG + threshold + chunking | 리뷰 청킹, 유사도 임계값, 근거 없으면 답변 거부 |

---

## 4. 데이터 수집 계획

기존 500건(인기순)만으로는 추천 다양성이 부족하다. **1,500~2,000건 규모로 재수집**한다.

### 4-1. 수집 소스

| 단계 | 엔드포인트 | 산출 |
|---|---|---|
| 목록 | `store.steampowered.com/search/results/?filter=topsellers&infinite=1` 외 장르별 필터 | app_id 목록 |
| 상세 | `store.steampowered.com/api/appdetails?appids={id}&l=korean&cc=kr` | 설명, 장르, 카테고리, 가격, 언어 |
| 리뷰 | `store.steampowered.com/appreviews/{id}?json=1&language=koreana&num_per_page=100` | 리뷰 원문 |

### 4-2. 수집 범위

- **게임**: 인기순 상위 500 + 장르별(액션/RPG/시뮬레이션/전략/인디/캐주얼) 각 200~250 → 중복 제거 후 약 1,500~2,000건
- **리뷰**: 게임당 최대 100건 (긍정/부정 각 50건 균형 수집) → 리뷰 RAG 대상은 **상위 300개 게임**으로 한정
  - 이유: 임베딩 비용. 전체 게임 리뷰를 다 임베딩하면 15만 청크가 넘는다.

### 4-3. 3차 프로젝트 원칙 계승

- **수집과 파싱 분리**: raw는 원본 JSON/문자열 그대로 저장, 타입 변환은 `standardize.py`에서만
- **재크롤링 없이 파싱 수정 가능** — 이번에도 동일
- **품질 규칙 검증**: 필수값 누락 / app_id 중복 / 할인율 범위 / 장르 미매칭 / 설명 길이 부족(신규)

### 4-4. 주의사항 (실측 기반)

- appdetails는 **1회 호출당 1개 appid**만 안정적으로 반환된다. 배치 요청 시 일부 null.
- 요청 간 **1.0~1.5초 sleep** 필수. 없으면 429 이후 IP 단위 임시 차단.
- `success: false` 응답(지역 미판매, 삭제된 앱)은 정상적인 케이스로 처리하고 별도 기록.
- `type`이 `game`이 아닌 항목(DLC, 사운드트랙, 데모)은 제외.
- 1,500건 수집 시 예상 소요: 약 40~50분. **팀원별로 app_id 구간을 나눠 병렬 수집**을 권장.

---

## 5. RAG 설계

### 5-1. 컬렉션 2개

| 컬렉션 | 문서 단위 | 임베딩 대상 텍스트 | 메타데이터 |
|---|---|---|---|
| `steam_games` | 게임 1건 | `이름. 장르. 카테고리. 짧은설명` | app_id, name, price, is_free, discount, review_score, genres, total_reviews |
| `steam_reviews` | 리뷰 청크 | 리뷰 원문 (400자 청크, 50자 오버랩) | app_id, review_id, voted_up, playtime_hours, votes_up |

- 임베딩 모델: `gemini-embedding-2`, 768차원
- 거리 함수: cosine (`similarity = 1 - distance`)

### 5-2. 하이브리드 검색

정형 조건은 **Chroma `where` 절**로, 취향은 **벡터 유사도**로 처리한다.

```python
collection.query(
    query_embeddings=[vibe_vector],
    n_results=CANDIDATE_K,
    where={'$and': [{'final_price': {'$lte': 30000}},
                    {'review_score': {'$gte': 8}}]}
)
```

이렇게 하면 "3만원 이하인데 스토리가 좋은 게임"이 한 번의 툴 호출로 처리된다.
**이것이 이 프로젝트의 핵심 데모 포인트.**

### 5-3. Threshold와 환각 방지

- `CANDIDATE_K = 8` → threshold `0.65` 통과분 중 상위 `MAX_CONTEXT_DOCS = 4`만 컨텍스트로 사용
- 통과 문서가 0개면 **생성 호출을 하지 않고** "근거 없음"을 반환한다.
- 답변 마지막에 사용한 문서 ID를 반드시 표기한다. (8/28 실습 규칙 계승)

### 5-4. 리뷰 요약 시 편향 방지

리뷰는 긍정이 훨씬 많다. 단순 Top-k를 쓰면 요약이 항상 긍정으로 기운다.
→ `ask_about_game_reviews`는 **긍정 청크와 부정 청크를 각각 검색해서 균형을 맞춘 뒤** 컨텍스트를 구성한다.

---

## 6. Function Calling 설계

| 함수 | 인자 | 용도 |
|---|---|---|
| `search_games_by_filter` | max_price, min_price, genres, is_free, min_review_score, only_discounted, sort_by, limit | 순수 정형 조건 |
| `search_games_by_vibe` | vibe_query + (선택) max_price, is_free, genres, min_review_score, limit | 하이브리드 |
| `get_game_detail` | app_id | 단일 게임 상세 |
| `ask_about_game_reviews` | app_id, question | 리뷰 RAG |
| `compare_games` | app_ids (2~4개) | 게임 비교 |

### 검증 계층 (8/26 계승)

모든 함수 인자는 **pydantic strict 모델**로 검증한다.
- `extra='forbid'` — LLM이 만들어낸 없는 인자 차단
- `Literal` enum — 존재하지 않는 장르명 차단
- `Field(ge=, le=)` — 가격 음수, limit 100 등 차단
- 검증 실패 시 **함수를 실행하지 않고** 에러를 LLM에 돌려준다.

---

## 7. Streamlit 화면

```
app/streamlit_app.py
├── Tab 1. 큐레이터 챗봇
│     - 채팅 입력 + 대화 이력
│     - 사이드바: "LLM이 호출한 툴" 실시간 표시 (툴명 / 인자 / 검증결과 / 결과건수)
│     - 추천 게임은 카드로 (헤더 이미지, 가격, 할인, 평가, 유사도)
├── Tab 2. 게임 상세 & 리뷰 근거
│     - 게임 선택 → 정형 정보 + 리뷰 RAG 요약
│     - 요약 아래 "근거 리뷰 원문" expander (플레이타임, 추천여부 함께)
└── Tab 3. 데이터 대시보드
      - 수집 현황(단계별 건수), 품질 규칙 위반 현황
      - 장르별 가격 분포, 평가점수 분포, 할인율 분포
```

**툴 호출 과정을 사이드바에 노출하는 것**이 발표에서 가장 잘 먹힌다.
"LLM이 알아서 함수를 골랐다"를 말로 하지 않고 화면으로 보여줄 수 있다.

---

## 8. 검증 계획

| 항목 | 방법 | 목표 |
|---|---|---|
| 툴 라우팅 정확도 | 질문 30개 × 정답 툴 라벨링 → 일치율 | 85% 이상 |
| 인자 검증 차단율 | 의도적 오류 케이스 10개 | 100% 차단 |
| 환각 방지 | 데이터에 없는 게임 질문 10개 | 100% "근거 없음" 응답 |
| 검색 품질 | 취향 질문 20개 → 사람이 관련성 3점 척도 채점 | 평균 2.0 이상 |
| 응답 속도 | 질문당 end-to-end | 10초 이내 |

`src/eval/routing_cases.py`에 케이스를 넣고 스크립트로 돌린다.

---

## 9. 분업 (3인, 2026-08-28 확정)

이번 주 강의 주제가 **Function Calling + RAG**다. 팀원 두 명은 그 중 강의에서 직접 배운
**"툴 하나 만들기"(선언 + pydantic 검증 + 함수 구현)** 에 집중하고, 데이터 수집·RAG 설계·
프론트엔드처럼 설계 판단이 필요한 부분은 리드가 가져간다.

### 9-1. 담당

| 담당 | 작업 | 파일 |
|---|---|---|
| **리드** | 데이터 수집 파이프라인 전체 | `src/collect/**`, `main.py` |
| **리드** | RAG 설계 + 리뷰 집계/압축 검색 | `src/agent/retrieval.py` |
| **리드** | 취향 검색·리뷰 RAG 툴 (RAG와 얽혀 있음) | `src/agent/tools/search_games_by_vibe.py`, `.../ask_about_game_reviews.py` |
| **리드** | Function Calling 루프 + 툴 등록 | `src/agent/orchestrator.py`, `src/agent/registry.py` |
| **리드** | 임베딩·인덱싱 | `src/index/**` |
| **리드** | Streamlit 3개 탭 전부 | `app/streamlit_app.py` |
| **리드** | 평가 스크립트 | `src/eval/**` |
| **팀원 B** | 정형 조건 검색 툴 1개 | `src/agent/tools/search_games_by_filter.py` |
| **팀원 C** | 게임 상세 조회 툴 1개 | `src/agent/tools/get_game_detail.py` |
| **팀원 C** | 게임 비교 툴 1개 | `src/agent/tools/compare_games.py` |

팀원 두 명의 공통 과제:
1. **강의 실습 복습** — 8/25(Function Calling), 8/26(pydantic 검증) 실습 코드를 다시 돌려본다.
2. **깃 실습** — `CONTRIBUTING.md`대로 브랜치 → 커밋 → PR → 머지를 1회 완주한다.
3. **담당 툴 파일 구현** — 아래 9-2 규칙을 지켜서 자기 파일만 채운다.

### 9-2. 코드가 겹치지 않게 하는 규칙

여러 명이 같은 파일을 고치면 매번 충돌(conflict)이 난다. 그래서 **툴 1개 = 파일 1개 = 담당자 1명**으로 쪼갰다.

```
src/agent/
├── retrieval.py                    [리드]
├── orchestrator.py                 [리드]
├── registry.py                     [리드]  ← 툴을 모아 TOOLS/FUNCTION_MAP을 만든다
└── tools/
    ├── _common.py                  [리드]  ← 공용 데이터 로딩. 고치지 말고 가져다 쓴다
    ├── _template.py                [리드]  ← 작성 예시. 복사해서 참고만 한다
    ├── search_games_by_filter.py   [팀원 B]
    ├── get_game_detail.py          [팀원 C]
    ├── compare_games.py            [팀원 C]
    ├── search_games_by_vibe.py     [리드]
    └── ask_about_game_reviews.py   [리드]
```

- **자기 이름이 붙은 파일만 고친다.** 남의 파일은 열어서 읽는 건 자유지만 수정·정리·포맷팅 금지.
- **공용 파일(`config.py`, `model.py`, `_common.py`, `registry.py`)은 리드만 고친다.**
  상수를 추가하고 싶거나 공용 함수가 필요하면 직접 넣지 말고 리드에게 요청한다.
  (모두가 `config.py`에 한 줄씩 추가하는 게 충돌 1순위 원인이다.)
- **툴 파일 하나에는 3개가 모두 들어간다** — `ARGUMENTS`(pydantic 모델), `DECLARATION`(JSON 선언),
  `run()`(실행 함수). 이름을 이렇게 고정해야 `registry.py`가 자동으로 등록한다.
  선언은 A파일, 검증은 B파일처럼 흩어두면 툴 하나 만들 때마다 파일 3개가 충돌한다.
- **브랜치도 파일 단위로 딴다** — `tools/search-games-by-filter` 처럼.
- 자기 툴은 파일 맨 아래 `if __name__ == '__main__':`로 직접 실행해 눈으로 확인하고 커밋한다.
  (`uv run python -m src.agent.tools.get_game_detail`)

### 9-3. 진행 순서

① 리드가 수집을 끝내 `games.csv`를 올려둔다(팀원 툴은 이 파일이 있어야 돌아간다) →
② 팀원 B·C가 각자 툴 파일 구현 + PR → ③ 리드가 `registry.py`에 등록하고 RAG·오케스트레이터 연결 →
④ 리드가 Streamlit·평가 마무리.

팀원 툴은 서로 의존이 없으므로 B와 C는 순서 상관없이 동시에 진행하면 된다.

---

## 10. 실행 방법

```bash
cp .env.example .env      # 지금 단계(수집)는 비어 있어도 동작함
uv sync
```

`uv sync`로 만든 가상환경은 `uv run`을 붙여야 쓰인다. 그냥 `python ...`으로 실행하면
전역 Python이 잡혀서 `ModuleNotFoundError`가 난다(자세한 건 `CONTRIBUTING.md`의 "실행할 때
가상환경이 안 잡힘" 참고).

```bash
# 데이터 수집 전체 파이프라인 (crawl_list -> fetch_details -> standardize -> fetch_reviews -> standardize)
uv run python main.py

# 특정 단계만 건너뛰고 싶을 때
uv run python main.py --skip-crawl              # app_ids.csv가 이미 있을 때
uv run python main.py --skip-crawl --skip-details --skip-reviews   # games.csv/reviews.csv 표준화만 다시

# 개별 단계를 직접 돌리고 싶을 때
uv run python -m src.collect.crawl_list
uv run python -m src.collect.fetch_details
uv run python -m src.collect.fetch_reviews
uv run python -m src.collect.standardize

# 인덱싱 ~ 앱 실행 — 재작성 예정 (아래는 목표 설계)
# uv run python -m src.index.index_games
# uv run python -m src.index.index_reviews
# uv run python -m src.agent.orchestrator
# uv run streamlit run app/streamlit_app.py
```

---

## 11. 발표 시 강조할 것

1. **정형/비정형을 LLM이 스스로 나눠 처리한다** — 툴 라우팅 로그를 화면에 띄워 보여준다.
2. **하이브리드 검색** — `where` 절 + 벡터 검색을 한 번에. SQL만으로도, 벡터만으로도 안 되는 질문.
3. **환각을 데이터로 막았다** — threshold 미달 시 생성 자체를 안 한다. 실패 케이스를 당당하게 보여준다.
4. **3차 프로젝트의 원칙을 그대로 이어받았다** — raw/표준화 분리, 품질 규칙, 실패 사례 기록.

---

## 부록. 스캐폴드 제거 기록 (2026-08-28)

한 차례 전체 스캐폴드(수집 후반부·표준화·인덱싱·에이전트·평가)를 작성해 아래를 확인했었다.

| 항목 | 결과 |
|---|---|
| 전 파이썬 파일 구문 검사 | 통과 |
| 인자 검증 차단율 (오류 케이스 10개) | 10/10 차단 |
| 정상 인자 통과 | 3/3 통과 |
| 툴 선언 enum ↔ pydantic Literal 일치 | 일치 |
| `TOOLS` / `FUNCTION_MAP` / `ARGUMENT_MODELS` 키 정합성 | 일치 |
| `standardize.py` (DLC 제외, 중복 감지, 장르 미매칭, 가격 100 나누기, 리뷰 청킹) | 정상 |
| function_result JSON 직렬화 | 통과 (numpy 타입 제거 처리 완료) |

이후 처음부터 직접 구현하기로 하면서 `crawl_list.py` / `http_client.py`만 남기고 나머지는 삭제했다
(git 커밋 이력 없이 삭제해 코드 자체는 복구 불가 — 필요하면 이 README의 설계(2~9장)를 참고해 재작성한다).

**재작성 시 실측 기반으로 미리 확인할 것 — 이전 스캐폴드 작업 중 발견한 함정**

1. **Steam 검색 페이지의 장르 필터 파라미터**(`config.GENRE_FILTERS`의 태그 ID).
   Steam이 파라미터를 바꾸는 일이 있으므로, 첫 실행에서 장르별 수집 결과가
   인기순과 거의 같다면 태그 ID가 안 먹은 것이다. 브라우저에서 장르 페이지를 열고
   URL의 `tags=` 값을 확인해 교체할 것.
2. **`appdetails`는 1회 호출당 appid 1개만 안정적으로 반환한다.** 배치 요청 시 일부 null이 온다.
3. **`price_overview`는 100배 정수다.** 원화는 `2750000` → `27,500원`으로 나눠야 한다.
   첫 표준화 결과에서 가격 자릿수를 눈으로 확인할 것.
   (3차 프로젝트에서 "정규식 오타로 모든 가격이 0"이 나왔던 것과 같은 자리다.)
4. **개별 리뷰에는 별점이 없다.** `voted_up` 추천/비추천 2단계뿐이고,
   `review_score`(1~9) 게임 단위 집계값은 `appreviews`의 `query_summary`로만 얻을 수 있다.
5. **요청 간 1초 이상 대기 필수.** 없으면 429 이후 IP 단위로 잠시 막힌다.
6. **`type`이 `game`이 아닌 것(DLC·사운드트랙·데모)은 수집 대상에서 제외.**
