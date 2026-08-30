"""특정 게임의 유저 리뷰를 근거로 질문에 답하는 툴. 리뷰 RAG."""
from pydantic import ConfigDict, Field

from model import StrictModel
from src.agent.retrieval import search_reviews_by_game
from src.loaders import load_games

FUNCTION_NAME = 'ask_about_game_reviews'


# ==================================
# 1. 인자 검증 모델
# ==================================
class AskAboutGameReviewsArguments(StrictModel):
    """ask_about_game_reviews 인자 검증 클래스"""
    model_config = ConfigDict(strict=True, extra='forbid')

    app_id: str = Field(min_length=1, max_length=20)
    question: str = Field(min_length=2, max_length=200)


ARGUMENTS = AskAboutGameReviewsArguments


# ==================================
# 2. LLM에게 보여줄 선언
# ==================================
DECLARATION = {
    'type': 'function',
    'name': FUNCTION_NAME,
    'description': (
        '특정 게임 1개에 대해 유저들이 실제로 뭐라고 하는지 리뷰에서 찾아 근거를 모은다. '
        '예 : "이 게임 핵 많아?", "최적화 어때?", "초보자도 할 만해?", "스토리 어때?" '
        '반드시 app_id를 알고 있을 때만 호출한다. app_id를 모르면 먼저 '
        'search_games_by_filter나 search_games_by_vibe로 게임을 찾아 app_id를 확보한다. '
        'app_id를 추측해서 넣지 않는다. '
        '가격·할인·장르처럼 상점에 적힌 정보는 리뷰가 아니라 get_game_detail로 조회한다.'
    ),
    'parameters': {
        'type': 'object',
        'properties': {
            'app_id': {
                'type': 'string',
                'description': '게임의 app_id. 숫자가 아니라 문자열로 넘긴다',
            },
            'question': {
                'type': 'string',
                'description': '그 게임에 대해 유저 평판을 묻는 질문',
            },
        },
        'required': ['app_id', 'question'],
    },
}


# ==================================
# 3. 실제 실행 함수
# ==================================
def _empty(app_id: str, name: str | None, reason: str, best: float) -> dict:
    """근거를 못 찾았을 때의 응답. 예외를 던지지 않는 이유는
    LLM이 실패 사유를 알아야 지어내지 않고 정확히 답하기 때문이다."""
    return {
        'success': False,
        'app_id': app_id,
        'name': name,
        'reason': reason,
        'best_similarity': best,
        'positive': [],
        'negative': [],
    }


def run(app_id: str, question: str) -> dict:
    """리뷰 근거를 긍정·부정으로 나눠 반환한다."""
    games = load_games()
    matched = games[games['app_id'] == app_id]

    # 없는 게임과 리뷰 없는 게임은 답변이 달라져야 하므로 사유를 구분한다
    if matched.empty:
        return _empty(app_id, None, '해당 app_id의 게임이 데이터에 없다', 0.0)

    name = matched.iloc[0]['name']
    found = search_reviews_by_game(app_id, question)

    if not (found['positive'] or found['negative']):
        return _empty(app_id, name, '이 질문에 답할 근거 리뷰가 없다',
                      found['best_similarity'])

    return {
        'success': True,
        'app_id': app_id,
        'name': name,
        'reason': None,
        'best_similarity': found['best_similarity'],
        'positive': found['positive'],
        'negative': found['negative'],
    }
