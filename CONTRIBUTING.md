# 협업 가이드 (Git/GitHub 처음이어도 이대로만 따라하면 됨)

3명이 각자 브랜치에서 작업하고, GitHub에서 Pull Request(PR)로 합친다.
**절대 `main` 브랜치에 직접 커밋/푸시하지 않는다.** 이것만 지키면 실수해도 되돌리기 쉽다.

---

## 0. 최초 1회 설정

### 0-1. 프로그램 설치 확인

```bash
git --version
uv --version
```

둘 중 하나라도 안 되면 먼저 설치:
- git: https://git-scm.com/downloads
- uv: https://docs.astral.sh/uv/getting-started/installation/

### 0-2. 깃허브 계정 ↔ 로컬 연결 (최초 1회)

```bash
git config --global user.name "본인 GitHub 아이디"
git config --global user.email "본인 GitHub 가입 이메일"
```

`git push` 할 때 로그인 창이 뜨면 GitHub 아이디/비밀번호 대신 **Personal Access Token**을 비밀번호 칸에 입력한다
(GitHub 비밀번호 자체는 더 이상 안 먹힘). 토큰 발급: GitHub 우측 상단 프로필 → Settings → Developer settings →
Personal access tokens → Generate new token (권한은 `repo` 체크).

### 0-3. 저장소 받기

```bash
git clone https://github.com/oseguri/steam_curator.git
cd steam_curator
uv sync                # pyproject.toml 기준으로 가상환경 + 의존성 자동 설치
```

`.env` 파일은 git에 안 올라가 있다(비밀키라서 의도적으로 제외됨, `.gitignore` 참고).
`.env.example`을 복사해서 직접 만든다:

```bash
cp .env.example .env
```

지금 단계(API 수집)는 `.env`가 비어 있어도 동작한다. 나중에 Gemini API 키를 쓰는 사람만 채우면 된다.

### 0-4. 스크립트는 항상 `uv run`으로 실행한다

`uv sync`는 프로젝트 전용 가상환경(`.venv`)에만 패키지를 설치한다. 그냥 `python main.py`처럼
실행하면 컴퓨터에 원래 깔려있던 전역 Python이 잡혀서 `ModuleNotFoundError: No module named 'bs4'` 같은
에러가 난다. 항상 앞에 `uv run`을 붙이거나, 가상환경을 먼저 활성화하고 쓴다.

```bash
uv run python main.py
uv run python -m src.collect.fetch_details
```

매번 `uv run` 붙이기 귀찮으면 터미널 하나를 계속 켜두고 가상환경을 활성화해서 쓴다(터미널 새로 열 때마다 다시 해야 함):

```powershell
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux / WSL
source .venv/bin/activate
```

활성화되면 프롬프트 앞에 `(steam-curator)`가 붙는다. 그 상태에서는 `python main.py`만 써도 된다.

---

## 1. 매번 작업할 때 흐름

### 1-1. 시작 전에 최신 상태로 맞추기

```bash
git checkout main
git pull origin main
```

### 1-2. 내 작업용 브랜치 만들기

```bash
git checkout -b <브랜치이름>
```

**브랜치 이름 규칙**: `담당영역/할일` 형식, 영어 소문자 + 하이픈.
**브랜치는 파일 하나 단위로 딴다** — 그래야 PR도 작아지고 충돌도 안 난다.

| 예시 | 의미 |
|---|---|
| `tools/search-games-by-filter` | 정형 조건 검색 툴 (팀원 B) |
| `tools/get-game-detail` | 게임 상세 조회 툴 (팀원 C) |
| `tools/compare-games` | 게임 비교 툴 (팀원 C) |
| `agent/retrieval` | RAG 검색 로직 (리드) |
| `app/tab3-dashboard` | Streamlit 대시보드 탭 (리드) |

### 1-3. 코드 작성 → 커밋

```bash
git status                 # 뭐가 바뀌었는지 먼저 확인 (중요)
git add src/collect/fetch_details.py   # 파일을 콕 집어서 추가. git add . 은 되도록 쓰지 말 것
git commit -m "appdetails API로 게임 상세 수집 스크립트 작성"
```

**커밋 메시지는 한국어로, "무엇을 했는지"를 한 줄로.** 너무 잘게 쪼갤 필요 없고,
하나의 작업 단위(함수 하나 완성, 버그 하나 수정)가 끝날 때마다 커밋하면 된다.

`git status`에 `.env`, `data/`, `chroma_data/`, `.venv/` 같은 게 보이면 **add하지 말 것** —
이미 `.gitignore`에 등록돼 있어서 정상적으로는 안 보여야 한다. 보인다면 바로 물어볼 것.

### 1-4. 내 브랜치를 GitHub에 올리기

```bash
git push origin <브랜치이름>
```

### 1-5. Pull Request 만들기

1. GitHub 저장소 페이지로 가면 방금 푸시한 브랜치로 "Compare & pull request" 버튼이 뜬다.
2. 제목: 한 줄 요약 (예: "appdetails 수집 스크립트 추가")
3. 설명: 뭘 했는지, 어떻게 테스트했는지 3줄 이내.
4. 다른 팀원 1명을 리뷰어로 지정하고 알림 준다(단톡방 등).
5. 리뷰어가 확인하고 Approve 하면 **"Squash and merge"** 버튼으로 합친다.
6. 합친 뒤에는 GitHub에서 "Delete branch" 눌러서 브랜치 정리.

### 1-6. 로컬 정리

```bash
git checkout main
git pull origin main
git branch -d <브랜치이름>
```

---

## 2. 파일 소유권 — 충돌을 없애는 핵심 규칙

이 프로젝트는 **파일 1개 = 담당자 1명**으로 쪼개놨다. 자기 파일만 고치면 충돌이 아예 안 난다.
누가 어느 파일을 맡는지는 README의 "9. 분업"에 있다.

| 구분 | 파일 | 규칙 |
|---|---|---|
| 내 파일 | 예: `src/agent/tools/get_game_detail.py` | 마음대로 고친다 |
| 남의 파일 | 다른 담당자 이름이 붙은 파일 | 읽는 건 자유, **수정 금지** |
| 공용 파일 | `config.py`, `model.py`, `src/agent/tools/_common.py`, `src/agent/registry.py` | **리드만 수정.** 필요하면 요청 |

- 상수(경로·임계값 등)를 추가하고 싶어도 `config.py`를 직접 고치지 않는다. 리드에게 말한다.
  모두가 `config.py`에 한 줄씩 더하는 게 충돌 1순위 원인이다.
- 공용 데이터 로딩은 `src/agent/tools/_common.py`의 `load_games()`를 쓴다.
  자기 파일에서 `pd.read_csv`를 새로 쓰지 않는다(사람마다 타입 처리가 달라져서 버그가 난다).
- 남의 코드를 보다가 고치고 싶은 게 보이면 직접 고치지 말고 담당자에게 알려준다.

---

## 3. 절대 하지 말 것

- `main` 브랜치에서 직접 코드 수정 후 커밋/푸시 (반드시 브랜치 따서 PR로)
- `git push --force` (특히 `main`에) — 다른 사람 작업이 통째로 날아갈 수 있음
- `git add .` 로 한 번에 다 올리기 — `.env`나 큰 데이터 파일이 실수로 딸려갈 수 있음
- `git reset --hard`, `git checkout .` 등 — 안 커밋한 내 작업이 사라짐. 헷갈리면 그냥 물어볼 것
- 남의 파일·공용 파일을 말 없이 수정하거나 포맷팅 정리하기 — 충돌 원인 1위

---

## 4. 자주 막히는 상황

### "다른 사람이 먼저 push해서 내 push가 거부됨"

```bash
git pull origin <브랜치이름>   # 상대 변경사항을 먼저 받아온다
# 충돌(conflict)이 나면 파일 안의 <<<<<<< / ======= / >>>>>>> 표시 부분을 직접 골라서 정리
git add <충돌났던 파일>
git commit
git push origin <브랜치이름>
```

### "커밋했는데 메시지를 잘못 씀"

직전 커밋 하나만이고 아직 push 안 했다면:

```bash
git commit --amend -m "새 메시지"
```

이미 push했다면 그냥 새 커밋을 하나 더 추가한다 (`--amend` + `--force push`는 하지 않는다).

### "뭔가 꼬였는데 뭘 해야 할지 모르겠음"

`git status` 결과를 그대로 캡처해서 팀원이나 리드한테 물어본다. 대부분은 지우기 전에 상태부터 보면 해결된다.

### "`ModuleNotFoundError: No module named 'bs4'`(설치했는데도 안 잡힘)"

`uv sync`까지 했는데도 이 에러가 나면 `uv run` 없이 그냥 `python`으로 실행한 경우다.
위 0-4를 참고해서 `uv run python ...`으로 실행하거나 가상환경을 먼저 활성화한다.

### "`uv sync`가 `.venv` 파일을 못 지운다고 에러남 (Windows, 액세스 거부)"

WSL/Linux에서 만든 `.venv`를 그대로 Windows에서 열면, 리눅스 심볼릭 링크(`lib64 -> lib`)를
Windows가 못 지워서 나는 에러다. `.venv` 폴더를 통째로 지우고 `uv sync`를 다시 돌리면 된다.

```powershell
Remove-Item -Recurse -Force .venv
uv sync
```

같은 프로젝트 폴더를 WSL과 Windows 양쪽에서 번갈아 쓰면 계속 날 수 있으니, 되도록 한쪽 환경만 정해서 쓴다.

---

## 5. 로컬 개발 팁

- 자기 툴을 짤 때는 파일 맨 아래 `if __name__ == '__main__':` 블록으로 직접 실행해서 눈으로 확인하고 커밋할 것
  (예: `uv run python -m src.agent.tools.get_game_detail`, 항상 `uv run`을 붙인다 — 0-4 참고)
- 툴 파일을 처음 열면 맨 위 주석에 "할 일"과 "반환 형태"가 적혀 있다. 그대로 따라가면 된다.
  구조가 헷갈리면 같은 폴더의 `_template.py`에 완성된 예시가 있으니 보고 베낀다.
- 툴 파일은 `games.csv`가 있어야 실행된다. 리드가 수집을 끝내고 공유해주면 `data/processed/`에 넣고 쓴다.
- 새 라이브러리가 필요하면 `pip install`이 아니라 `uv add <패키지명>` — `pyproject.toml`과 `uv.lock`이 같이 갱신되고,
  그 커밋을 받은 팀원은 `uv sync`만 다시 하면 됨
- 막히면 혼자 오래 붙잡지 말고 15~20분 안에 팀원/리드에게 공유. 이 프로젝트는 강의 스타일(`config.py` 중앙관리,
  `{'success': bool, ...}` 반환 등)을 따르므로 README의 "코드 스타일" 절과 이미 있는 `crawl_list.py`/`http_client.py`를
  참고하면 패턴을 그대로 베낄 수 있다.
