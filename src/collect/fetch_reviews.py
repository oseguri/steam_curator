"""[3단계] appreviews API로 리뷰를 수집한다.

긍정/부정을 각각 절반씩 수집한다. 그냥 최신순으로 받으면
리뷰 요약이 항상 긍정으로 기울기 때문이다(스팀 리뷰는 압도적으로 긍정이 많다).

리뷰 RAG 대상은 임베딩 비용 때문에 상위 REVIEW_TARGET_GAMES개 게임으로 한정한다.
"""
import csv
import json

from config import (
    GAMES_PATH,
    REVIEW_RAW_PATH,
    REVIEW_TARGET_GAMES,
    REVIEWS_PER_GAME,
    STEAM_REVIEW_URL,
    print_title,
)
from src.collect.http_client import get_json, sleep_between_requests


def load_target_app_ids() -> list[dict]:
    """games.csv에서 리뷰 수가 많은 상위 N개 게임을 고른다."""
    if not GAMES_PATH.exists():
        raise FileNotFoundError(
            f'{GAMES_PATH} 가 없습니다. standardize.py를 먼저 실행하세요.'
        )

    with GAMES_PATH.open('r', encoding='utf-8-sig', newline='') as csv_file:
        rows = list(csv.DictReader(csv_file))

    def review_count(row: dict) -> int:
        try:
            return int(row.get('total_reviews') or 0)
        except ValueError:
            return 0

    rows.sort(key=review_count, reverse=True)
    return rows[:REVIEW_TARGET_GAMES]


def load_done_app_ids() -> set[str]:
    if not REVIEW_RAW_PATH.exists():
        return set()

    done = set()
    with REVIEW_RAW_PATH.open('r', encoding='utf-8') as raw_file:
        for line in raw_file:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(str(json.loads(line)['app_id']))
            except Exception:  # noqa: BLE001, S112
                continue

    return done


def fetch_reviews(app_id: str, review_type: str, limit: int) -> list[dict]:
    """review_type: 'positive' | 'negative'"""
    collected = []
    cursor = '*'

    while len(collected) < limit:
        payload = get_json(
            STEAM_REVIEW_URL.format(app_id=app_id),
            params={
                'json': 1,
                'language': 'koreana',
                'filter': 'all',
                'review_type': review_type,
                'purchase_type': 'all',
                'num_per_page': 100,
                'cursor': cursor,
            },
        )
        sleep_between_requests()

        if not payload or not payload.get('success'):
            break

        reviews = payload.get('reviews') or []
        if not reviews:
            break

        collected.extend(reviews)

        next_cursor = payload.get('cursor')
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    return collected[:limit]


def main() -> None:
    print_title('[3단계] 리뷰 수집')

    targets = load_target_app_ids()
    done = load_done_app_ids()

    half = REVIEWS_PER_GAME // 2
    print(f'대상 게임: {len(targets)}개 / 이미 수집: {len(done)}개')
    print(f'게임당 긍정 {half}건 + 부정 {half}건')

    with REVIEW_RAW_PATH.open('a', encoding='utf-8') as raw_file:
        for index, game in enumerate(targets, start=1):
            app_id = game['app_id']

            if app_id in done:
                continue

            positive = fetch_reviews(app_id, 'positive', half)
            negative = fetch_reviews(app_id, 'negative', half)

            record = {
                'app_id': app_id,
                'name': game.get('name', ''),
                'positive': positive,
                'negative': negative,
            }
            raw_file.write(json.dumps(record, ensure_ascii=False) + '\n')
            raw_file.flush()

            print(
                f'{index}/{len(targets)} {app_id} {game.get("name", "")} '
                f'-> 긍정 {len(positive)} / 부정 {len(negative)}'
            )

    print_title('수집 결과')
    print(f'저장 위치: {REVIEW_RAW_PATH}')


if __name__ == '__main__':
    main()
