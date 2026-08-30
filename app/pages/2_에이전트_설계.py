"""에이전트 설계 - 저장 형태, 처리 흐름, 툴, 검색 경로."""
import pandas as pd
import streamlit as st
from common import collection_counts, setup_page

setup_page('에이전트 설계', '🧭')

st.title('에이전트 설계')

counts = collection_counts()

# ---------------------------------------------------------------------------
st.header('1. 데이터 저장 구조')

st.markdown(
    f"""
    수집 결과는 CSV 두 개로, 검색용 벡터는 Chroma 컬렉션 두 개로 나눠 담았습니다.

    | | 원본 | Chroma 컬렉션 | 문서 1건의 단위 |
    |---|---|---|---|
    | 게임 | `games.csv` | `steam_games` {counts['steam_games']:,}건 | 게임 1개 |
    | 리뷰 | `reviews.csv` | `steam_reviews` {counts['steam_reviews']:,}건 | **리뷰 1건** |
    """
)

game_tab, review_tab = st.tabs(['steam_games', 'steam_reviews'])

with game_tab:
    st.markdown('**임베딩한 문장** — 이름 + 장르 + 플레이 방식 + 짧은 설명')
    st.code('To the Moon. 어드벤처, 인디, RPG. 싱글 플레이어. '
            '두 명의 박사가 죽어가는 남자의 마지막 소원을 인공적으로 이루어주기 위해...', language='text')

    st.markdown('**메타데이터** — 검색 조건으로 걸거나 추천 카드를 그릴 때 씁니다.')
    st.dataframe(
        pd.DataFrame([
            {'필드': 'app_id', '값 예시': '206440', '용도': '문서 id'},
            {'필드': 'name', '값 예시': 'To the Moon', '용도': '표시'},
            {'필드': 'final_price', '값 예시': '10800', '용도': '가격 조건'},
            {'필드': 'price', '값 예시': '10800', '용도': '표시'},
            {'필드': 'discount_percent', '값 예시': '0', '용도': '표시'},
            {'필드': 'is_free', '값 예시': 'False', '용도': '조건'},
            {'필드': 'review_score', '값 예시': '9', '용도': '평가 조건'},
            {'필드': 'review_score_desc', '값 예시': '압도적으로 긍정적', '용도': '표시'},
            {'필드': 'total_reviews', '값 예시': '86,396', '용도': '표시'},
            {'필드': 'positive_ratio', '값 예시': '0.9613', '용도': '표시'},
            {'필드': 'genres', '값 예시': "['어드벤처', '인디', 'RPG']", '용도': '장르 조건'},
            {'필드': 'player_modes', '값 예시': "['싱글 플레이어']", '용도': '조건'},
            {'필드': 'header_image', '값 예시': 'https://...', '용도': '카드 이미지'},
            {'필드': 'release_date', '값 예시': '2012년 9월 7일', '용도': '표시'},
            {'필드': 'short_description', '값 예시': '두 명의 박사가...', '용도': '표시'},
        ]),
        width='stretch', hide_index=True, height=380,
    )
    st.caption(
        '임베딩 문장에 `categories`는 넣지 않았습니다. `Steam Cloud`, `가족 공유` 같은 기술 태그가 '
        '문장의 42%를 차지해 취향 검색에 방해가 됩니다. 의미 있는 항목은 `player_modes`가 이미 추려둔 5종입니다.'
    )

with review_tab:
    st.markdown('**임베딩한 문장** — 리뷰 원문 그대로')
    st.code('게임은 유저가 운영하고 회사는 장사만 함  핵은 쳐돌아다니는데 잡는 건 감감무소식이고, '
            '신고를 해도 이 새끼들이 신고를 읽기는 하는지...', language='text')

    st.markdown('**메타데이터** — 아래 6개는 `games.csv`에서 가져와 붙였습니다.')
    st.dataframe(
        pd.DataFrame([
            {'필드': 'app_id', '값 예시': '730', '출처': '리뷰', '용도': '게임별 묶기'},
            {'필드': 'name', '값 예시': 'Counter-Strike 2', '출처': '리뷰', '용도': '표시'},
            {'필드': 'review_id', '값 예시': '232965962', '출처': '리뷰', '용도': '원문 추적'},
            {'필드': 'voted_up', '값 예시': 'True', '출처': '리뷰', '용도': '긍정·부정 나누기'},
            {'필드': 'playtime_hours', '값 예시': '2309.0', '출처': '리뷰', '용도': '표시'},
            {'필드': 'votes_up', '값 예시': '4', '출처': '리뷰', '용도': '표시'},
            {'필드': 'final_price', '값 예시': '0', '출처': '게임', '용도': '가격 조건'},
            {'필드': 'is_free', '값 예시': 'True', '출처': '게임', '용도': '조건'},
            {'필드': 'review_score', '값 예시': '8', '출처': '게임', '용도': '평가 조건'},
            {'필드': 'total_reviews', '값 예시': '9,823,266', '출처': '게임', '용도': '표시'},
            {'필드': 'genres', '값 예시': "['액션', '무료 플레이']", '출처': '게임', '용도': '장르 조건'},
            {'필드': 'player_modes', '값 예시': "['멀티플레이어']", '출처': '게임', '용도': '조건'},
        ]),
        width='stretch', hide_index=True, height=350,
    )
    st.caption(
        '리뷰에 게임 정보를 붙여둔 이유는 "3만원 이하인데 스토리 좋은 게임"의 가격 조건을 '
        '리뷰를 검색하는 시점에 함께 걸기 위해서입니다. 검색한 뒤에 거르면 '
        '상위 100건이 전부 조건 밖일 때 남는 것이 없습니다.'
    )

st.info(
    '**리뷰를 게임별로 합치지 않고 1건씩 저장한 이유** — 합치면 벡터가 평균으로 흐려져 '
    '정답 유사도(0.45~0.51)가 무관한 질문의 점수(0.54)보다도 낮아집니다. '
    '무엇보다 어떤 리뷰가 걸렸는지 알 수 없어 근거 원문을 보여줄 수 없습니다.'
)

st.info(
    '**리뷰 문장에 게임 이름을 붙이지 않은 이유** — 붙이면 같은 게임의 리뷰끼리 유사도가 3배로 뭉쳐, '
    '벡터가 "무슨 말을 했는가"보다 "어느 게임인가"를 담게 됩니다. 게임이 무엇인지는 메타데이터에 이미 있습니다.'
)

# ---------------------------------------------------------------------------
st.divider()
st.header('2. 처리 흐름')

st.graphviz_chart(
    """
    digraph agent {
        rankdir=LR;
        bgcolor="transparent";
        node [shape=box style="rounded,filled" fontname="sans-serif" fontsize=11
              color="#7f8c9b" fillcolor="#eef2f6" fontcolor="#1b2733"];
        edge [color="#7f8c9b" fontname="sans-serif" fontsize=9 fontcolor="#5a6b7b"];

        q     [label="질문" fillcolor="#dbe7f3"];
        llm   [label="LLM\\n툴 5개 중 선택" fillcolor="#dbe7f3"];
        valid [label="pydantic 검증" fillcolor="#faeee0"];
        tool  [label="툴 실행"];
        store [label="games.csv / Chroma" shape=cylinder fillcolor="#e6e0f0"];
        ans   [label="근거를 인용한 답변" fillcolor="#dbe7f3"];

        q -> llm -> valid -> tool -> store -> ans;
        valid -> llm [label="실패 사유 반환" style=dashed];
    }
    """
)

st.caption(
    'LLM이 만들어낸 인자는 실행 전에 pydantic으로 검사합니다. 없는 장르명, 문자열로 넘긴 숫자, '
    '지어낸 인자가 여기서 막힙니다. 검사에 걸리면 예외를 내지 않고 사유를 LLM에 돌려주어 다시 부르게 합니다.'
)

# ---------------------------------------------------------------------------
st.divider()
st.header('3. 툴 5개')

st.markdown('LLM은 질문을 보고 아래 다섯 개 중에서 고릅니다.')

st.dataframe(
    pd.DataFrame([
        {
            '툴': 'search_games_by_filter',
            '이럴 때 씁니다': '"3만원 이하 액션 게임 5개"',
            '입력': '가격 · 장르 · 평가점수 · 정렬',
            '찾는 곳': 'games.csv',
            '돌려주는 것': '게임 카드 N개',
        },
        {
            '툴': 'search_games_by_vibe',
            '이럴 때 씁니다': '"혼자 힐링되는 게임"',
            '입력': '취향 문장 + 가격 · 장르',
            '찾는 곳': 'steam_reviews / steam_games (벡터)',
            '돌려주는 것': '게임 카드 5개 + 근거 리뷰 3건씩',
        },
        {
            '툴': 'ask_about_game_reviews',
            '이럴 때 씁니다': '"이 게임 핵 많아?"',
            '입력': 'app_id + 질문',
            '찾는 곳': 'steam_reviews (해당 게임만, 벡터)',
            '돌려주는 것': '긍정 2건 / 부정 2건',
        },
        {
            '툴': 'get_game_detail',
            '이럴 때 씁니다': '"그 게임 얼마야?"',
            '입력': 'app_id',
            '찾는 곳': 'games.csv',
            '돌려주는 것': '게임 1개 상세',
        },
        {
            '툴': 'compare_games',
            '이럴 때 씁니다': '"이 둘 중에 뭐가 나아?"',
            '입력': 'app_id 2~4개',
            '찾는 곳': 'games.csv',
            '돌려주는 것': '게임 여러 개 + 못 찾은 id',
        },
    ]),
    width='stretch',
    hide_index=True,
)

st.caption(
    '벡터 검색을 쓰는 것은 `search_games_by_vibe`와 `ask_about_game_reviews` 두 개입니다. '
    '나머지 셋은 `games.csv`를 조건으로 거릅니다.'
)

st.markdown(
    """
    **취향 검색이 게임 점수를 매기는 방법**

    리뷰 100건을 검색해 게임별로 묶고, 각 게임에서 유사도 상위 3건을 평균 냅니다.
    걸린 리뷰가 3건보다 적으면 모자란 자리를 0으로 채웁니다.
    그렇게 하지 않으면 평균이 사실상 최고점이 되어, 리뷰 1건이 걸린 게임이 7건 걸린 게임을 이깁니다.
    """
)

# ---------------------------------------------------------------------------
st.divider()
st.header('4. 두 컬렉션 검색 라우팅 전략')

st.markdown(
    """
    리뷰를 수집한 게임은 299개이고 나머지 921개는 상점 설명만 있습니다.
    그래서 취향 질문이 들어오면 `steam_reviews`로 답할 수 있는 경우와 없는 경우가 갈립니다.

    처음에는 **`steam_reviews`를 검색해 결과가 하나도 없을 때만 `steam_games`를 검색**하도록 만들었습니다.
    측정해 보니 두 번째 검색이 한 번도 실행되지 않았습니다.
    리뷰 검색이 엉뚱한 답을 내놓아도 결과는 비어 있지 않기 때문입니다.
    `기차 운전 시뮬레이터`를 물으면 트럭 게임이 나오는데, 정답인 기차 게임은 리뷰가 없어
    `steam_reviews`에 아예 들어 있지 않습니다.

    두 컬렉션의 점수를 비교해 보니 구분이 됐습니다.
    리뷰 검색은 실제로 관련된 리뷰가 있을 때와 없을 때 점수가 눈에 띄게 갈리는데,
    게임 설명 검색은 해당 장르의 게임이 있으면 점수를 유지했습니다.

    → **두 컬렉션을 모두 검색해 1위 점수가 높은 쪽을 우선하고, 남는 자리를 나머지 쪽으로 채웁니다.**
    """
)

st.dataframe(
    pd.DataFrame([
        {'상황': '리뷰에 관련 내용이 충분', '우선하는 컬렉션': 'steam_reviews', '예': '스토리가 감동적인 게임'},
        {'상황': '리뷰를 수집하지 않은 장르', '우선하는 컬렉션': 'steam_games', '예': '기차 운전 시뮬레이터'},
        {'상황': '양쪽 모두 점수가 낮음', '우선하는 컬렉션': '없음 (빈 결과)', '예': '세탁기 고치는 법'},
    ]),
    width='stretch',
    hide_index=True,
)

st.caption('이렇게 바꾼 뒤 P@5가 0.467에서 0.547로 올랐습니다. 자세한 수치는 검색 성능 평가 페이지에 있습니다.')
