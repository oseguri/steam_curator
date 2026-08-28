"""Steam 요청 공통 - 재시도, 지연, 헤더를 한 곳에서 관리한다."""
import time

import requests

from config import MAX_RETRY, REQUEST_DELAY, REQUEST_TIMEOUT

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
    ),
    'Accept-Language': 'ko-KR,ko;q=0.9',
}

COOKIES = {
    # 성인 게임 페이지 우회 + 지역/언어 고정
    'birthtime': '536457601',
    'mature_content': '1',
    'Steam_Language': 'koreana',
}


def get_json(url: str, params: dict | None = None) -> dict | None:
    """실패 시 None을 돌려준다. 예외로 파이프라인을 멈추지 않는다."""
    for attempt in range(1, MAX_RETRY + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers=HEADERS,
                cookies=COOKIES,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 429:
                wait = REQUEST_DELAY * (attempt * 5)
                print(f'  429 발생. {wait:.1f}초 대기 후 재시도 ({attempt}/{MAX_RETRY})')
                time.sleep(wait)
                continue

            response.raise_for_status()
            return response.json()

        except Exception as error:
            print(f'  요청 실패({attempt}/{MAX_RETRY}): {type(error).__name__} {error}')
            time.sleep(REQUEST_DELAY * attempt)

    return None


def sleep_between_requests() -> None:
    time.sleep(REQUEST_DELAY)
