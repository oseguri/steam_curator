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

| 예시 | 의미 |
|---|---|
| `collect/fetch-details` | appdetails API 수집 |
| `collect/fetch-reviews` | appreviews API 수집 |
| `collect/standardize` | 표준화·품질검증 |
| `agent/retrieval` | RAG 검색 로직 |
| `app/tab3-dashboard` | Streamlit 대시보드 탭 |

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

## 2. 절대 하지 말 것

- `main` 브랜치에서 직접 코드 수정 후 커밋/푸시 (반드시 브랜치 따서 PR로)
- `git push --force` (특히 `main`에) — 다른 사람 작업이 통째로 날아갈 수 있음
- `git add .` 로 한 번에 다 올리기 — `.env`나 큰 데이터 파일이 실수로 딸려갈 수 있음
- `git reset --hard`, `git checkout .` 등 — 안 커밋한 내 작업이 사라짐. 헷갈리면 그냥 물어볼 것
- 다른 사람이 작업 중인 파일을 미리 말 없이 크게 리팩터링하기 — 충돌 원인 1위

---

## 3. 자주 막히는 상황

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

---

## 4. 로컬 개발 팁

- 각자 담당 스크립트를 짤 때 파일 맨 아래 `if __name__ == '__main__':` 블록으로 직접 실행해서 눈으로 확인하고 커밋할 것
  (예: `python -m src.collect.fetch_details`)
- 새 라이브러리가 필요하면 `pip install`이 아니라 `uv add <패키지명>` — `pyproject.toml`과 `uv.lock`이 같이 갱신되고,
  그 커밋을 받은 팀원은 `uv sync`만 다시 하면 됨
- 막히면 혼자 오래 붙잡지 말고 15~20분 안에 팀원/리드에게 공유. 이 프로젝트는 강의 스타일(`config.py` 중앙관리,
  `{'success': bool, ...}` 반환 등)을 따르므로 README의 "코드 스타일" 절과 이미 있는 `crawl_list.py`/`http_client.py`를
  참고하면 패턴을 그대로 베낄 수 있다.
