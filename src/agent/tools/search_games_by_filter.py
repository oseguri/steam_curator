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
from pydantic import ConfigDict

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

    # TODO: 위 "할 일 1"의 인자들을 채운다


ARGUMENTS = SearchGamesByFilterArguments


# ==================================
# 2. LLM에게 보여줄 선언
# ==================================
DECLARATION = {
    'type': 'function',
    'name': FUNCTION_NAME,
    'description': '',  # TODO
    'parameters': {
        'type': 'object',
        'properties': {},  # TODO
        'required': [],
    },
}


# ==================================
# 3. 실제 실행 함수
# ==================================
def run(**arguments) -> dict:
    # TODO: 인자를 ARGUMENTS와 똑같은 이름/기본값으로 풀어서 받도록 시그니처를 바꾸고 구현한다
    raise NotImplementedError('search_games_by_filter.run() 구현 필요')


if __name__ == '__main__':
    # 손으로 호출해보면서 결과를 눈으로 확인한다
    print(run(max_price=30000, genres=['액션'], limit=5))
