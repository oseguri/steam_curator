"""retrieval.py"""
from collections import defaultdict

from chromadb.api.types import QueryResult

from config import (
    DESCRIPTION_THRESHOLD,
    GAME_COLLECTION,
    RECOMMEND_TOP_N,
    REVIEW_COLLECTION,
    REVIEW_SEARCH_K,
    TOP_REVIEWS_PER_GAME,
    VIBE_THRESHOLD,
)
from src.index.chroma_store import get_collection
from src.index.embedder import embed_text


def score_game(similarities: list[float]) -> float:
    """게임 점수 = 상위 TOP_REVIEWS_PER_GAME 유사도 평균"""
    top = sorted(similarities, reverse=True)[:TOP_REVIEWS_PER_GAME]
    padded = top + [0.0] * (TOP_REVIEWS_PER_GAME - len(top))
    return sum(padded) / TOP_REVIEWS_PER_GAME

def search_by_vibe(
    query: str,
    filters: dict | None = None,
    threshold: float = VIBE_THRESHOLD,
) -> list[dict]:
    """취향 질문으로 리뷰를 검색하고 게임 단위로 집계해 상위 N개를 반환한다."""
    embed_query = embed_text(
        text=query,
        task_type="RETRIEVAL_QUERY",
    )

    collection = get_collection(REVIEW_COLLECTION)

    results: QueryResult = collection.query(
        query_embeddings=[embed_query],
        n_results=REVIEW_SEARCH_K,
        where=filters,
    )

    matches = zip(
        results['documents'][0],
        results['distances'][0],
        results['metadatas'][0],
    )


    by_game: dict[str, list[dict]] = defaultdict(list)
    for document, distance, metadata in matches:
        by_game[metadata['app_id']].append(
            {
                'text': document,
                'similarity': 1 - distance,
                'voted_up': metadata['voted_up'],
                'playtime_hours': metadata['playtime_hours'],
                'name': metadata['name'],
                'final_price': metadata['final_price'],
            }
        )

    ranked = []
    for app_id, reviews in by_game.items():
        reviews.sort(key=lambda review: review['similarity'], reverse=True)
        ranked.append(
            {
                'app_id': app_id,
                'name': reviews[0]['name'],
                'final_price': reviews[0]['final_price'],
                'score': score_game([review['similarity'] for review in reviews]),
                'match_count': len(reviews),
                'evidence': [
                    {
                        key: review[key]
                        for key in ('text', 'similarity', 'voted_up', 'playtime_hours')
                    }
                    for review in reviews[:TOP_REVIEWS_PER_GAME]
                ]
            }
        )

    passed = [game for game in ranked if game['score'] >= threshold]

    return sorted(
        passed,
        key=lambda game: game['score'],
        reverse=True
    )[:RECOMMEND_TOP_N]

def search_by_description(
    query: str,
    filters: dict | None = None,
    threshold: float = DESCRIPTION_THRESHOLD,
) -> list[dict]:
    """게임 설명 컬렉션에서 검색(리뷰가 없는 게임 검색에 사용)"""
    results: QueryResult = get_collection(GAME_COLLECTION).query(
        query_embeddings=[embed_text(query, 'RETRIEVAL_QUERY')],
        n_results=RECOMMEND_TOP_N,
        where=filters,
    )

    matches = zip(results['distances'][0], results['metadatas'][0])

    ranked = [
        {
            'app_id': metadata['app_id'],
            'name': metadata['name'],
            'final_price': metadata['final_price'],
            'score': 1 - distance,
            'match_count': 0,
            'evidence': [],
        }
        for distance, metadata in matches
    ]

    return [game for game in ranked if game['score'] >= threshold]

def search_games(
    query: str,
    filters=None,
) -> tuple[list[dict], str]:
    """game 검색, vibe search 먼저 시도 후 리뷰가 없는 경우 description search"""
    result = search_by_vibe(query=query, filters=filters)
    if result:
        return result, 'search_by_vibe'
    return search_by_description(query=query, filters=filters), 'search_by_description'

if __name__ == '__main__':
    import sys

    from config import print_title

    # 임계값을 인자로 받고 아닌 경우 config의 VIBE_THRESHOLD를 사용
    threshold = float(sys.argv[1]) if len(sys.argv) > 1 else VIBE_THRESHOLD

    # (질문, 추천이 나와야 하는가)
    QUESTIONS = [
        ('스토리가 감동적이고 눈물나는 게임', True),
        ('혼자 조용히 힐링되는 게임', True),
        ('핵 때문에 짜증나는 게임', True),
        ('친구랑 협동해서 좀비 잡는 게임', True),
        ('난이도가 극악이라 계속 죽는 게임', True),
        ('그래픽이 아름답고 풍경이 좋은 게임', True),
        ('세탁기 고치는 법', False),
        ('오늘 저녁 뭐 먹지', False),
        ('파이썬 문법 알려줘', False),
    ]

    print_title(f'search_by_vibe  임계값 {threshold}')

    relevant_scores, irrelevant_scores = [], []
    for question, should_pass in QUESTIONS:
        candidates = search_by_vibe(question, threshold=0.0)
        passed = [game for game in candidates if game['score'] >= threshold]

        verdict = 'OK' if bool(passed) == should_pass else '!!! 기대와 다름 !!!'
        label = '관련' if should_pass else '무관'
        print(f'\n[{label}] {question}  ->  통과 {len(passed)}/{len(candidates)}  {verdict}')
        for game in candidates:
            mark = '  통과' if game['score'] >= threshold else '  미달'
            print(f'{mark} {game["score"]:.4f} ({game["match_count"]:2}건) {game["name"]}')

        top = candidates[0]['score'] if candidates else 0.0
        (relevant_scores if should_pass else irrelevant_scores).append(top)

    print_title('임계값 판단 근거')
    print(f'관련 질문 최고점 최저값 : {min(relevant_scores):.4f}')
    print(f'무관 질문 최고점 최대값 : {max(irrelevant_scores):.4f}')
    gap = min(relevant_scores) - max(irrelevant_scores)
    if gap > 0:
        print(f'빈 구간 {gap:.4f}  ->  임계값 후보 {max(irrelevant_scores):.2f} ~ {min(relevant_scores):.2f}')
    else:
        print(f'구간이 {-gap:.4f}만큼 겹친다 -> 단일 임계값으로 못 가른다')

    print_title('근거 리뷰 (1번 질문 1위 게임)')
    top_game = search_by_vibe(QUESTIONS[0][0], threshold=0.0)[0]
    print(f'{top_game["name"]}  점수 {top_game["score"]:.4f}  매칭 {top_game["match_count"]}건')
    for evidence in top_game['evidence']:
        flag = '긍정' if evidence['voted_up'] else '부정'
        print(f'  {evidence["similarity"]:.4f} [{flag} {evidence["playtime_hours"]}h] {evidence["text"][:70]}')
