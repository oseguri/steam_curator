"""search_games_by_vibe.py"""
from pydantic import ConfigDict, Field

from config import RECOMMEND_TOP_N
from model import GenreType, StrictModel
from src.agent.retrieval import search_games

FUNCTION_NAME = 'search_games_by_vibe'


# ==================================
# 1. 인자 검증 모델
# ==================================
class SearchGamesByVibeArguments(StrictModel):
    """search_games_by_vibe 인자 검증 클래스"""
    model_config = ConfigDict(strict=True, extra='forbid')

    vibe_query: str = Field(min_length=2, max_length=200)
    max_price: int | None = Field(default=None, ge=0, le=500000)
    min_price: int | None = Field(default=None, ge=0, le=500000)
    is_free: bool | None = None
    genres: list[GenreType] | None = Field(default=None, max_length=5)
    min_review_score: int | None = Field(default=None, ge=1, le=9)
    limit: int = Field(default=RECOMMEND_TOP_N, ge=1, le=RECOMMEND_TOP_N)


ARGUMENTS = SearchGamesByVibeArguments


# ==================================
# 2. LLM에게 보여줄 선언
# ==================================
DECLARATION = {
    'type': 'function',
    'name': FUNCTION_NAME,
    'description': (
        '"힐링되는", "몰입감 있는", "눈물나는", "핵이 많은"처럼 분위기·취향·평판을 '
        '나타내는 표현으로 게임을 찾는다. 유저 리뷰를 근거로 검색하므로 '
        '상점 설명에 안 적히는 것(난이도 체감, 최적화, 핵 문제)도 찾을 수 있다. '
        '예 : "스토리가 감동적인 게임", "3만원 이하인데 혼자 힐링되는 게임", '
        '"핵 때문에 짜증나는 온라인 게임". '
        '가격·장르 조건은 vibe_query에 넣지 말고 별도 인자로 넘긴다. '
        '분위기 표현 없이 조건만 있으면(예: "3만원 이하 액션 게임") '
        'search_games_by_filter를 사용한다.'
    ),
    'parameters': {
        'type': 'object',
        'properties': {
            'vibe_query': {
                'type': 'string',
                'description': '취향·분위기를 나타내는 표현. 가격·장르 조건은 빼고 쓴다',
            },
            'max_price': {'type': 'integer', 'description': '최대 가격(원)'},
            'min_price': {'type': 'integer', 'description': '최소 가격(원)'},
            'is_free': {'type': 'boolean', 'description': '무료 게임만 볼 때 true'},
            'genres': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': '장르. 여러 개면 모두 만족하는 게임만 나온다',
            },
            'min_review_score': {
                'type': 'integer',
                'description': '최소 평가점수 1~9',
                'minimum': 1,
                'maximum': 9,
            },
        },
        'required': ['vibe_query'],
    },
}


# ==================================
# 3. 실제 실행 함수
# ==================================
def build_where(
    max_price: int | None,
    min_price: int | None,
    is_free: bool | None,
    genres: list[str] | None,
    min_review_score: int | None,
) -> dict | None:
    """정형 조건을 Chroma where 절로 조립"""
    conditions = []
    if max_price is not None:
        conditions.append({'final_price': {'$lte': max_price}})
    if min_price is not None:
        conditions.append({'final_price': {'$gte': min_price}})
    if is_free is not None:
        conditions.append({'is_free': is_free})
    if min_review_score is not None:
        conditions.append({'review_score': {'$gte': min_review_score}})
    for genre in genres or []:
        conditions.append({'genres': {'$contains': genre}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {'$and': conditions}


def run(
    vibe_query: str,
    max_price: int | None = None,
    min_price: int | None = None,
    is_free: bool | None = None,
    genres: list[str] | None = None,
    min_review_score: int | None = None,
    limit: int = RECOMMEND_TOP_N,
) -> dict:
    """취향 검색 결과를 반환한다. 근거 리뷰를 함께 실어 LLM이 지어내지 못하게 한다."""
    where = build_where(max_price, min_price, is_free, genres, min_review_score)
    games, source = search_games(vibe_query, filters=where)

    return {
        'success': bool(games),
        'search_type': 'vibe',
        'source': source,
        'returned': len(games[:limit]),
        'games': games[:limit],
    }