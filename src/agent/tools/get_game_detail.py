"""app_id로 게임 한 개의 상세 정보를 조회하는 툴.

[담당: 팀원 C] 이 파일만 고치면 된다. 다른 파일은 건드리지 않는다.
(같은 담당인 compare_games.py 와도 파일이 분리돼 있으니 각각 따로 커밋하면 된다.)

작성법은 같은 폴더의 _template.py를 그대로 따라간다.

--------------------------------------------------------------------
할 일
--------------------------------------------------------------------
1. GetGameDetailArguments 를 채운다
   - app_id : str, 길이 1~12
   * app_id를 int가 아니라 str로 두는 이유: games.csv에서도 문자열로 읽고 있어서
     타입이 다르면 비교가 안 된다.

2. DECLARATION 을 채운다
   - description: app_id로 특정 게임 1개의 상세 정보(가격·할인·평가·장르·설명)를
     조회하는 툴이라고 쓴다.

3. run(app_id) 를 구현한다
   - load_games()로 DataFrame을 받아 app_id가 일치하는 행을 찾는다.
   - LLM이 app_id를 숫자로 넘길 수도 있으니 str(app_id)로 감싸서 비교한다.
   - 없으면 예외를 던지지 말고 success=False로 이유를 담아 돌려준다.
   - 있으면 to_records(matched, 1)[0] 으로 dict 하나를 만든다.

--------------------------------------------------------------------
반환 형태
--------------------------------------------------------------------
    찾았을 때:   {'success': True, 'game': dict}
    없을 때:     {'success': False, 'reason': '수집된 데이터에 app_id 999 가 없습니다.'}

--------------------------------------------------------------------
직접 확인하는 법
--------------------------------------------------------------------
    uv run python -m src.agent.tools.get_game_detail
"""
from pydantic import ConfigDict, Field

from model import StrictModel
from src.loaders import load_games, to_records

FUNCTION_NAME = 'get_game_detail'


# ==================================
# 1. 인자 검증 모델
# ==================================
class GetGameDetailArguments(StrictModel):
    model_config = ConfigDict(strict=True, extra='forbid')

    app_id: str = Field(min_length=1, max_length=12)

ARGUMENTS = GetGameDetailArguments


# ==================================
# 2. LLM에게 보여줄 선언
# ==================================
DECLARATION = {
    'type': 'function',
    'name': FUNCTION_NAME,
    'description': 'app_id로 특정 게임 1개의 상세 정보(가격·할인·평가·장르·설명)를 조회',
    'parameters': {
        'type': 'object',
        'properties': {
            'app_id': {
                'type': 'string',
                'description': '조회할 Steam 게임의 app_id',
                'minLength': 1,
                'maxLength': 12,
            },
        },
        'required': ['app_id'],
    },
}


# ==================================
# 3. 실제 실행 함수
# ==================================
def run(app_id: str) -> dict:
    games = load_games()
    matched = games[games['app_id'] == str(app_id)]

    if matched.empty:
        return {
            'success': False,
            'reason': f'수집된 데이터에 app_id {app_id} 가 없습니다.',
        }

    game = to_records(matched, 1)[0]

    return {
        'success': True,
        'game': game,
    }

if __name__ == '__main__':
    print(run('730'))
    print(run('존재하지않는id'))
