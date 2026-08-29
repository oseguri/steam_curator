"""정형 조건(가격·장르·평가점수 등)으로 게임을 검색하는 툴.

[담당: 팀원 B] 이 파일만 고치면 된다. 다른 파일은 건드리지 않는다.

작성법은 같은 폴더의 _template.py를 그대로 따라간다.
데이터는 _common.load_games()로 읽는다(직접 read_csv 하지 말 것).

--------------------------------------------------------------------
할 일
--------------------------------------------------------------------
1. SearchGamesByFilterArguments 를 채운다
   - min_price, max_price   : int | None, 0 이상 500000 이하
   - genres                 : list[GenreType] | None, 최대 5개
   - player_modes           : list[PlayerModeType] | None, 최대 3개
   - is_free                : bool | None
   - min_review_score       : int | None, 1~9
   - min_total_reviews      : int | None, 0 이상
   - only_discounted        : bool | None
   - sort_by                : SortType | None
   - limit                  : int, 기본 5, 1~20
   * GenreType / PlayerModeType / SortType 은 model.py에 이미 정의돼 있으니 import해서 쓴다.
     (직접 새로 만들면 config·model과 목록이 어긋난다)

2. DECLARATION 을 채운다
   - 위 인자들을 properties에 그대로 옮긴다. enum이 있는 항목은 enum도 적는다.
   - description: "3만원 이하", "할인 중인", "평가 좋은" 처럼 수치·분류로 딱 떨어지는
     조건일 때 쓰는 툴이라고 쓰고, 분위기/취향 표현이면 search_games_by_vibe를 쓰라고 밝힌다.

3. run() 을 구현한다
   - load_games()로 DataFrame을 받아 조건을 하나씩 걸러낸다.
   - genres / player_modes 는 '액션|인디'처럼 파이프로 합쳐진 문자열 컬럼이다.
     str.contains 로 거르되, 여러 개면 '|'.join(...) 으로 OR 검색한다.
   - sort_by 는 SORT_KEYS 로 (컬럼, 오름차순여부)를 찾아 정렬한다. 값이 없으면 평가순.
   - 마지막에 to_records(frame, limit) 로 변환해서 반환한다.

--------------------------------------------------------------------
반환 형태 (이 모양을 지켜야 리드가 만드는 Streamlit 화면이 그대로 붙는다)
--------------------------------------------------------------------
    {
        'success': bool,              # 결과가 1건 이상이면 True
        'search_type': 'structured_filter',
        'total_matched': int,         # 필터를 통과한 전체 건수(limit 적용 전)
        'returned': int,              # 실제로 돌려준 건수
        'games': list[dict],          # to_records()의 결과
    }

--------------------------------------------------------------------
직접 확인하는 법
--------------------------------------------------------------------
    uv run python -m src.agent.tools.search_games_by_filter
"""
from pydantic import ConfigDict, Field

from model import StrictModel
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
    model_config = ConfigDict(strict=True, extra='forbid')

    # [예시] 선택 인자는 `int | None` + default=None 으로 둔다.
    # LLM이 안 보내면 run()에서 그 조건을 아예 걸지 않는다는 뜻이다.
    # 제약(ge/le)이 있으면 기본값도 Field() 안에 함께 넣는다.
    min_price: int | None = Field(default=None, ge=0, le=500000)

    # TODO: max_price, genres, player_modes, is_free, min_review_score,
    #       min_total_reviews, only_discounted, sort_by 를 여기에 이어서 채운다.
    #       리스트 개수 제한은 Field(max_length=...) 로 건다.
    #       GenreType / PlayerModeType / SortType 은 model.py에서 import 해온다.

    # limit만 None이 아닌 기본값을 갖는다. LLM이 안 보내면 5건을 돌려준다.
    limit: int = Field(default=5, ge=1, le=20)


ARGUMENTS = SearchGamesByFilterArguments


# ==================================
# 2. LLM에게 보여줄 선언
# ==================================
DECLARATION = {
    'type': 'function',
    'name': FUNCTION_NAME,
    # TODO: 이 툴을 언제 쓰는지 한 문장 + 예시 2~3개를 쓴다.
    #       분위기/취향 표현("힐링되는", "몰입감 있는")이면
    #       search_games_by_vibe 를 쓰라고 반드시 밝힌다.
    'description': '',  # TODO
    'parameters': {
        'type': 'object',
        # ARGUMENTS의 필드와 1:1로 대응시킨다.
        #   int -> 'integer' / ge= -> 'minimum' / le= -> 'maximum'
        #   Literal -> 'enum' / max_length= -> 'maxItems'
        'properties': {
            # [예시] description에 단위와 변환 예시를 적어야
            # LLM이 "2만원"을 2나 20000000이 아닌 20000으로 보낸다.
            'min_price': {
                'type': 'integer',
                'description': '최소 가격(원). 이 가격 이상인 게임만 찾는다. 예: "2만원 이상" -> 20000',
                'minimum': 0,
                'maximum': 500000,
            },
            # TODO: 나머지 인자들을 같은 방식으로 옮긴다.
            'limit': {
                'type': 'integer',
                'description': '돌려줄 게임 개수. 기본 5개.',
                'minimum': 1,
                'maximum': 20,
            },
        },
        # 전부 선택 인자라 required는 비워둔다.
        # (조건 없이 불러도 "평가순 상위 5개"라는 유효한 답이 나온다)
        'required': [],
    },
}


# ==================================
# 3. 실제 실행 함수
# ==================================
# TODO: 시그니처에 나머지 인자를 ARGUMENTS와 "똑같은 이름/기본값"으로 이어서 적는다.
#       리드의 orchestrator가 run(**검증된_인자) 형태로 부르기 때문에
#       이름이 하나라도 다르면 TypeError가 난다.
def run(min_price: int | None = None, limit: int = 5) -> dict:
    frame = load_games()

    # 조건을 하나씩 걸어 frame을 좁혀나간다.
    # frame을 덮어쓰며 이어 걸면 자연스럽게 AND 조건이 된다.
    #
    # `if min_price:` 라고 쓰면 안 된다. min_price=0("무료부터 전부")이
    # 거짓으로 취급돼 필터가 통째로 무시된다. 반드시 `is not None`으로 검사한다.
    if min_price is not None:
        frame = frame[frame['final_price'] >= min_price]

    # TODO: max_price(<=), min_total_reviews(>=), min_review_score(>=) 는 위와 같은 꼴.
    #       is_free / only_discounted 는 bool, genres / player_modes 는
    #       '액션|인디'처럼 파이프로 합쳐진 문자열이라 str.contains 로 거른다.

    # TODO: sort_by 정렬을 여기에 넣는다. 필터를 다 건 뒤, limit로 자르기 전이다.
    #       column, ascending = SORT_KEYS[sort_by or '평가순']

    # limit로 자르기 "전"의 전체 건수. LLM이 "총 153건 중 5건"이라고 말할 수 있어야 한다.
    total_matched = len(frame)
    games = to_records(frame, limit)

    # 결과가 0건이어도 예외를 던지지 않는다. success=False로 돌려줘야
    # LLM이 "조건에 맞는 게임이 없다"고 정확히 답할 수 있다.
    return {
        'success': len(games) > 0,
        'search_type': 'structured_filter',
        'total_matched': total_matched,
        'returned': len(games),
        'games': games,
    }


if __name__ == '__main__':
    # 손으로 호출해보면서 결과를 눈으로 확인한다.
    # 검증 -> 실행 순서는 리드의 orchestrator가 하는 것과 똑같다.
    # 검증에서 막힌 인자는 run()에 도달조차 하지 않는다는 점을 확인할 것.
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
