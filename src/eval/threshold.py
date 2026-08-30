"""임계값 확정용 분포 측정.

관련/무관 질문의 점수 분포를 찍고, 후보 임계값을 훑어 가장 잘 가르는 구간을 찾는다.
config.py의 VIBE_THRESHOLD / REVIEW_THRESHOLD / DESCRIPTION_THRESHOLD는
측정 전 추정치라 이 스크립트 결과로 대체한다.

    uv run python -m src.eval.threshold
"""
import statistics

from config import (
    DESCRIPTION_THRESHOLD,
    REVIEW_THRESHOLD,
    VIBE_THRESHOLD,
    print_title,
)
from src.agent.retrieval import (
    search_by_description,
    search_by_vibe,
    search_reviews_by_game,
)
from src.eval.questions import REVIEW_QUESTIONS, THRESHOLD_QUESTIONS

SWEEP_START, SWEEP_END, SWEEP_STEP = 0.35, 0.85, 0.01


def collect_vibe() -> list[tuple[str, float, bool]]:
    """추천 경로: 질문별 1위 게임 점수."""
    rows = []
    for question, should_pass in THRESHOLD_QUESTIONS:
        games = search_by_vibe(question, threshold=0.0)
        rows.append((question, games[0]['score'] if games else 0.0, should_pass))
    return rows


def collect_description() -> list[tuple[str, float, bool]]:
    """설명 폴백 경로: 같은 질문으로 1위 게임 점수."""
    rows = []
    for question, should_pass in THRESHOLD_QUESTIONS:
        games = search_by_description(question, threshold=0.0)
        rows.append((question, games[0]['score'] if games else 0.0, should_pass))
    return rows


def collect_review() -> list[tuple[str, float, bool]]:
    """리뷰 RAG 경로: 근거 후보 중 최고 유사도."""
    rows = []
    for app_id, question, should_pass in REVIEW_QUESTIONS:
        found = search_reviews_by_game(app_id, question, threshold=0.0)
        rows.append((f'{app_id} / {question}', found['best_similarity'], should_pass))
    return rows


def sweep(rows: list[tuple[str, float, bool]]) -> list[tuple[float, int]]:
    """후보 임계값별 정답 개수. 관련은 통과해야, 무관은 막혀야 정답이다."""
    results = []
    value = SWEEP_START
    while value <= SWEEP_END + 1e-9:
        correct = sum(1 for _, score, should_pass in rows
                      if (score >= value) == should_pass)
        results.append((round(value, 2), correct))
        value += SWEEP_STEP
    return results


def report(label: str, rows: list[tuple[str, float, bool]], current: float) -> None:
    print_title(f'{label}  (현재 config 값 {current})')

    for name, score, should_pass in sorted(rows, key=lambda row: -row[1]):
        kind = '관련' if should_pass else '무관'
        mark = '통과' if score >= current else '미달'
        wrong = '  <- 현재값에서 오분류' if (score >= current) != should_pass else ''
        print(f'  [{kind}] {mark} {score:.4f}  {name[:44]}{wrong}')

    relevant = [score for _, score, should_pass in rows if should_pass]
    irrelevant = [score for _, score, should_pass in rows if not should_pass]
    print()
    print(f'  관련 {len(relevant)}건  최저 {min(relevant):.4f} / 중앙 {statistics.median(relevant):.4f} / 최고 {max(relevant):.4f}')
    print(f'  무관 {len(irrelevant)}건  최저 {min(irrelevant):.4f} / 중앙 {statistics.median(irrelevant):.4f} / 최고 {max(irrelevant):.4f}')

    gap = min(relevant) - max(irrelevant)
    if gap > 0:
        print(f'  겹침 없음. 빈 구간 {gap:.4f}  ({max(irrelevant):.4f} ~ {min(relevant):.4f})')
    else:
        print(f'  구간이 {-gap:.4f}만큼 겹친다. 단일 임계값으로 완전히 가를 수 없다')

    scores = sweep(rows)
    best = max(count for _, count in scores)
    winners = [value for value, count in scores if count == best]
    print()
    print(f'  임계값 훑기: 최고 정답 {best}/{len(rows)}건')
    print(f'    최적 구간 {min(winners):.2f} ~ {max(winners):.2f}')
    print(f'    권장값 {statistics.median(winners):.2f}  (구간 중앙)')
    current_correct = sum(1 for _, score, should_pass in rows
                          if (score >= current) == should_pass)
    print(f'    현재값 {current} -> {current_correct}/{len(rows)}건')


if __name__ == '__main__':
    report('추천 경로 search_by_vibe', collect_vibe(), VIBE_THRESHOLD)
    report('설명 폴백 search_by_description', collect_description(), DESCRIPTION_THRESHOLD)
    report('리뷰 RAG search_reviews_by_game', collect_review(), REVIEW_THRESHOLD)
