import pandas as pd
from chromadb.api.models.Collection import Collection

from config import (
    GAME_COLLECTION,
    print_title,
)
from src.index.chroma_store import reset_collection, to_list
from src.index.embedder import embed_texts
from src.loaders import (
    load_games,
    to_records,
)


def build_document(row: pd.Series) -> str:
    """임베딩할 문서를 게임 games row로 부터 생성 후 반환"""
    genres = row['genres'].replace('|', ', ')
    player_modes = row['player_modes'].replace('|', ', ')
    return f"{row['name']}. {genres}. {player_modes}. {row['short_description']}"

def build_metadata(record: dict) -> dict:
    """chromaDB 에 넣을 game metadata 반환"""
    metadata = dict(record)
    metadata['genres'] = to_list(record['genres'])
    metadata['player_modes'] = to_list(record['player_modes'])
    return metadata

def index_games(limit: int | None = None) -> Collection:
    """
    games를 chromaDB에 저장
    """
    games = load_games()
    if limit:
        games = games.head(n=limit)

    records = to_records(games, limit=len(games))

    ids = [record['app_id'] for record in records]
    documents = [build_document(row) for _, row in games.iterrows()]
    metadatas = [build_metadata(record) for record in records]
    embeddings = embed_texts(
        texts=documents,
        task_type='RETRIEVAL_DOCUMENT'
    )

    collection = reset_collection(GAME_COLLECTION)
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    return collection


if __name__ == '__main__':
    import sys

    from src.index.embedder import embed_text

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    print_title(f'게임 인덱싱 ({limit or "전체"}건)')
    collection = index_games(limit)

    print_title('검증')
    expected = limit or len(load_games())
    count = collection.count()
    print(f'count : {count} / 입력 {expected}'
          f'  -> {"OK" if count == expected else "!!! 개수 불일치 !!!"}')

    # 의미 검색이 실제로 되는지. distance가 1.0에 가까우면 벡터가 잘못 들어간 것이다
    question = '마블 게임'
    found = collection.query(
        query_embeddings=[embed_text(question, 'RETRIEVAL_QUERY')],
        n_results=3,
    )
    print(f'\n"{question}" 상위 3개')
    for metadata, distance in zip(found['metadatas'][0], found['distances'][0]):
        print(f'  {distance:.4f}  {metadata["name"]}')

    # 장르 빈 4건이 유령 리스트를 물려받지 않았는지 (전체 인덱싱일 때만 의미 있다)
    empty = collection.get(where={'genres': ''})
    action = collection.get(where={'genres': {'$contains': '액션'}})
    print(f'\ngenres 빈 게임 : {len(empty["ids"])}건 {[m["name"] for m in empty["metadatas"]]}')
    print(f'$contains 액션 : {len(action["ids"])}건')
