import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from google import genai
from google.genai.types import EmbedContentConfig

from config import (
    EMBED_BATCH_SIZE,
    EMBED_WORKERS,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    GEMINI_API_KEY,
    MAX_RETRY,
    REQUEST_DELAY,
)

client = genai.Client(api_key=GEMINI_API_KEY)

def embed_text(
    text: str,
    task_type: str,
) -> list[float]:
    """
    text를 임베딩 하여 반환
    임베딩 실패하는 경우 config의 MAX_RETRY 만큼 재시도

    Args:
        text (str): 임베딩 할 텍스트
        task_type (str): EmbedContentConfig의 task_type
    """

    for attempt in range(1, MAX_RETRY + 1):
        try:
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=[text],
                config=EmbedContentConfig(
                    output_dimensionality=EMBEDDING_DIM,
                    task_type=task_type
                )
            )

            return response.embeddings[0].values

        except Exception:
            if attempt == MAX_RETRY:
                raise
            time.sleep(REQUEST_DELAY * attempt)


def embed_texts(
    texts: list[str],
    task_type: str,
) -> list[list[float]]:
    """
    text list를 임베딩 하여 반환
    Thread 사용하여 병렬 처리 (confing의 EMBED_WORKERS를 max_workers로 사용)
    Args:
        texts(list[str]): 임베딩 할 텍스트
        task_type(str): EmbedContentConfig의 task_type
    """

    results = [None] * len(texts)
    failed = []
    done = 0

    with ThreadPoolExecutor(
        max_workers=EMBED_WORKERS
    ) as executor:
        future_map = {
            executor.submit(
                embed_text,
                text,
                task_type,
            ): i
            for i, text in enumerate(texts)
        }

        for future in as_completed(future_map):
            i = future_map[future]
            try:
                results[i] = future.result()
            except Exception as e:  # noqa: BLE001
                failed.append(i)
                print(f'Exception Occured\n{e}')

            done += 1
            if done % EMBED_BATCH_SIZE == 0:
                print(f' Embedding {done}/{len(texts)}')

    if failed:
        raise RuntimeError(f'임베딩 {len(failed)}건 실패 (인덱스: {failed[:10]})')

    return results


if __name__ == '__main__':
    # 테스트
    import csv
    from itertools import islice

    from config import REVIEWS_PATH, print_title

    SAMPLE_SIZE = 20

    print_title('embedder 스모크 테스트')
    print(f'모델 {EMBEDDING_MODEL} / {EMBEDDING_DIM}차원 / 워커 {EMBED_WORKERS}개')

    # 5.6MB짜리 파일을 다 읽을 필요가 없어 앞에서 SAMPLE_SIZE건만 잘라 쓴다.
    with REVIEWS_PATH.open('r', encoding='utf-8-sig', newline='') as review_file:
        samples = [row['text'] for row in islice(csv.DictReader(review_file), SAMPLE_SIZE)]

    started = time.time()
    vectors = embed_texts(samples, 'RETRIEVAL_DOCUMENT')
    elapsed = time.time() - started

    empty_count = sum(1 for vector in vectors if not vector)
    dimensions = {len(vector) for vector in vectors if vector}

    print_title('결과')
    print(f'반환 개수 : {len(vectors)} / 입력 {len(samples)}건'
          f'  -> {"OK" if len(vectors) == len(samples) else "!!! 개수 불일치 !!!"}')
    print(f'빈 벡터   : {empty_count}건'
          f'  -> {"OK" if empty_count == 0 else "!!! 실패한 건이 있다 !!!"}')
    print(f'차원      : {dimensions or "없음"}'
          f'  -> {"OK" if dimensions == {EMBEDDING_DIM} else "!!! 차원 불일치 !!!"}')
    print(f'소요 시간 : {elapsed:.1f}초 ({elapsed / len(samples):.2f}초/건)')

    print()
    for sample, vector in zip(samples, vectors):
        print(f'첫 문장 : {sample[:60]}')
        print(f'첫 벡터 : {[round(value, 4) for value in vector[:5]]} ...')
