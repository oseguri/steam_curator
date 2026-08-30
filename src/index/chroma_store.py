import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.errors import NotFoundError

from config import CHROMA_DIR

client = chromadb.PersistentClient(path=CHROMA_DIR)
COLLECTION_METADATA = {
    'hnsw': {
        'space': 'cosine'
    }
}

def to_list(value: str) -> list[str] | str:
    """파이프 문자열 ex)text1|text2|text3 를 리스트로, 값이 없으면 ''

    Chroma 제약 때문에 존재하는 함수라 여기에 둔다.
    빈 리스트 []는 거부당하고, 키를 아예 빼면 이전 인덱싱의 리스트가
    같은 id에 되살아난다(chromadb 1.5.9). 그래서 값이 없어도 ''를 채운다.
    """
    if not value:
        return ''
    return [text.strip() for text in value.split('|')]


def reset_collection(name: str) -> Collection:
    """chromadb에서 name에 해당하는 컬렉션을 지우고 새로 만들어서 반환"""

    try:
        client.delete_collection(name)
    except NotFoundError:
        pass

    return client.get_or_create_collection(
        name=name,
        configuration=COLLECTION_METADATA,
        embedding_function=None,
    )

def get_collection(name: str) -> Collection:
    """chromadb에서 name에 해당하는 컬렉션을 반환"""
    return client.get_collection(
        name=name,
        embedding_function=None,
    )

if __name__ == '__main__':
    from config import EMBEDDING_DIM, print_title
    TEST_NAME = 'test_smoke'

    vector_a = [1.0] + [0.0] * (EMBEDDING_DIM - 1)
    vector_b = [0.0] * (EMBEDDING_DIM - 1) + [1.0]

    TEST_VALUE = {
        'ids': ['a', 'b'],
        'embeddings': [vector_a, vector_b],
        'documents': ['첫번째 문서', '두번째 문서'],
        'metadatas': [{'genres': ['액션', '인디']}, {'genres': ['RPG']}],
    }

    print_title('chroma_store smoke test')
    # 없을때 collection reset
    collection = reset_collection(TEST_NAME)
    print(f'1회차 : count={collection.count()} -> OK')
    collection.add(**TEST_VALUE)
    collection = reset_collection(TEST_NAME)
    count = collection.count()
    print(f'2회차(있을 때) : count={count}'
          f'  -> {"OK" if count == 0 else "!!! 이전 데이터가 남았다 !!!"}'
    )

    collection.add(**TEST_VALUE)
    count = collection.count()
    print(f'add 2건: count={count}'
            f'{"OK" if count == 2 else "개수 불일치"}'
    )

    # 3) 거리 함수가 cosine인가 - 자기 자신 0.0, 직교 1.0. L2면 0.0 / 1.414가 나온다
    result = collection.query(query_embeddings=[vector_a], n_results=2)
    distances = result['distances'][0]
    is_cosine = abs(distances[0]) < 0.01 and abs(distances[1] - 1.0) < 0.01
    print(f'query distance : {[round(d, 4) for d in distances]}'
          f'  -> {"OK (cosine)" if is_cosine else "!!! cosine이 아니다 !!!"}')
    print(f'  최근접 문서  : {result["documents"][0][0]}'
          f'  -> {"OK" if result["ids"][0][0] == "a" else "!!! 순서가 이상하다 !!!"}')

    # 4) 조회 경로가 같은 데이터를 다른 모듈에서 부른다)
    reopened = get_collection(TEST_NAME)
    print(f'get_collection : count={reopened.count()}'
          f'  -> {"OK" if reopened.count() == 2 else "!!! 다른 컬렉션을 보고 있다 !!!"}')

    # 5) 장르 리스트 필터 - index_games.py에서 쓸 형태를 미리 확인해둔다
    filtered = collection.get(where={'genres': {'$contains': '액션'}})
    print(f'$contains 액션 : ids={filtered["ids"]}'
          f'  -> {"OK" if filtered["ids"] == ["a"] else "!!! 필터가 안 걸린다 !!!"}')

    client.delete_collection(TEST_NAME)
    print(f'\n정리 완료. 남은 컬렉션: {[c.name for c in client.list_collections()]}')

