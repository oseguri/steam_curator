"""프로젝트 전역 설정 - 경로, 모델, 상수를 한 곳에서 관리한다."""
import os
from pathlib import Path

from dotenv import load_dotenv

# ==================================
# PATH
# ==================================
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env'

DATA_DIR = BASE_DIR / 'data'
RAW_DIR = DATA_DIR / 'raw'
PROCESSED_DIR = DATA_DIR / 'processed'

APPID_LIST_PATH = RAW_DIR / 'app_ids.csv'
DETAIL_RAW_PATH = RAW_DIR / 'detail_raw.jsonl'
REVIEW_RAW_PATH = RAW_DIR / 'review_raw.jsonl'

GAMES_PATH = PROCESSED_DIR / 'games.csv'
REVIEWS_PATH = PROCESSED_DIR / 'reviews.csv'
QUALITY_PATH = PROCESSED_DIR / 'quality_issues.csv'

# ==================================
# COLLECT
# ==================================
REQUEST_DELAY = 1.2
REQUEST_TIMEOUT = 15
MAX_RETRY = 3

LIST_PAGE_COUNT = 10
LIST_PAGE_SIZE = 50
REVIEWS_PER_GAME = 100
REVIEW_TARGET_GAMES = 300

STEAM_SEARCH_URL = 'https://store.steampowered.com/search/results/'
STEAM_DETAIL_URL = 'https://store.steampowered.com/api/appdetails'
STEAM_REVIEW_URL = 'https://store.steampowered.com/appreviews/{app_id}'

# 장르별 추가 수집 (Steam 장르 태그 ID)
GENRE_FILTERS = {
    '액션': '19',
    'RPG': '122',
    '시뮬레이션': '599',
    '전략': '9',
    '인디': '492',
    '캐주얼': '597',
}

# ==================================
# 표준화 / 품질검증
# ==================================
MIN_DESCRIPTION_LENGTH = 20   # 이보다 짧으면 임베딩 품질이 나빠 품질 이슈로 기록
MIN_REVIEW_LENGTH = 30        # 이보다 짧은 리뷰('추천', 'ㅋㅋ')는 임베딩해도 의미 없음
MAX_SAME_CHAR_RATIO = 0.3     # 동일 문자 비율이 이보다 높으면 도배/ASCII아트로 보고 제외
REVIEW_CHUNK_SIZE = 1000      # 리뷰는 1건=1문서가 기본. 이 길이를 넘을 때만 문장 경계로 분할


def print_title(title: str) -> None:
    print('\n' + '-' * 80)
    print(title)
    print('-' * 80)
    print()

# ==================================
# API key & Model
# ==================================
load_dotenv(ENV_PATH)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL')

# ==================================
# Vector DB / INDEXING
# ==================================
CHROMA_DIR = BASE_DIR / 'chroma_data'
GAME_COLLECTION = 'steam_games'
REVIEW_COLLECTION = 'steam_reviews'
EMBEDDING_DIM = 768
EMBED_BATCH_SIZE = 100 #임베딩 진행률 출력 간격
EMBED_WORKERS = 8
CHROMA_BATCH_SIZE = 1000

for _dir in (RAW_DIR, PROCESSED_DIR, CHROMA_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ==================================
# SEARCH
# ==================================
REVIEW_SEARCH_K = 100 #리뷰 컬렉션 1차 검색 개수
TOP_REVIEWS_PER_GAME = 3 #게임 점수 - 상위 3개
RECOMMEND_TOP_N = 5 # 최종 추천 게임 수
MAX_CONTEXT_DOCS = 4 # 리뷰 질의 시 LLM에 넣을 문서 수
VIBE_THRESHOLD = 0.3 # 추천 질의 임계값 - 테스트 통해 수정
REVIEW_THRESHOLD = 0.55 # 리뷰 질의 임계값 - 테스트 통해 수정
