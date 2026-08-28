"""[4단계] raw -> 표준화 + 품질 검증.

raw는 문자열/원본 JSON 그대로 두고, 타입 변환은 오직 이 단계에서만 한다.
파싱을 고쳐야 할 때 재수집이 필요 없도록 하기 위한 3차 프로젝트 원칙.

Game/ReviewChunk 모델(model.py)을 거쳐서 만들기 때문에, 필드 타입이 안 맞으면
CSV에 잘못된 값이 조용히 깔리는 대신 여기서 바로 예외로 드러난다.
"""
import csv
import html
import json
import re
from collections import Counter

from pydantic import ValidationError

from config import (
    DETAIL_RAW_PATH,
    GAMES_PATH,
    MAX_SAME_CHAR_RATIO,
    MIN_DESCRIPTION_LENGTH,
    MIN_REVIEW_LENGTH,
    QUALITY_PATH,
    REVIEW_CHUNK_SIZE,
    REVIEW_RAW_PATH,
    REVIEWS_PATH,
    print_title,
)
from model import GAME_CSV_FIELDS, GENRE_ENUM, REVIEW_CSV_FIELDS, Game, ReviewChunk

TAG_PATTERN = re.compile(r'<[^>]+>')
SENTENCE_SPLIT_PATTERN = re.compile(r'(?<=[.!?。])\s+')

PLAYER_MODE_KEYWORDS = {
    '싱글 플레이어': ['싱글 플레이어'],
    '멀티플레이어': ['멀티플레이어', 'PvP', 'MMO'],
    '협동': ['협동', 'Co-op'],
    '온라인 협동': ['온라인 협동'],
    'PvP': ['PvP'],
}


# ==================================
# 공통 변환
# ==================================
def clean_text(value: str | None) -> str:
    if not value:
        return ''
    return TAG_PATTERN.sub(' ', html.unescape(value)).replace('\r', ' ').replace('\n', ' ').strip()


def to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_languages(raw: str | None) -> int:
    """'한국어, 영어<strong>*</strong>...' 형태에서 언어 개수만 센다."""
    text = clean_text(raw)
    if not text:
        return 0
    parts = [part.strip() for part in text.split(',') if part.strip()]
    return len(parts)


def parse_player_modes(categories: list[str]) -> list[str]:
    modes = []
    joined = ' '.join(categories)
    for mode, keywords in PLAYER_MODE_KEYWORDS.items():
        if any(keyword in joined for keyword in keywords):
            modes.append(mode)
    return modes


# ==================================
# 게임 표준화
# ==================================
def standardize_game(record: dict) -> tuple[Game | None, list[tuple[str, str]]]:
    """(Game 또는 None, [(rule_name, detail), ...]) 를 돌려준다.

    Game 생성 자체가 pydantic ValidationError를 낼 수 있어(타입 자체가 잘못된 경우)
    이 경우도 quality_issues에 남기고 해당 게임만 건너뛴다.
    """
    data = record.get('data') or {}

    if data.get('type') != 'game':
        return None, []

    summary = record.get('review_summary') or {}
    price_info = data.get('price_overview') or {}
    is_free = bool(data.get('is_free'))

    genres = [item.get('description', '') for item in (data.get('genres') or []) if item.get('description')]
    categories = [
        item.get('description', '') for item in (data.get('categories') or []) if item.get('description')
    ]

    total_positive = to_int(summary.get('total_positive'))
    total_negative = to_int(summary.get('total_negative'))
    total_reviews = to_int(summary.get('total_reviews'), total_positive + total_negative)

    positive_ratio = 0.0
    if total_reviews > 0:
        positive_ratio = round(total_positive / total_reviews, 4)

    # 가격은 원 단위 정수로. price_overview는 100배 정수(센트 방식)로 온다.
    # (3차 프로젝트에서 정규식 오타로 모든 가격이 0으로 나온 적이 있는 자리라 여기가 맞는지 눈으로 확인할 것)
    initial_price = to_int(price_info.get('initial')) // 100
    final_price = to_int(price_info.get('final')) // 100

    app_id = str(record.get('app_id', ''))

    try:
        game = Game(
            app_id=app_id,
            name=(data.get('name') or '').strip(),
            is_free=is_free,
            price=0 if is_free else initial_price,
            final_price=0 if is_free else final_price,
            discount_percent=to_int(price_info.get('discount_percent')),
            review_score=to_int(summary.get('review_score')),
            review_score_desc=(summary.get('review_score_desc') or '').strip(),
            total_reviews=total_reviews,
            positive_ratio=positive_ratio,
            genres=genres,
            categories=categories,
            player_modes=parse_player_modes(categories),
            language_count=parse_languages(data.get('supported_languages')),
            release_date=((data.get('release_date') or {}).get('date') or '').strip(),
            developers=data.get('developers') or [],
            publishers=data.get('publishers') or [],
            header_image=data.get('header_image') or '',
            short_description=clean_text(data.get('short_description')),
        )
    except ValidationError as error:
        detail = '; '.join(f'{".".join(str(p) for p in e["loc"])}: {e["msg"]}' for e in error.errors())
        return None, [('INVALID_FIELD', detail)]

    return game, []


# ==================================
# 품질 검증
# ==================================
def check_quality(games: list[Game]) -> tuple[list[Game], list[dict]]:
    issues = []
    seen_app_ids = set()
    valid = []

    for game in games:
        game_issues = []

        if not game.app_id:
            game_issues.append(('REQUIRED_APPID', 'app_id 누락'))
        if not game.name:
            game_issues.append(('REQUIRED_NAME', '게임명 누락'))
        if game.app_id in seen_app_ids:
            game_issues.append(('DUPLICATE_APPID', f'중복 app_id: {game.app_id}'))
        if not 0 <= game.discount_percent <= 100:
            game_issues.append(('DISCOUNT_OUT_OF_RANGE', f'할인율 {game.discount_percent}'))

        unmatched = [genre for genre in game.genres if genre and genre not in GENRE_ENUM]
        if unmatched:
            game_issues.append(('UNMATCHED_GENRE', ','.join(unmatched)))

        # RAG용 규칙: 설명이 너무 짧으면 임베딩 품질이 나빠진다
        if len(game.short_description) < MIN_DESCRIPTION_LENGTH:
            game_issues.append(('DESCRIPTION_TOO_SHORT', f'{len(game.short_description)}자'))

        seen_app_ids.add(game.app_id)

        blocking = {'REQUIRED_APPID', 'REQUIRED_NAME', 'DUPLICATE_APPID'}
        for rule, detail in game_issues:
            issues.append({
                'app_id': game.app_id,
                'name': game.name,
                'rule_name': rule,
                'detail': detail,
            })

        if any(rule in blocking for rule, _ in game_issues):
            continue

        valid.append(game)

    return valid, issues


# ==================================
# 리뷰 전처리 + 청킹
# ==================================
def same_char_ratio(text: str) -> float:
    """가장 많이 나온 글자 하나의 비율. 'ㅋㅋㅋㅋㅋ' 도배나 '=====' ASCII 아트를 잡는다."""
    if not text:
        return 0.0
    most_common_count = Counter(text).most_common(1)[0][1]
    return most_common_count / len(text)


def split_sentences(text: str) -> list[str]:
    return [sentence for sentence in SENTENCE_SPLIT_PATTERN.split(text) if sentence.strip()]


def chunk_by_sentence(text: str, max_size: int) -> list[str]:
    """1,000자 넘는 리뷰만 문장 경계에서 나눈다.

    고정 길이로 잘라내면 "근데 최적화가"처럼 문장 중간에서 끊겨 문맥이 깨진다.
    문장 하나가 max_size보다 긴 극단적인 경우는 억지로 자르지 않고 그대로 한 청크로 둔다.
    """
    if len(text) <= max_size:
        return [text] if text else []

    chunks = []
    current = ''

    for sentence in split_sentences(text):
        candidate = f'{current} {sentence}'.strip() if current else sentence

        if len(candidate) > max_size and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks


def standardize_reviews(record: dict) -> list[ReviewChunk]:
    rows = []
    app_id = str(record.get('app_id', ''))
    name = record.get('name', '')

    for bucket, voted_up in (('positive', True), ('negative', False)):
        for review in record.get(bucket) or []:
            text = clean_text(review.get('review'))

            if len(text) < MIN_REVIEW_LENGTH:
                continue
            if same_char_ratio(text) > MAX_SAME_CHAR_RATIO:
                continue

            author = review.get('author') or {}
            playtime = round(to_int(author.get('playtime_forever')) / 60, 1)
            review_id = str(review.get('recommendationid', ''))

            for chunk_index, chunk in enumerate(chunk_by_sentence(text, REVIEW_CHUNK_SIZE)):
                rows.append(ReviewChunk(
                    chunk_id=f'{app_id}-{review_id}-{chunk_index}',
                    review_id=review_id,
                    app_id=app_id,
                    name=name,
                    voted_up=voted_up,
                    playtime_hours=playtime,
                    votes_up=to_int(review.get('votes_up')),
                    chunk_index=chunk_index,
                    text=chunk,
                ))

    return rows


# ==================================
# IO
# ==================================
def read_jsonl(path) -> list[dict]:
    if not path.exists():
        return []

    records = []
    with path.open('r', encoding='utf-8') as raw_file:
        for line in raw_file:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return records


def write_csv(path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open('w', encoding='utf-8-sig', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    print_title('[4단계] 표준화 + 품질 검증')

    detail_records = read_jsonl(DETAIL_RAW_PATH)
    print(f'detail raw: {len(detail_records)}건')

    games = []
    invalid_issues = []
    skipped = 0

    for record in detail_records:
        if not record.get('success'):
            skipped += 1
            continue

        game, issues = standardize_game(record)

        if game is None:
            if issues:
                invalid_issues.append({
                    'app_id': str(record.get('app_id', '')),
                    'name': (record.get('data') or {}).get('name', ''),
                    'rule_name': issues[0][0],
                    'detail': issues[0][1],
                })
            else:
                skipped += 1  # type != 'game' (DLC/사운드트랙/데모)
            continue

        games.append(game)

    valid_games, quality_issues = check_quality(games)
    all_issues = invalid_issues + quality_issues

    write_csv(GAMES_PATH, GAME_CSV_FIELDS, [game.to_csv_row() for game in valid_games])
    write_csv(QUALITY_PATH, ['app_id', 'name', 'rule_name', 'detail'], all_issues)

    print(f'game 타입 아님/요청 실패로 제외: {skipped}건')
    print(f'표준화: {len(games)}건 -> 정상 {len(valid_games)}건')
    print(f'품질 이슈: {len(all_issues)}건 -> {QUALITY_PATH.name}')

    review_records = read_jsonl(REVIEW_RAW_PATH)
    if review_records:
        review_rows: list[ReviewChunk] = []
        for record in review_records:
            review_rows.extend(standardize_reviews(record))

        write_csv(REVIEWS_PATH, REVIEW_CSV_FIELDS, [row.to_csv_row() for row in review_rows])
        print(f'리뷰 청크: {len(review_rows)}건 -> {REVIEWS_PATH.name}')
    else:
        print('리뷰 raw가 없습니다. fetch_reviews.py를 먼저 실행하세요.')


if __name__ == '__main__':
    main()
