"""여러 게임을 나란히 비교하는 툴.

[담당: 팀원 C] 이 파일만 고치면 된다. 다른 파일은 건드리지 않는다.

작성법은 같은 폴더의 _template.py를 그대로 따라간다.

--------------------------------------------------------------------
할 일
--------------------------------------------------------------------
1. CompareGamesArguments 를 채운다
   - app_ids : list[str], 최소 2개 최대 4개
   * pydantic에서 리스트 개수 제한은 Field(min_length=2, max_length=4) 로 건다.
   * 1개만 넘어오면 "비교"가 아니므로 반드시 검증에서 막혀야 한다.

2. DECLARATION 을 채운다
   - description: 두 개 이상 네 개 이하의 게임을 app_id로 나란히 비교한다고 쓴다.
   - properties의 app_ids에는 'minItems': 2, 'maxItems': 4 도 함께 적는다.

3. run(app_ids) 를 구현한다
   - load_games()로 DataFrame을 받아 isin()으로 여러 app_id를 한 번에 찾는다.
   - LLM이 숫자로 넘길 수 있으니 [str(app_id) for app_id in app_ids] 로 맞춘 뒤 비교한다.
   - 찾지 못한 app_id는 버리지 말고 missing_app_ids에 담아 돌려준다.
     (LLM이 "3개 중 1개는 데이터에 없다"고 정확히 답할 수 있어야 한다)

--------------------------------------------------------------------
반환 형태
--------------------------------------------------------------------
    {
        'success': bool,              # 1건이라도 찾았으면 True
        'missing_app_ids': list[str], # 못 찾은 app_id
        'games': list[dict],          # to_records()의 결과
    }

--------------------------------------------------------------------
직접 확인하는 법
--------------------------------------------------------------------
    uv run python -m src.agent.tools.compare_games
"""
from pydantic import ConfigDict, Field

from model import StrictModel
from src.loaders import load_games, to_records

FUNCTION_NAME = 'compare_games'


# ==================================
# 1. 인자 검증 모델
# ==================================
class CompareGamesArguments(StrictModel):
    model_config = ConfigDict(strict=True, extra='forbid')

    app_ids: list[str] = Field(min_length=2, max_length=4)

ARGUMENTS = CompareGamesArguments


# ==================================
# 2. LLM에게 보여줄 선언
# ==================================
DECLARATION = {
    'type': 'function',
    'name': FUNCTION_NAME,
    'description': '두 개 이상 네 개 이하의 게임을 app_id로 나란히 비교한다.',
    'parameters': {
        'type': 'object',
        'properties': {
            'app_ids': {
                'type': 'array',
                'description': '비교할 Steam 게임의 app_id 목록',
                'items': {'type': 'string'},
                'minItems': 2,
                'maxItems': 4,
            },
        },
        'required': ['app_ids'],
    },
}

# ==================================
# 3. 실제 실행 함수
# ==================================
def run(app_ids: list[str]) -> dict:
    requested_app_ids = [str(app_id) for app_id in app_ids]

    games = load_games()
    matched = games[games['app_id'].isin(requested_app_ids)]

    found_app_ids = set(matched['app_id'].astype(str))
    missing_app_ids = [
        app_id for app_id in requested_app_ids
        if app_id not in found_app_ids
    ]

    return {
        'success': not matched.empty,
        'missing_app_ids': missing_app_ids,
        'games': to_records(matched, len(requested_app_ids)),
    }

if __name__ == '__main__':
    print(run(['730', '440']))
