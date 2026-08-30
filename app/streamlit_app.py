"""Steam Game Curator - 프로젝트 개요."""
import streamlit as st
from common import setup_page

setup_page('Steam Game Curator')

st.title('Steam Game Curator')
st.caption('RAG + Function Calling 기반 게임 추천 에이전트')

st.markdown(
    """
    Steam 게임 1,220건과 유저 리뷰 8,402건을 대상으로,
    질문 한 문장을 정형 조건과 취향으로 나누어 답변하는 에이전트를 구축했습니다.
    어떤 방식으로 처리할지는 LLM이 스스로 판단하여 선택합니다.

    | 질문 유형 | 예시 | 처리 방식 |
    |---|---|---|
    | 정형 조건 | 3만원 이하 액션 게임 | pandas 필터링 |
    | 취향/감성 | 혼자 힐링되는 게임 | 리뷰 벡터 검색 |
    | 하이브리드 | 3만원 이하인데 스토리 좋은 게임 | Chroma `where` + 리뷰 벡터 검색 |
    | 평판 질의 | CS2 핵 많아? | 특정 게임 리뷰 RAG |
    """
)

st.divider()

st.subheader('페이지 구성')
st.markdown(
    """
    | 페이지 | 내용 |
    |---|---|
    | 데이터 | 수집한 데이터의 규모와 분포 |
    | 에이전트 설계 | 저장 형태, 처리 흐름, 툴 5개, 검색 경로 결정 |
    | 검색 성능 평가 | 설명만 임베딩과 리뷰 집계를 같은 문항으로 비교한 결과 |
    | 큐레이터 챗봇 | 실제 동작. 사이드바에 LLM의 툴 호출 과정 노출 |
    | 게임 상세 | 특정 게임의 리뷰를 근거로 답하는 경로 |
    """
)

st.divider()

st.subheader('환경')
st.markdown(
    """
    - 임베딩 `gemini-embedding-2` (768차원)
    - 생성 `gemini-3.7-flash` + Function Calling
    - 벡터 DB `Chroma` (cosine)
    - 인자 검증 `pydantic` strict
    """
)
