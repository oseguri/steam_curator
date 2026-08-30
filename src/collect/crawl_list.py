"""[1단계] Steam 검색 결과에서 app_id 목록을 수집한다.

수집과 파싱을 분리한다는 3차 프로젝트 원칙에 따라
이 단계에서는 app_id와 목록상 위치(rank)만 남기고 가공하지 않는다.
"""
import csv
import re

from bs4 import BeautifulSoup

from config import (
    APPID_LIST_PATH,
    GENRE_FILTERS,
    LIST_PAGE_COUNT,
    LIST_PAGE_SIZE,
    STEAM_SEARCH_URL,
    print_title,
)
from src.collect.http_client import get_json, sleep_between_requests

APPID_PATTERN = re.compile(r'/app/(\d+)')


def parse_results_html(html: str, source: str, start_rank: int) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    rows = []

    for offset, anchor in enumerate(soup.select('a[href*="/app/"]')):
        match = APPID_PATTERN.search(anchor.get('href', ''))
        if not match:
            continue

        title_tag = anchor.select_one('.title')

        rows.append({
            'app_id': match.group(1),
            'list_name': title_tag.get_text(strip=True) if title_tag else '',
            'source': source,
            'rank': start_rank + offset,
        })

    return rows


def crawl_pages(source: str, extra_params: dict) -> list[dict]:
    collected = []

    for page in range(LIST_PAGE_COUNT):
        start = page * LIST_PAGE_SIZE

        params = {
            'start': start,
            'count': LIST_PAGE_SIZE,
            'infinite': 1,
            'dynamic_data': '',
            'cc': 'kr',
            'l': 'koreana',
        }
        params.update(extra_params)

        payload = get_json(STEAM_SEARCH_URL, params=params)
        sleep_between_requests()

        if not payload or not payload.get('results_html'):
            print(f'  [{source}] page {page + 1}: 응답 없음. 중단')
            break

        rows = parse_results_html(payload['results_html'], source, start + 1)
        collected.extend(rows)
        print(f'  [{source}] page {page + 1}: {len(rows)}건 (누적 {len(collected)})')

        if len(rows) == 0:
            break

    return collected


def deduplicate(rows: list[dict]) -> list[dict]:
    """app_id 기준 중복 제거. 먼저 만난 항목(= 더 높은 순위)을 남긴다."""
    seen = set()
    unique = []

    for row in rows:
        if row['app_id'] in seen:
            continue
        seen.add(row['app_id'])
        unique.append(row)

    return unique


def save(rows: list[dict]) -> None:
    with APPID_LIST_PATH.open('w', encoding='utf-8-sig', newline='') as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=['app_id', 'list_name', 'source', 'rank'],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    print_title('[1단계] app_id 목록 수집')

    all_rows = []

    print('인기 판매순 수집')
    all_rows.extend(crawl_pages('topsellers', {'filter': 'topsellers'}))

    for genre_name, tag_id in GENRE_FILTERS.items():
        print(f'\n장르 수집: {genre_name}')
        all_rows.extend(
            crawl_pages(
                f'genre:{genre_name}',
                {'filter': 'topsellers', 'tags': tag_id},
            )
        )

    unique_rows = deduplicate(all_rows)

    print_title('수집 결과')
    print(f'전체 수집: {len(all_rows)}건')
    print(f'중복 제거 후: {len(unique_rows)}건')

    save(unique_rows)
    print(f'저장 완료: {APPID_LIST_PATH}')


if __name__ == '__main__':
    main()
