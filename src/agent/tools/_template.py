"""툴 파일 작성 템플릿 - 이 파일을 복사해서 자기 툴을 만든다.

[소유자: 리드 / 읽기 전용] 실제로 등록되지 않는 예시 파일이다. 고치지 말고 참고만 할 것.

툴 파일 하나에는 반드시 아래 3개가 **모두** 들어간다. 세 개를 한 파일에 모아두는 이유는
여러 명이 같은 파일을 건드리지 않게 하기 위해서다. (선언은 A파일, 검증은 B파일에 흩어두면
툴 하나 만들 때마다 3개 파일이 충돌한다.)

  1. ARGUMENTS  - pydantic 모델. LLM이 만들어낸 인자를 실행 전에 검증한다.  (8/26 강의)
  2. DECLARATION - LLM에게 보여줄 함수 설명(JSON schema).                   (8/25 강의)
  3. run()      - 실제로 실행되는 함수. 항상 {'success': bool, ...} 를 반환.

이름은 반드시 ARGUMENTS / DECLARATION / run 으로 맞춘다.
리드가 만드는 등록 파일(registry.py)이 이 세 이름을 기준으로 자동 수집하기 때문에,
이름이 다르면 툴이 등록되지 않는다.
"""
from pydantic import ConfigDict, Field

from model import StrictModel

# 파일 맨 위에 자기 툴의 함수 이름을 정해둔다. 선언과 등록에서 같은 값을 쓴다.
FUNCTION_NAME = 'example_tool'


# ==================================
# 1. 인자 검증 모델 (pydantic)
# ==================================
class ExampleToolArguments(StrictModel):
    """StrictModel을 상속하면 strict=True, extra='forbid'가 자동 적용된다.

    - strict=True      : "30000"(문자열)을 30000(정수)으로 몰래 바꾸지 않고 거절한다
    - extra='forbid'   : LLM이 지어낸 없는 인자를 거절한다
    - Field(ge=, le=)  : 숫자 범위를 벗어나면 거절한다
    """
    model_config = ConfigDict(strict=True, extra='forbid')

    keyword: str = Field(min_length=1, max_length=100)
    limit: int = Field(default=5, ge=1, le=20)


ARGUMENTS = ExampleToolArguments


# ==================================
# 2. LLM에게 보여줄 선언 (JSON schema)
# ==================================
# description은 LLM이 "이 툴을 쓸지 말지" 판단하는 유일한 근거다.
# 언제 쓰는지 + 언제 안 쓰는지를 예시와 함께 쓰면 라우팅 정확도가 크게 오른다.
DECLARATION = {
    'type': 'function',
    'name': FUNCTION_NAME,
    'description': (
        '(예시 툴입니다) 무엇을 하는 툴인지 한 문장으로 씁니다. '
        '"이런 질문일 때 쓰세요" 예시를 2~3개 넣습니다. '
        '헷갈리는 다른 툴이 있다면 "그럴 때는 XXX를 쓰세요"라고 밝혀줍니다.'
    ),
    'parameters': {
        'type': 'object',
        'properties': {
            'keyword': {'type': 'string', 'description': '검색어'},
            'limit': {
                'type': 'integer',
                'description': '결과 개수',
                'minimum': 1,
                'maximum': 20,
            },
        },
        # 반드시 있어야 하는 인자만 적는다. 나머지는 LLM이 필요할 때만 넣는다.
        'required': ['keyword'],
    },
}


# ==================================
# 3. 실제 실행 함수
# ==================================
def run(keyword: str, limit: int = 5) -> dict:
    """인자 이름과 기본값은 위 ARGUMENTS 모델과 정확히 일치해야 한다.

    검증을 통과한 인자만 여기로 들어오므로, 함수 안에서 타입 검사를 또 할 필요는 없다.
    반환값은 항상 dict이고 'success' 키를 반드시 포함한다.
    결과가 비었을 때도 예외를 던지지 말고 success=False로 돌려준다
    (예외를 던지면 LLM이 이유를 알 수 없어서 엉뚱한 답을 지어낸다).
    """
    return {
        'success': True,
        'search_type': 'example',
        'returned': 0,
        'games': [],
    }
