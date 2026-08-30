"""Steam Game Curator - RAG + Function Calling 에이전트 대시보드 진입점."""
import streamlit as st
from common import collection_counts, games_frame, reviews_frame, setup_page

setup_page('Steam Game Curator')

st.title('Steam Game Curator')
st.caption(
    '"3만원 이하인데 스토리가 감동적인 게임" 한 문장을 정형 조건과 취향으로 나눠 '
    '유저 리뷰를 근거로 답하는 RAG + Function Calling 에이전트입니다.'
)

st.markdown(
    """
    지난 미니 프로젝트가 **수집 → 정제 → 적재** 파이프라인을 다뤘다면,
    이번 과제의 중심은 **에이전트 설계**입니다.
    질문 하나가 답이 되기까지 아래 단계를 거칩니다.

    | 단계 | 모듈 | 하는 일 |
    |---|---|---|
    | 1. 툴 라우팅 | `src/agent/orchestrator.py` | LLM이 질문을 보고 5개 툴 중 무엇을 쓸지 스스로 고른다 |
    | 2. 인자 검증 | `src/agent/registry.py` | pydantic strict로 LLM이 만든 인자를 실행 전에 거른다 |
    | 3. 하이브리드 검색 | `src/agent/retrieval.py` | 가격·장르는 Chroma `where`로, 취향은 벡터로 동시에 건다 |
    | 4. 게임 단위 집계 | `src/agent/retrieval.py` | 리뷰 1건=1문서로 검색한 뒤 게임별 상위 3개 유사도 평균 |
    | 5. 근거 반환 | `src/agent/tools/*.py` | 추천마다 실제 리뷰 원문을 함께 돌려준다 |
    | 6. 임계값 차단 | `config.py` | 근거가 부족하면 생성 자체를 하지 않는다 |
    """
)

st.divider()

counts = collection_counts()
games = games_frame()
reviews = reviews_frame()

st.subheader('데이터·인덱싱 현황')
columns = st.columns(5)
columns[0].metric('게임', f'{len(games):,}건')
columns[1].metric('리뷰 청크', f'{len(reviews):,}건')
columns[2].metric('리뷰 보유 게임', f"{reviews['app_id'].nunique():,}개")
columns[3].metric('게임 벡터', f"{counts['steam_games']:,}건")
columns[4].metric('리뷰 벡터', f"{counts['steam_reviews']:,}건")

if not counts['steam_games'] or not counts['steam_reviews']:
    st.error(
        '벡터 인덱스가 비어 있습니다. 아래를 먼저 실행해주세요.\n\n'
        '```\nuv run python -m src.index.index_games\n'
        'uv run python -m src.index.index_reviews\n```'
    )
    st.stop()

st.divider()

st.subheader('이번 과제에서 답하려던 질문')
left, right = st.columns(2)

with left:
    st.markdown(
        """
        **"상점 설명에 없는 것을 어떻게 찾는가"**

        `핵이 많다`, `최적화가 나쁘다`, `난이도가 극악이다` 같은 평판은
        개발사가 상점 설명에 쓸 리 없습니다. 유저 리뷰에만 있습니다.

        그래서 게임 설명이 아니라 **리뷰 8,402건을 1건씩 임베딩**하고,
        검색 후 게임 단위로 집계하는 구조를 택했습니다.
        같은 20문항으로 두 방식을 재보니 P@5가 **0.320 → 0.547**로 올랐습니다.
        """
    )

with right:
    st.markdown(
        """
        **"없는 것을 없다고 말하게 하려면"**

        벡터 검색은 "없다"를 모릅니다. 무슨 질문을 넣어도 가장 가까운 걸 돌려줍니다.
        `세탁기 고치는 법`에도 게임 5개가 나옵니다.

        그래서 임계값을 실측으로 정했고, 미달이면 **LLM 호출 자체를 하지 않습니다.**
        다만 리뷰 질의 경로는 임계값으로 갈리지 않는다는 것도 측정으로 확인했고,
        그쪽은 프롬프트와 근거 노출로 막았습니다.
        """
    )

st.info(
    '왼쪽 사이드바에서 **큐레이터 챗봇 / 에이전트 설계 / 검색 성능 평가 / '
    '게임 상세 / 데이터 현황** 페이지로 이동할 수 있습니다.'
)
