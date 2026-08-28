"""CLI 진입점 - 인자를 파싱해서 수집 파이프라인(src/collect/pipeline.py)을 호출한다."""
import argparse

from src.collect.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Steam 데이터 수집 파이프라인을 처음부터 끝까지 실행한다.')
    parser.add_argument(
        '--skip-crawl', action='store_true',
        help='app_id 목록 크롤링 건너뛰기 (data/raw/app_ids.csv가 이미 있을 때)',
    )
    parser.add_argument(
        '--skip-details', action='store_true',
        help='appdetails 수집 건너뛰기 (표준화만 다시 하고 싶을 때)',
    )
    parser.add_argument(
        '--skip-reviews', action='store_true',
        help='리뷰 수집 건너뛰기 (게임 데이터만 먼저 눈으로 확인하고 싶을 때)',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_pipeline(
        skip_crawl=args.skip_crawl,
        skip_details=args.skip_details,
        skip_reviews=args.skip_reviews,
    )


if __name__ == '__main__':
    main()
