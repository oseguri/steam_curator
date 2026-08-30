"""에이전트 설계 - 질문 하나가 답이 되기까지의 구조와 그렇게 정한 근거."""
import pandas as pd
import streamlit as st
from common import setup_page
from pydantic import ValidationError

setup_page('에이전트 설계', '🧭')

from config import (
    DESCRIPTION_THRESHOLD,
    PRIMARY_SOURCE_SLOTS,
    RECOMMEND_TOP_N,
    REVIEW_SEARCH_K,
    REVIEW_THRESHOLD,
    TOP_REVIEWS_PER_GAME,
    VIBE_THRESHOLD,
)
from src.agent.registry import ARGUMENT_MODELS, TOOLS

st.title('에이전트 설계')
st.caption('질문 한 문장이 근거 있는 답변이 되기까지의 흐름과, 각 단계를 그렇게 정한 이유입니다.')

# ---------------------------------------------------------------------------
st.header('1. 전체 흐름')

st.graphviz_chart(
    """
    digraph agent {
        rankdir=LR;
        bgcolor="transparent";
        node [shape=box style="rounded,filled" fontname="sans-serif" fontsize=11
              color="#7f8c9b" fillcolor="#eef2f6" fontcolor="#1b2733"];
        edge [color="#7f8c9b" fontname="sans-serif" fontsize=9 fontcolor="#5a6b7b"];

        question [label="사용자 질문" fillcolor="#dbe7f3"];
        llm      [label="LLM 라우팅\\n툴 5개 중 선택" fillcolor="#dbe7f3"];
        valid    [label="pydantic strict 검증\\nextra=forbid / Literal" fillcolor="#faeee0"];

        subgraph cluster_tools {
            label="툴"; style="rounded,dashed"; color="#b0bcc7"; fontcolor="#5a6b7b"; fontsize=10;
            filter [label="search_games_by_filter\\n정형 조건"];
            vibe   [label="search_games_by_vibe\\n취향 · 하이브리드"];
            review [label="ask_about_game_reviews\\n리뷰 RAG"];
            etc    [label="get_game_detail\\ncompare_games"];
        }

        pandas [label="games.csv\\npandas 필터" shape=cylinder];
        chroma [label="Chroma\\n리뷰 8,402 / 게임 1,220" shape=cylinder fillcolor="#e6e0f0"];
        agg    [label="게임 단위 집계\\n상위 3개 유사도 평균" fillcolor="#e4efe2"];
        gate   [label="임계값 차단\\n미달이면 생성 안 함" fillcolor="#faeee0"];
        answer [label="근거 리뷰를 인용한 답변" fillcolor="#dbe7f3"];

        question -> llm -> valid;
        valid -> filter; valid -> vibe; valid -> review; valid -> etc;
        filter -> pandas; etc -> pandas;
        vibe -> chroma; review -> chroma;
        chroma -> agg -> gate -> answer;
        pandas -> answer;
        valid -> llm [label="검증 실패 시 사유 반환" style=dashed];
    }
    """
)

st.markdown(
    """
    **검증을 LLM과 실행 사이에 끼운 이유**: LLM은 존재하지 않는 인자나 없는 장르명을
    만들어냅니다. 그대로 실행하면 엉뚱한 결과가 나오거나 런타임에서 터집니다.
    검증 실패를 예외로 던지지 않고 **사유를 LLM에게 돌려주면** 인자를 고쳐 다시 부릅니다.
    위 그림의 점선이 그 경로입니다.
    """
)

# ---------------------------------------------------------------------------
st.divider()
st.header('2. 툴 5개')

st.caption(
    '`src/agent/registry.py`가 `src/agent/tools/` 아래 파일을 자동으로 수집합니다. '
    '아래 표는 지금 실제로 등록된 목록을 그대로 읽은 것입니다.'
)

st.dataframe(
    pd.DataFrame([
        {
            '함수': declaration['name'],
            '인자': len(declaration['parameters']['properties']),
            '필수': ', '.join(declaration['parameters'].get('required', [])) or '-',
            '설명': declaration['description'].split('. ')[0],
        }
        for declaration in TOOLS
    ]),
    width='stretch',
    hide_index=True,
)

st.markdown(
    """
    툴 파일에는 `FUNCTION_NAME` / `ARGUMENTS` / `DECLARATION` / `run` 네 이름을 고정해 둡니다.
    팀원 3명이 각자 파일 하나씩 맡아도 충돌하지 않게 하려는 구조인데,
    이름이 어긋나면 조용히 등록에서 빠지거나 런타임에 터집니다.
    그래서 `registry.py`가 **import 시점에 네 가지를 검사**하고 어긋나면 즉시 예외를 냅니다.

    - `FUNCTION_NAME`과 `DECLARATION['name']`이 같은가 — 다르면 LLM이 부르는 이름과 실행되는 게 갈린다
    - 함수 이름이 중복되지 않는가 — 나중에 등록된 툴이 앞의 것을 덮어쓴다
    - `ARGUMENTS` 필드와 `run()` 파라미터가 일치하는가 — 검증은 통과하고 실행에서 `TypeError`가 난다
    - `DECLARATION` 속성이 `ARGUMENTS`의 부분집합인가 — 선언에만 있는 인자는 `extra='forbid'`에 걸려 전부 거절된다
    """
)

# ---------------------------------------------------------------------------
st.divider()
st.header('3. 검증 계층이 실제로 막는 것')

st.caption('아래 표는 지금 이 페이지를 그리면서 실제 pydantic 모델에 넣어본 결과입니다.')

CASES = [
    ('search_games_by_vibe', {'vibe_query': '힐링되는 게임', '유령인자': 1}, '없는 인자를 지어냄'),
    ('search_games_by_vibe', {'vibe_query': '힐링되는 게임', 'max_price': '30000'}, '숫자를 문자열로 넘김'),
    ('search_games_by_vibe', {'vibe_query': '힐링되는 게임', 'genres': ['핵앤슬래시']}, '존재하지 않는 장르'),
    ('search_games_by_vibe', {'vibe_query': '힐링되는 게임', 'min_review_score': 99}, '범위를 벗어난 값'),
    ('ask_about_game_reviews', {'app_id': 730, 'question': '핵 많아?'}, 'app_id를 숫자로 넘김'),
    ('search_games_by_vibe', {'vibe_query': '힐링되는 게임', 'max_price': 30000}, '정상 호출'),
]

rows = []
for function_name, arguments, label in CASES:
    try:
        ARGUMENT_MODELS[function_name](**arguments)
        rows.append({'상황': label, '결과': '통과', '사유': '-'})
    except ValidationError as error:
        first = error.errors()[0]
        rows.append({
            '상황': label,
            '결과': '차단',
            '사유': f"{'.'.join(str(part) for part in first['loc'])} — {first['msg']}",
        })

st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

st.markdown(
    """
    `strict=True`라서 `"30000"`을 30000으로 몰래 바꾸지 않고 거절합니다.
    타입을 알아서 맞춰주면 편할 것 같지만, LLM이 무엇을 잘못 넘겼는지 영영 모르게 됩니다.
    """
)

# ---------------------------------------------------------------------------
st.divider()
st.header('4. 취향 검색은 왜 리뷰를 1건씩 임베딩하는가')

left, right = st.columns(2)

with left:
    st.graphviz_chart(
        """
        digraph vibe {
            rankdir=TB;
            bgcolor="transparent";
            node [shape=box style="rounded,filled" fontname="sans-serif" fontsize=10
                  color="#7f8c9b" fillcolor="#eef2f6" fontcolor="#1b2733"];
            edge [color="#7f8c9b" fontsize=9 fontcolor="#5a6b7b"];

            q [label="취향 질문 + 정형 조건" fillcolor="#dbe7f3"];
            w [label="Chroma where\\n가격 · 장르 · 평가" fillcolor="#faeee0"];
            s [label="리뷰 top100 검색"];
            g [label="app_id로 그룹핑"];
            t [label="게임 점수 =\\n상위 3개 유사도 평균" fillcolor="#e4efe2"];
            r [label="상위 5게임 + 근거 리뷰" fillcolor="#dbe7f3"];

            q -> w -> s -> g -> t -> r;
        }
        """
    )

with right:
    st.markdown(
        f"""
        **정형 조건을 검색 단계에서 거는 이유**

        "3만원 이하인데 스토리 좋은 게임"에서 가격을 나중에 거르면,
        상위 {REVIEW_SEARCH_K}건이 전부 5만원짜리일 때 남는 게 없습니다.
        Chroma `where`로 먼저 좁히면 {REVIEW_SEARCH_K}칸이 조건에 맞는 게임에 배분됩니다.

        실제로 필터를 걸면 매칭 리뷰 수가 **오히려 늘어납니다**
        (To the Moon 7건 → 8건). 후필터로는 얻을 수 없는 효과입니다.

        **상위 {TOP_REVIEWS_PER_GAME}개 평균을 쓰는 이유**

        합계는 리뷰가 많은 게임이 무조건 이기고, 최대값은 튀는 리뷰 하나에 휘둘립니다.
        다만 매칭이 {TOP_REVIEWS_PER_GAME}건 미만이면 평균이 사실상 최대값이 되어,
        리뷰 1건짜리 게임이 7건짜리를 이기는 일이 실제로 있었습니다
        (ARK 0.776 > To the Moon 0.766).
        그래서 **부족분을 0으로 채워** 평균 냅니다.
        """
    )

# ---------------------------------------------------------------------------
st.divider()
st.header('5. 검색 경로를 고르는 방법')

st.markdown(
    f"""
    리뷰가 있는 게임은 299개뿐이고 나머지 921개는 상점 설명만 있습니다.
    처음에는 *"리뷰 집계가 빈 결과일 때만 설명으로 폴백"* 으로 짰는데,
    **한 번도 발동하지 않았습니다.** 리뷰 집계가 헛짚어도 임계값은 넘기 때문입니다.

    `기차 운전 시뮬레이터`를 물으면 트럭 게임 5개를 0.72로 돌려줍니다.
    정답인 기차 게임 4개는 전부 리뷰가 없어서 리뷰 경로에 **존재하지도 않습니다.**

    측정해 보니 갈라주는 신호가 있었습니다.
    리뷰 집계는 근거가 있으면 0.75~0.83, 헛짚으면 0.72로 떨어지는데
    설명 경로는 해당 장르 게임이 있으면 0.73을 유지합니다.
    → **두 경로를 모두 돌려 1위 점수가 높은 쪽에 {PRIMARY_SOURCE_SLOTS}자리, 나머지 1자리를 반대 경로로** 채웁니다.
    """
)

st.dataframe(
    pd.DataFrame([
        {'방식': '설명만 임베딩', 'Hit@5': 0.867, 'P@5': 0.320, 'R@5': 0.302},
        {'방식': '리뷰 집계', 'Hit@5': 0.867, 'P@5': 0.467, 'R@5': 0.401},
        {'방식': '점수 비교 라우팅 (현재)', 'Hit@5': 1.000, 'P@5': 0.547, 'R@5': 0.481},
    ]),
    width='stretch',
    hide_index=True,
)

st.caption('자세한 문항별 결과는 **검색 성능 평가** 페이지에 있습니다.')

# ---------------------------------------------------------------------------
st.divider()
st.header('6. 임계값과 환각 차단')

columns = st.columns(3)
columns[0].metric('취향 검색', VIBE_THRESHOLD, help='관련 최저 0.7130 / 무관 최고 0.6334')
columns[1].metric('설명 폴백', DESCRIPTION_THRESHOLD, help='관련 최저 0.6006 / 무관 최고 0.5728')
columns[2].metric('리뷰 질의', REVIEW_THRESHOLD, help='관련과 무관이 0.1320 겹친다')

st.markdown(
    f"""
    벡터 검색은 "없다"를 모릅니다. `세탁기 고치는 법`에도 가장 가까운 게임 {RECOMMEND_TOP_N}개를 돌려줍니다.
    그래서 관련 질문과 무관 질문을 각각 던져 점수 분포를 재고, 그 사이 빈 구간에 임계값을 놓았습니다.

    **다만 리뷰 질의 경로는 임계값으로 갈리지 않는다는 것도 측정으로 확인했습니다.**
    `app_id`로 한 게임에 좁힌 뒤라 후보 리뷰가 전부 그 게임 얘기여서,
    유사도가 *"질문에 답이 되는가"* 가 아니라 *"이 게임 얘기인가"* 만 반영합니다.
    실제로 `이 게임 요리 레시피 알려줘`(0.6126)가 `최적화는 어떤가요?`(0.4807)보다 높게 나옵니다.

    → 이 경로의 환각 방지는 임계값이 아니라 **시스템 프롬프트와 근거 원문 노출**이 맡습니다.
    README에 처음 적었던 계획(0.65)을 측정 결과로 뒤집은 부분입니다.
    """
)
