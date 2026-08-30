"""processed CSV를 읽는 공통 로더."""
import functools
import json

import pandas as pd

from config import GAMES_PATH

CARD_COLUMNS = [
    'app_id', 'name', 'final_price', 'price', 'discount_percent', 'is_free',
    'review_score', 'review_score_desc', 'total_reviews', 'positive_ratio',
    'genres', 'player_modes', 'header_image', 'release_date', 'short_description',
]


@functools.lru_cache(maxsize=1)
def load_games() -> pd.DataFrame:
    """games.csv를 DataFrame으로 읽어서 return"""
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
    """DataFrame 상위 limit행을 LLM에 넘길 dict 리스트로 바꾼다."""
    subset = frame.head(limit)[CARD_COLUMNS]
    return json.loads(subset.to_json(orient='records', force_ascii=False))
