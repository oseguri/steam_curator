"""LLM 오케스트레이션 - function calling 루프 + pydantic 검증.

ask()는 {'answer', 'trace', 'results', 'interaction_id'}를 반환한다.
trace는 Streamlit 사이드바에 실시간으로 뿌릴 호출 기록이다.
"""
import uuid

from google import genai
from google.genai import types
from pydantic import ValidationError

from config import GEMINI_API_KEY, GEMINI_MODEL
from src.agent.constant import MAX_TURNS, SYSTEM_PROMPT
from src.agent.registry import ARGUMENT_MODELS, FUNCTION_MAP, TOOLS
from src.agent.utils import finish

client = genai.Client(api_key=GEMINI_API_KEY)


def build_config(with_tools: bool = True) -> types.GenerateContentConfig:
    """GenerateContentConfig 생성"""
    if not with_tools:
        return types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)

    declarations = [
        {key: value for key, value in declaration.items() if key != 'type'}
        for declaration in TOOLS
    ]
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=declarations)],
    )


def execute_call(call) -> tuple[dict, dict]:
    """호출 1건을 검증하고 실행한다. (LLM에 돌려줄 결과, trace 항목)을 반환"""
    arguments = dict(call.args or {})
    entry = {
        'function': call.name,
        'arguments': arguments,
        'validated': False,
        'error': None,
        'returned': 0,
        'source': None,
    }

    if call.name not in FUNCTION_MAP:
        entry['error'] = f'등록되지 않은 함수다. 사용 가능: {sorted(FUNCTION_MAP)}'
        return {'success': False, 'error': entry['error']}, entry

    try:
        validated = ARGUMENT_MODELS[call.name](**arguments)
    except ValidationError as error:
        entry['error'] = '; '.join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
        return {'success': False, 'error': entry['error']}, entry

    entry['validated'] = True
    result = FUNCTION_MAP[call.name](**validated.model_dump())
    entry['returned'] = result.get('returned', len(result.get('games', [])))
    entry['source'] = result.get('source')
    return result, entry

def to_messages(history: list[dict] | None, question: str) -> list[types.Content]:
    """{'role': 'user'|'model', 'text': ...} 목록을 Gemini 형식으로 바꾼다.

    Streamlit이 google.genai 타입을 몰라도 되게 평범한 dict로 주고받는다.
    이력에는 함수 호출 턴을 넣지 않는다. 질문과 최종 답변만 있으면
    "그 중에 제일 싼 건?" 같은 후속 질문의 맥락으로 충분하고,
    함수 응답까지 쌓으면 토큰이 금방 불어난다.
    """
    messages = [
        types.Content(role=item['role'], parts=[types.Part(text=item['text'])])
        for item in (history or [])
    ]
    messages.append(types.Content(role='user', parts=[types.Part(text=question)]))
    return messages


def ask(question: str, history: list[dict] | None = None) -> dict:
    """질문 하나를 처리. history는 {'role', 'text'} 목록"""
    interaction_id = uuid.uuid4().hex[:12]
    messages = to_messages(history, question)
    config = build_config()
    trace: list[dict] = []
    results: list[dict] = []

    for _ in range(MAX_TURNS):
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=messages,
            config=config,
        )

        calls = response.function_calls or []
        if not calls:
            return finish(interaction_id, question, response.text, trace, results)

        messages.append(response.candidates[0].content)

        response_parts = []
        for call in calls:
            result, entry = execute_call(call)
            trace.append(entry)
            if result.get('success'):
                results.append(result)
            response_parts.append(
                types.Part.from_function_response(
                    name=call.name, response={'result': result}
                )
            )
        messages.append(types.Content(role='user', parts=response_parts))

    final = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=messages,
        config=build_config(with_tools=False),
    )
    return finish(interaction_id, question, final.text, trace, results)


if __name__ == '__main__':
    from config import print_title

    # 발표 시나리오 4개. 시연 직전 점검용으로도 쓴다
    SCENARIOS = [
        ('정형', '3만원 이하 액션 게임 5개 알려줘'),
        ('취향', '혼자 조용히 힐링되는 게임 추천해줘'),
        ('하이브리드', '3만원 이하인데 스토리가 감동적인 게임 있어?'),
        ('환각 차단', '그란 투리스모 8 재밌어?'),
    ]

    for label, question in SCENARIOS:
        print_title(f'[{label}] {question}')
        answer = ask(question)

        for step, entry in enumerate(answer['trace'], start=1):
            status = 'OK' if entry['validated'] else f'검증실패({entry["error"]})'
            source = f' source={entry["source"]}' if entry['source'] else ''
            print(f'  {step}. {entry["function"]}  {status}'
                  f'  결과 {entry["returned"]}건{source}')
            print(f'     인자 {entry["arguments"]}')

        print()
        print(answer['answer'])
        print()
