"""전체 수집 파이프라인을 함수 하나로 묶는다.

crawl_list -> fetch_details -> standardize(games.csv 확보) -> fetch_reviews -> standardize(reviews.csv까지)

fetch_reviews는 games.csv에서 리뷰 많은 상위 N개를 골라 대상으로 삼기 때문에
반드시 그 전에 standardize를 한 번 돌려 games.csv를 만들어둬야 한다.

각 단계 스크립트는 이미 수집한 app_id는 건너뛰므로(멱등) 중간에 끊겨도 다시 실행하면 이어서 받는다.
"""
from config import print_title
from src.collect import crawl_list, fetch_details, fetch_reviews, standardize


def run_pipeline(
    skip_crawl: bool = False,
    skip_details: bool = False,
    skip_reviews: bool = False,
) -> None:
    if not skip_crawl:
        crawl_list.main()

    if not skip_details:
        fetch_details.main()

    standardize.main()

    if not skip_reviews:
        fetch_reviews.main()
        standardize.main()

    print_title('전체 파이프라인 완료')


if __name__ == '__main__':
    run_pipeline()
