"""appdetails API로 게임 상세(설명·가격·장르·개발사)를 수집"""
import csv
import json

from config import (
    APPID_LIST_PATH,
    DETAIL_RAW_PATH,
    STEAM_DETAIL_URL,
    STEAM_REVIEW_URL,
    print_title,
)
from src.collect.http_client import get_json, sleep_between_requests


def load_app_ids() -> list[dict]:
    if not APPID_LIST_PATH.exists():
        raise FileNotFoundError(
            f'{APPID_LIST_PATH} 가 없습니다. crawl_list.py를 먼저 실행하세요.'
        )

    with APPID_LIST_PATH.open('r', encoding='utf-8-sig', newline='') as csv_file:
        return list(csv.DictReader(csv_file))


def load_done_app_ids() -> set[str]:
    if not DETAIL_RAW_PATH.exists():
        return set()

    done = set()
    with DETAIL_RAW_PATH.open('r', encoding='utf-8') as raw_file:
        for line in raw_file:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(str(json.loads(line)['app_id']))
            except Exception:  # noqa: BLE001, S112
                continue

    return done


def fetch_review_summary(app_id: str) -> dict:
    """리뷰 본문 없이 query_summary만 받는다(num_per_page=0).

    평가점수(1~9)와 긍/부정 건수는 appdetails에는 없고 appreviews의
    query_summary로만 얻을 수 있다.
    """
    payload = get_json(
        STEAM_REVIEW_URL.format(app_id=app_id),
        params={
            'json': 1,
            'language': 'all',
            'purchase_type': 'all',
            'num_per_page': 0,
        },
    )

    if not payload or not payload.get('success'):
        return {}

    return payload.get('query_summary') or {}


def fetch_one(app_id: str) -> dict:
    # appdetails는 1회 호출당 appid 1개만 안정적으로 응답한다(실측). 배치로 넣으면 일부 null.
    payload = get_json(
        STEAM_DETAIL_URL,
        params={'appids': app_id, 'l': 'korean', 'cc': 'kr'},
    )

    if payload is None:
        return {'app_id': app_id, 'success': False, 'reason': 'request_failed'}

    entry = payload.get(str(app_id)) or {}

    if not entry.get('success'):
        # 지역 미판매·삭제된 앱 등 정상적으로 발생하는 케이스라 별도 예외 처리 없이 기록만 한다.
        return {'app_id': app_id, 'success': False, 'reason': 'api_success_false'}

    data = entry.get('data', {})

    # DLC/사운드트랙/데모는 리뷰 요약을 굳이 가져오지 않는다(요청 절약, 어차피 standardize에서 제외됨)
    summary = {}
    if data.get('type') == 'game':
        sleep_between_requests()
        summary = fetch_review_summary(app_id)

    return {
        'app_id': app_id,
        'success': True,
        'data': data,
        'review_summary': summary,
    }


def main() -> None:
    print_title('[2단계] 게임 상세 수집')

    targets = load_app_ids()
    done = load_done_app_ids()

    print(f'대상: {len(targets)}건 / 이미 수집: {len(done)}건')

    ok_count = 0
    fail_count = 0

    with DETAIL_RAW_PATH.open('a', encoding='utf-8') as raw_file:
        for index, row in enumerate(targets, start=1):
            app_id = row['app_id']

            if app_id in done:
                continue

            record = fetch_one(app_id)
            raw_file.write(json.dumps(record, ensure_ascii=False) + '\n')
            raw_file.flush()

            if record['success']:
                ok_count += 1
                name = record['data'].get('name', '')
                app_type = record['data'].get('type', '')
                print(f'{index}/{len(targets)} {app_id} OK  [{app_type}] {name}')
            else:
                fail_count += 1
                print(f'{index}/{len(targets)} {app_id} FAIL ({record["reason"]})')

            # 요청 간 1초 이상 대기 필수 - 없으면 429 이후 IP 단위로 잠시 막힌다(실측).
            sleep_between_requests()

    print_title('수집 결과')
    print(f'성공: {ok_count}건 / 실패: {fail_count}건')
    print(f'저장 위치: {DETAIL_RAW_PATH}')


if __name__ == '__main__':
    main()
