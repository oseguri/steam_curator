"""프로젝트 전역 설정 - 경로, 모델, 상수를 한 곳에서 관리한다."""
from pathlib import Path

# ==================================
# PATH
# ==================================
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env'

DATA_DIR = BASE_DIR / 'data'
RAW_DIR = DATA_DIR / 'raw'
PROCESSED_DIR = DATA_DIR / 'processed'

APPID_LIST_PATH = RAW_DIR / 'app_ids.csv'

for _dir in (RAW_DIR, PROCESSED_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ==================================
# COLLECT
# ==================================
REQUEST_DELAY = 1.2
REQUEST_TIMEOUT = 15
MAX_RETRY = 3

LIST_PAGE_COUNT = 10
LIST_PAGE_SIZE = 50

STEAM_SEARCH_URL = 'https://store.steampowered.com/search/results/'

# 장르별 추가 수집 (Steam 장르 태그 ID)
GENRE_FILTERS = {
    '액션': '19',
    'RPG': '122',
    '시뮬레이션': '599',
    '전략': '9',
    '인디': '492',
    '캐주얼': '597',
}


def print_title(title: str) -> None:
    print('\n' + '-' * 80)
    print(title)
    print('-' * 80)
    print()
