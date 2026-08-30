"""정형 조건(가격·장르·평가점수 등)으로 게임을 검색하는 툴."""
from pydantic import ConfigDict, Field

from model import (
    GENRE_ENUM,
    PLAYER_MODE_ENUM,
    SORT_ENUM,
    GenreType,
    PlayerModeType,
    SortType,
    StrictModel,
)
from src.agent.tools._common import load_games, to_records

FUNCTION_NAME = 'search_games_by_filter'

# sort_by 값 -> (정렬할 컬럼, 오름차순인가?)
SORT_KEYS = {
    '평가순': ('review_score', False),
    '가격낮은순': ('final_price', True),
    '가격높은순': ('final_price', False),
    '리뷰많은순': ('total_reviews', False),
    '할인율순': ('discount_percent', False),
}


# ==================================
# 1. 인자 검증 모델
# ==================================
class SearchGamesByFilterArguments(StrictModel):
    """search_games_by_filter 인자 검증 클래스"""
    model_config = ConfigDict(strict=True, extra='forbid')

    min_price: int | None = Field(default=None, ge=0, le=500000)
    max_price: int | None = Field(default=None, ge=0, le=500000)
    genres: list[GenreType] | None = Field(default=None, max_length=5)
    player_modes: list[PlayerModeType] | None = Field(default=None, max_length=3)
    is_free: bool | None = None
    only_discounted: bool | None = None
    min_review_score: int | None = Field(default=None, ge=1, le=9)
    min_total_reviews: int | None = Field(default=None, ge=0)
    sort_by: SortType | None = None
    limit: int = Field(default=5, ge=1, le=20)


ARGUMENTS = SearchGamesByFilterArguments


# ==================================
# 2. LLM에게 보여줄 선언
# ==================================
DECLARATION = {
    'type': 'function',
    'name': FUNCTION_NAME,
    'description': (
        '가격, 장르, 플레이 방식, 평가점수, 할인 여부처럼 수치나 분류로 딱'
        '떨어지는 조건으로 게임 목록을 찾는다.'
        '예 : "3만원 이하 액션 게임", "할인 중인 인디 게임 5개", "평가 좋은 협동 게임"'
        '"힐링되는", "몰입감 있는"처럼 분위기나 취향을 나타내는 표현이면 이 툴이 아니라'
        'search_games_by_vibe를 사용한다.'
        ),
    'parameters': {
        'type': 'object',
        'properties': {
            'min_price': {
                'type': 'integer',
                'description': '최소 가격(원). 이 가격 이상인 게임만 찾는다. 예: "2만원 이상" -> 20000',
                'minimum': 0,
                'maximum': 500000,
            },
            'max_price': {
                'type': 'integer',
                'description': '최대 가격(원). 이 가격 이하인 게임만 찾는다. 예: "3만원 이하" -> 30000',
                'minimum': 0,
                'maximum': 500000,
            },
            'genres': {
                'type': 'array',
                'description': '장르 목록. 여러 개를 넣으면 하나라도 해당하는 게임을 찾는다(OR). 최대 5개.',
                'items': {'type': 'string', 'enum': GENRE_ENUM},
                'maxItems': 5,
            },
            'player_modes': {
                'type': 'array',
                'description': '플레이 방식 목록. 여러 개를 넣으면 하나라도 해당하는 게임을 찾는다(OR). 최대 3개.',
                'items': {'type': 'string', 'enum': PLAYER_MODE_ENUM},
                'maxItems': 3,
            },
            'is_free': {
                'type': 'boolean',
                'description': 'true면 무료 게임만, false면 유료 게임만 찾는다. 예: "무료 게임" -> true',
            },
            'min_review_score': {
                'type': 'integer',
                'description': (
                    '최소 평가점수(1~9). 높을수록 좋은 평가다. '
                    '예: "평가 좋은" -> 7, "평가 아주 좋은" -> 8'
                ),
                'minimum': 1,
                'maximum': 9,
            },
            'min_total_reviews': {
                'type': 'integer',
                'description': '최소 리뷰 수. 예: "리뷰 1000개 이상인" -> 1000',
                'minimum': 0,
            },
            'only_discounted': {
                'type': 'boolean',
                'description': 'true면 현재 할인 중인 게임만 찾는다. 예: "할인 중인" -> true',
            },
            'sort_by': {
                'type': 'string',
                'description': '정렬 기준. 지정하지 않으면 평가순으로 정렬한다.',
                'enum': SORT_ENUM,
            },
            'limit': {
                'type': 'integer',
                'description': '돌려줄 게임 개수. 기본 5개.',
                'minimum': 1,
                'maximum': 20,
            },
        },
        'required': [],
    },
}


# ==================================
# 3. 실제 실행 함수
# ==================================
def run(
    min_price: int | None = None,
    max_price: int | None = None,
    genres: list[str] | None = None,
    player_modes: list[str] | None = None,
    is_free: bool | None = None,
    min_review_score: int | None = None,
    min_total_reviews: int | None = None,
    only_discounted: bool | None = None,
    sort_by: str | None = None,
    limit: int = 5,
) -> dict:
    """
    조건들을 인자로 받고 필터링 한 게임들을 반환
    """

    frame = load_games()

    if min_price is not None:
        frame = frame[frame['final_price'] >= min_price]
    if max_price is not None:
        frame = frame[frame['final_price'] <= max_price]

    if min_review_score is not None:
        frame = frame[frame['review_score'] >= min_review_score]

    if min_total_reviews is not None:
        frame = frame[frame['total_reviews'] >= min_total_reviews]


    if is_free is not None:
        frame = frame[frame['is_free'] == is_free]

    if only_discounted is not None:
        if only_discounted:
            frame = frame[frame['discount_percent'] > 0]
        else:
            frame = frame[frame['discount_percent'] <= 0]


    if genres:
        frame = frame[frame['genres'].str.contains('|'.join(genres), na=False)]

    if player_modes:
        frame = frame[frame['player_modes'].str.contains('|'.join(player_modes), na=False)]

    column, ascending = SORT_KEYS[sort_by or '평가순']
    frame = frame.sort_values(column, ascending=ascending)

    total_matched = len(frame)
    games = to_records(frame, limit)

    return {
        'success': len(games) > 0,
        'search_type': 'structured_filter',
        'total_matched': total_matched,
        'returned': len(games),
        'games': games,
    }


if __name__ == '__main__':
    from pydantic import ValidationError

    CASES = [
        ('정상', {'min_price': 50000}),
        ('빈 인자', {}),
        ('문자열 가격', {'min_price': '50000'}),   # LLM이 "50000"을 보낸 경우
        ('음수 가격', {'min_price': -1}),
        ('없는 인자', {'max_pirce': 30000}),       # LLM의 오타/환각
    ]

    for label, raw_arguments in CASES:
        try:
            validated = ARGUMENTS(**raw_arguments)
        except ValidationError as error:
            reason = error.errors()[0]['type']
            print(f'차단  {label:8} {reason}')
            continue

        result = run(**validated.model_dump())
        print(f'통과  {label:8} total_matched={result["total_matched"]:4} '
              f'returned={result["returned"]}')
