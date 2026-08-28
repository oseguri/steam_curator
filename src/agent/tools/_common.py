"""툴 함수들이 공통으로 쓰는 데이터 로딩 유틸.

[소유자: 리드] 이 파일은 여러 사람이 함께 쓰므로 직접 고치지 말고 리드에게 요청할 것.

각자 툴 파일에서 games.csv를 따로 읽지 말고 여기 있는 load_games()를 가져다 쓴다.
(각자 읽으면 dtype 처리가 제각각이 되어 app_id가 숫자로 변하거나 결측치 처리가 달라진다.)
"""
import functools
import json

import pandas as pd

from config import GAMES_PATH

# LLM에 돌려줄 게임 카드에 담는 컬럼. 전체 컬럼을 다 넘기면 토큰만 낭비된다.
CARD_COLUMNS = [
    'app_id', 'name', 'final_price', 'price', 'discount_percent', 'is_free',
    'review_score', 'review_score_desc', 'total_reviews', 'positive_ratio',
    'genres', 'player_modes', 'header_image', 'release_date', 'short_description',
]


@functools.lru_cache(maxsize=1)
def load_games() -> pd.DataFrame:
    """games.csv를 DataFrame으로 읽는다. 캐시되므로 여러 번 불러도 파일은 한 번만 읽는다.

    app_id를 str로 고정하는 이유: 숫자로 읽히면 앞자리 0이 사라지고
    LLM이 넘긴 문자열 app_id와 비교가 안 된다.
    """
    frame = pd.read_csv(GAMES_PATH, encoding='utf-8-sig', dtype={'app_id': str})

    for column in ('price', 'final_price', 'discount_percent',
                   'review_score', 'total_reviews', 'language_count'):
        frame[column] = pd.to_numeric(frame[column], errors='coerce').fillna(0).astype(int)

    frame['positive_ratio'] = pd.to_numeric(frame['positive_ratio'], errors='coerce').fillna(0.0)
    frame['is_free'] = frame['is_free'].astype(str) == 'True'

    for column in ('genres', 'categories', 'player_modes', 'short_description',
                   'review_score_desc', 'header_image', 'release_date'):
        frame[column] = frame[column].fillna('')

    return frame


def to_records(frame: pd.DataFrame, limit: int) -> list[dict]:
    """DataFrame 상위 limit행을 LLM에 넘길 dict 리스트로 바꾼다.

    to_dict()를 쓰지 않는 이유: numpy.int64 / numpy.bool_이 그대로 남아
    나중에 json.dumps가 터진다. to_json을 거쳐 순수 파이썬 타입으로 만든다.
    """
    subset = frame.head(limit)[CARD_COLUMNS]
    return json.loads(subset.to_json(orient='records', force_ascii=False))
