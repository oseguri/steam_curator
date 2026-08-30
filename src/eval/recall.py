"""Recall@5 평가. 이 프로젝트에서 가장 강한 숫자를 만드는 스크립트.

같은 문항으로 세 방식을 잰다.

    설명만    search_by_description  - 베이스라인. 상점 설명만 임베딩한 것
    리뷰집계  search_by_vibe         - 리뷰 1건=1문서, 게임별 상위3 평균
    실제경로  search_games           - 리뷰집계 + 임계값 미달 시 설명 폴백

앞의 둘은 임계값 0으로 돌린다. 게이팅이 아니라 '순위 품질'을 비교해야 하기 때문이다.
실제경로만 config 임계값을 그대로 써서 배포 상태의 성능을 본다.

    uv run python -m src.eval.recall
"""
import json
from pathlib import Path

from config import RECOMMEND_TOP_N, print_title
from src.agent.retrieval import search_by_description, search_by_vibe, search_games
from src.eval.questions import RECALL_QUESTIONS

# 측정 결과를 파일로 남긴다. Streamlit 평가 페이지가 이걸 읽는다.
# 화면에서 매번 다시 재면 발표 중 30초를 기다려야 하고, 숫자를 화면에
# 하드코딩하면 코드와 어긋난다.
RESULT_PATH = Path(__file__).resolve().parent / 'recall_result.json'


def evaluate(name: str, search) -> dict:
    """문항별로 상위 N개를 받아 정답과 대조한다."""
    rows = []
    for question, answers in RECALL_QUESTIONS:
        found = search(question)
        found_ids = [game['app_id'] for game in found][:RECOMMEND_TOP_N]
        hits = [app_id for app_id in found_ids if app_id in answers]
        rows.append({
            'question': question,
            'answers': answers,
            'found': found_ids,
            'hits': hits,
            # 정답이 하나라도 상위 N에 들었는가
            'hit': bool(hits),
            # 보여준 N개 중 정답 비율
            'precision': len(hits) / RECOMMEND_TOP_N,
            # 정답 중 상위 N에 든 비율. 정답이 N개보다 많으면 100%가 불가능하다
            'recall': len(hits) / len(answers),
        })
    total = len(rows)
    return {
        'name': name,
        'rows': rows,
        'hit_rate': sum(row['hit'] for row in rows) / total,
        'precision': sum(row['precision'] for row in rows) / total,
        'recall': sum(row['recall'] for row in rows) / total,
    }


def print_detail(result: dict) -> None:
    print_title(f'{result["name"]} - 문항별')
    print(f'{"질문":40} {"정답수":>5} {"적중":>4} {"P@5":>6}')
    print('-' * 62)
    for row in result['rows']:
        mark = ' ' if row['hit'] else 'X'
        print(f'{row["question"][:38]:40} {len(row["answers"]):5} {len(row["hits"]):3}{mark} {row["precision"]:6.2f}')


if __name__ == '__main__':
    results = [
        evaluate('설명만', lambda question: search_by_description(question, threshold=0.0)),
        evaluate('리뷰집계', lambda question: search_by_vibe(question, threshold=0.0)),
        evaluate('실제경로', lambda question: search_games(question)[0]),
    ]

    for result in results:
        print_detail(result)

    print_title(f'종합 ({len(RECALL_QUESTIONS)}문항, 상위 {RECOMMEND_TOP_N}개 기준)')
    print(f'{"방식":10} {"Hit@5":>8} {"P@5":>8} {"R@5":>8}')
    print('-' * 38)
    for result in results:
        print(f'{result["name"]:10} {result["hit_rate"]:8.3f} {result["precision"]:8.3f} {result["recall"]:8.3f}')

    print()
    print('Hit@5 : 정답이 하나라도 상위 5개에 든 문항 비율')
    print('P@5   : 보여준 5개 중 정답 비율')
    print('R@5   : 정답 중 상위 5개에 든 비율 (정답이 5개보다 많으면 1.0이 불가능)')

    RESULT_PATH.write_text(
        json.dumps(
            {
                'summary': [
                    {
                        'name': result['name'],
                        'hit_rate': result['hit_rate'],
                        'precision': result['precision'],
                        'recall': result['recall'],
                    }
                    for result in results
                ],
                'per_question': [
                    {
                        'question': row['question'],
                        'answer_count': len(row['answers']),
                        **{
                            result['name']: result['rows'][index]['precision']
                            for result in results
                        },
                    }
                    for index, row in enumerate(results[0]['rows'])
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )
    print(f'\n결과 저장: {RESULT_PATH}')

    print_title('설명만 -> 리뷰집계로 뒤집힌 문항')
    baseline, aggregated = results[0], results[1]
    for base_row, agg_row in zip(baseline['rows'], aggregated['rows']):
        if base_row['precision'] != agg_row['precision']:
            arrow = '개선' if agg_row['precision'] > base_row['precision'] else '악화'
            print(f'  [{arrow}] {base_row["question"][:34]:36} '
                  f'P@5 {base_row["precision"]:.2f} -> {agg_row["precision"]:.2f}')
