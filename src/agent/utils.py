'''agent util 함수'''
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from config import INTERACTIONS_PATH
from src.agent.registry import ARGUMENT_MODELS, FUNCTION_MAP


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

def log_interaction(record: dict) -> None:
    """질의 기록을 한 줄씩 남긴다. 탭3 대시보드가 읽는다.

    기록 실패가 답변을 막으면 안 되므로 예외를 삼킨다.
    """
    try:
        with INTERACTIONS_PATH.open('a', encoding='utf-8') as file:
            file.write(json.dumps(record, ensure_ascii=False) + '\n')
    except OSError:
        pass

def finish(
    interaction_id: str,
    question: str,
    answer: str | None,
    trace: list[dict],
    results: list[dict],
) -> dict:
    """반환값을 만들고 기록을 남긴다. 반환 지점이 둘이라 한 곳에 모은다."""
    log_interaction({
        'interaction_id': interaction_id,
        'asked_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds'),
        'question': question,
        'answer': answer,
        # 인자까지 통째로 남긴다. 어떤 질문이 왜 실패했는지 나중에 되짚는다
        'trace': trace,
        'result_count': sum(len(result.get('games', [])) for result in results),
    })
    return {
        'answer': answer,
        'trace': trace,
        'results': results,
        'interaction_id': interaction_id,
    }