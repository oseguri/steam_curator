"""Streamlit 페이지들이 공유하는 유틸.

app/ 아래 스크립트는 streamlit이 실행하므로 프로젝트 루트가 sys.path에 없다.
여기서 한 번 끼워 넣어 각 페이지가 src.* 를 그대로 import할 수 있게 한다.
"""
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    GAME_COLLECTION,
    INTERACTIONS_PATH,
    QUALITY_PATH,
    REVIEW_COLLECTION,
)
from src.loaders import load_games, load_reviews

PAGE_ICON = '🎮'


def setup_page(title: str, icon: str = PAGE_ICON) -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout='wide')


# ==================================
# 데이터 로딩 (streamlit 캐시)
# ==================================
@st.cache_data(show_spinner=False)
def games_frame() -> pd.DataFrame:
    return load_games()


@st.cache_data(show_spinner=False)
def reviews_frame() -> pd.DataFrame:
    return load_reviews()


@st.cache_data(show_spinner=False)
def quality_frame() -> pd.DataFrame:
    if not QUALITY_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(QUALITY_PATH, encoding='utf-8-sig')


def interactions_frame() -> pd.DataFrame:
    """질의 기록. 챗봇을 쓸 때마다 늘어나므로 캐시하지 않는다."""
    if not INTERACTIONS_PATH.exists():
        return pd.DataFrame()
    rows = []
    for line in INTERACTIONS_PATH.read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def collection_counts() -> dict[str, int]:
    """인덱싱 현황. 컬렉션이 없으면 0으로 돌려준다."""
    from src.index.chroma_store import get_collection

    counts = {}
    for name in (GAME_COLLECTION, REVIEW_COLLECTION):
        try:
            counts[name] = get_collection(name).count()
        except Exception:  # noqa: BLE001
            counts[name] = 0
    return counts


# ==================================
# 표시 헬퍼
# ==================================
def format_price(game: dict) -> str:
    """무료·할인을 사람이 읽는 형태로."""
    if game.get('is_free') or not game.get('final_price'):
        return '무료'
    final = f"{game['final_price']:,}원"
    if game.get('discount_percent'):
        return f"~~{game['price']:,}원~~ **{final}** (-{game['discount_percent']}%)"
    return f'**{final}**'


def render_game_card(game: dict, show_evidence: bool = True) -> None:
    """추천 카드 하나.

    정형 검색과 취향 검색이 같은 필드 집합을 돌려주므로(카드 15개 필드 공통)
    이 함수 하나로 둘 다 그린다. 취향 검색에만 score/match_count/evidence가 더 있다.
    """
    image, body = st.columns([1, 3])

    with image:
        if game.get('header_image'):
            st.image(game['header_image'], width='stretch')

    with body:
        st.markdown(f"#### {game.get('name', '(이름 없음)')}")
        line = [format_price(game)]
        if game.get('review_score_desc'):
            ratio = game.get('positive_ratio') or 0
            line.append(f"{game['review_score_desc']} ({ratio:.0%})")
        if game.get('total_reviews'):
            line.append(f"리뷰 {game['total_reviews']:,}건")
        st.markdown(' · '.join(line))

        if game.get('genres'):
            st.caption(str(game['genres']).replace('|', ' · '))

        if game.get('score') is not None:
            match_count = game.get('match_count', 0)
            note = '' if match_count >= 3 else ' · 근거 적음'
            st.caption(f"유사도 {game['score']:.3f} · 매칭 리뷰 {match_count}건{note}")

        if game.get('short_description'):
            st.write(game['short_description'])

    evidence = game.get('evidence') or []
    if show_evidence and evidence:
        with st.expander(f"근거 리뷰 {len(evidence)}건"):
            for item in evidence:
                mark = '👍' if item['voted_up'] else '👎'
                st.markdown(
                    f"{mark} **유사도 {item['similarity']:.3f}** · "
                    f"플레이 {item['playtime_hours']:.0f}시간"
                )
                st.write(item['text'])
                st.divider()


def render_trace(trace: list[dict]) -> None:
    """LLM이 어떤 함수를 어떤 인자로 불렀는지. 사이드바에 그린다."""
    if not trace:
        st.info('툴 호출 없음 — 이전 대화 맥락을 바탕으로 답변합니다.')
        return

    for step, entry in enumerate(trace, start=1):
        ok = entry['validated']
        st.markdown(f"**{step}. `{entry['function']}`**")
        st.caption('✅ 검증 통과' if ok else f"❌ 검증 실패 — {entry['error']}")
        st.json(entry['arguments'], expanded=True)

        detail = [f"결과 {entry['returned']}건"]
        if entry.get('source'):
            label = {
                'search_by_vibe': '리뷰 집계',
                'search_by_description': '게임 설명(폴백)',
                '없음': '임계값 미달',
            }.get(entry['source'], entry['source'])
            detail.append(f'검색 경로: {label}')
        st.caption(' · '.join(detail))
        st.divider()
