"""index_reviews.py"""
from chromadb.api.models.Collection import Collection

from config import (
    REVIEW_COLLECTION,
    print_title,
)
from src.index.chroma_store import (
    add_in_batches,
    reset_collection,
    to_list,
)
from src.index.embedder import embed_texts
from src.loaders import (
    REVIEW_COLUMNS,
    load_games,
    load_reviews,
    to_records,
)

JOIN_COLUMNS = [
    'app_id', 'final_price', 'is_free',
    'review_score', 'total_reviews', 'genres', 'player_modes'
]

def build_metadata(record: dict) -> dict:
    """chromaDB 에 넣을 review metadata 반환"""
    return {
        'review_id': record['review_id'],
        'app_id': record['app_id'],
        'name': record['name'],
        'voted_up': record['voted_up'],
        'playtime_hours': record['playtime_hours'],
        'votes_up': record['votes_up'],
        'final_price': record['final_price'],
        'is_free': record['is_free'],
        'review_score': record['review_score'],
        'total_reviews': record['total_reviews'],
        'genres': to_list(record['genres']),
        'player_modes': to_list(record['player_modes']),
    }

def index_reviews(limit: int | None = None) -> Collection:
    """
    reviews를 chromaDB에 저장
    """
    reviews = load_reviews().merge(
        load_games()[JOIN_COLUMNS],
        on='app_id',
        how='left',
    )

    if limit:
        reviews = reviews.head(n=limit)

    records = to_records(
        frame=reviews,
        limit=len(reviews),
        columns=REVIEW_COLUMNS + JOIN_COLUMNS[1:],
    )

    ids = [record['chunk_id'] for record in records]
    documents = [record['text'] for record in records]
    metadatas = [build_metadata(record) for record in records]
    embeddings = embed_texts(
        texts=documents,
        task_type='RETRIEVAL_DOCUMENT'
    )

    collection = reset_collection(REVIEW_COLLECTION)
    add_in_batches(
        collection=collection,
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    return collection


if __name__ == '__main__':
    import sys

    from src.index.embedder import embed_text

    # 전체 8,402건은 약 7분 걸린다. 인자를 주면 그만큼만 돌려 먼저 확인한다
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    print_title(f'리뷰 인덱싱 ({limit or "전체"}건)')
    collection = index_reviews(limit)

    print_title('검증')
    expected = limit or len(load_reviews())
    count = collection.count()
    print(f'count : {count} / 입력 {expected}'
          f'  -> {"OK" if count == expected else "!!! 개수 불일치 !!!"}')

    question = '스토리가 감동적이고 눈물나는 게임'
    question_vector = embed_text(question, 'RETRIEVAL_QUERY')

    found = collection.query(query_embeddings=[question_vector], n_results=3)
    print(f'\n"{question}" 상위 3개 리뷰')
    for metadata, document, distance in zip(
        found['metadatas'][0], found['documents'][0], found['distances'][0]
    ):
        print(f'  {distance:.4f}  [{metadata["name"]}] {document[:60]}')

    cheap = collection.query(
        query_embeddings=[question_vector],
        n_results=3,
        where={'final_price': {'$lte': 30000}},
    )
    print('\n같은 질문 + 3만원 이하 필터')
    for metadata, distance in zip(cheap['metadatas'][0], cheap['distances'][0]):
        print(f'  {distance:.4f}  [{metadata["name"]}] {metadata["final_price"]}원')
    print(
        f'  -> {
            "필터가 결과를 바꿨다 OK"
            if cheap["ids"][0] != found["ids"][0]
            else "결과 동일 (원래 다 3만원 이하일 수 있다)"
        }'
    )
