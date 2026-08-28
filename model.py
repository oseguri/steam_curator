"""데이터 인터페이스 - 수집 → 표준화 → 인덱싱 → 에이전트가 공유하는 스키마.

pandas·CSV·Chroma는 타입을 강제하지 않아서 단계 사이에 필드가 은근히 어긋난다
(예: standardize.py가 만드는 컬럼명과 index_games.py가 읽는 컬럼명이 따로 놀거나,
장르 enum이 config와 agent에서 서로 다르게 정의되는 식). 이 파일을 거치면
필드 이름/타입 불일치를 코드 작성 시점에 바로 잡을 수 있다.

역할 분담:
- Game / ReviewChunk: standardize.py가 만들고 games.csv / reviews.csv에 쓰는 표준화 결과 1행
- *VectorMetadata: index_games.py / index_reviews.py가 Chroma에 넣는 메타데이터
  (Chroma 메타데이터는 str/int/float/bool만 허용 - 리스트・None 불가라 별도 모델로 분리)
- ReviewMatch / GameVibeScore: retrieval.py(리뷰 집계 기반 취향 검색)가 만들고
  tools.py(search_games_by_vibe)가 받는 결과 계약

LLM 함수 호출 인자 검증(pydantic strict, Literal enum)은 이 파일이 아니라
src/agent/schemas.py에서 별도로 정의한다. 이 파일은 어디까지나 "우리 데이터"의 모양이다.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ==================================
# 기준정보 (genres/player_modes 어휘를 한 곳에서만 정의)
# ==================================
GENRE_ENUM = [
    '액션', '어드벤처', '캐주얼', '인디', '대규모 멀티플레이어',
    '레이싱', 'RPG', '시뮬레이션', '스포츠', '전략',
    '무료 플레이', '앞서 해보기', '고어', '성인용 콘텐츠', '유틸리티',
]
PLAYER_MODE_ENUM = ['싱글 플레이어', '멀티플레이어', '협동', '온라인 협동', 'PvP']
SORT_ENUM = ['평가순', '가격낮은순', '가격높은순', '리뷰많은순', '할인율순']

# LLM 함수 호출 인자를 Literal로 제한할 때는 이 타입을 그대로 가져다 쓴다.
# (원래 스캐폴드에서 config.GENRE_ENUM과 agent/schemas.py의 Literal 목록이
#  따로 관리되다 개수가 어긋난 적이 있어서, 정의를 하나로 합쳤다.)
GenreType = Literal[*GENRE_ENUM]
PlayerModeType = Literal[*PLAYER_MODE_ENUM]
SortType = Literal[*SORT_ENUM]


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')


def _split_pipe(value: str) -> list[str]:
    return [part for part in value.split('|') if part]


# ==================================
# 게임 (games.csv 1행)
# ==================================
class Game(StrictModel):
    app_id: str
    name: str
    is_free: bool
    price: int = Field(ge=0)
    final_price: int = Field(ge=0)
    # 할인율은 범위를 벗어나는 게 실제로 관측된 적 있는 필드라 (번들 할인 등) 여기서 강제하지 않고,
    # standardize.py의 품질검증에서 "경고만 하고 게임은 유지"하는 소프트 규칙으로 다룬다.
    discount_percent: int
    review_score: int = Field(ge=0, le=9)
    review_score_desc: str
    total_reviews: int = Field(ge=0)
    positive_ratio: float = Field(ge=0.0, le=1.0)
    # genre는 미매칭 태그가 나올 수 있어(standardize.py 품질검증에서 경고만 하고 안 막음)
    # 여기서는 GenreType으로 강제하지 않고 느슨한 list[str]로 둔다.
    genres: list[str]
    categories: list[str]
    player_modes: list[str]
    language_count: int = Field(ge=0)
    release_date: str
    developers: list[str]
    publishers: list[str]
    header_image: str
    short_description: str

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> 'Game':
        """csv.DictReader가 주는 문자열 dict를 타입 있는 모델로 바꾼다."""
        return cls(
            app_id=row['app_id'],
            name=row['name'],
            is_free=row['is_free'] == 'True',
            price=int(row['price'] or 0),
            final_price=int(row['final_price'] or 0),
            discount_percent=int(row['discount_percent'] or 0),
            review_score=int(row['review_score'] or 0),
            review_score_desc=row['review_score_desc'],
            total_reviews=int(row['total_reviews'] or 0),
            positive_ratio=float(row['positive_ratio'] or 0.0),
            genres=_split_pipe(row['genres']),
            categories=_split_pipe(row['categories']),
            player_modes=_split_pipe(row['player_modes']),
            language_count=int(row['language_count'] or 0),
            release_date=row['release_date'],
            developers=_split_pipe(row['developers']),
            publishers=_split_pipe(row['publishers']),
            header_image=row['header_image'],
            short_description=row['short_description'],
        )

    def to_csv_row(self) -> dict[str, str]:
        """csv.DictWriter에 그대로 넘길 수 있는 문자열 dict로 바꾼다."""
        return {
            'app_id': self.app_id,
            'name': self.name,
            'is_free': str(self.is_free),
            'price': str(self.price),
            'final_price': str(self.final_price),
            'discount_percent': str(self.discount_percent),
            'review_score': str(self.review_score),
            'review_score_desc': self.review_score_desc,
            'total_reviews': str(self.total_reviews),
            'positive_ratio': str(self.positive_ratio),
            'genres': '|'.join(self.genres),
            'categories': '|'.join(self.categories),
            'player_modes': '|'.join(self.player_modes),
            'language_count': str(self.language_count),
            'release_date': self.release_date,
            'developers': '|'.join(self.developers),
            'publishers': '|'.join(self.publishers),
            'header_image': self.header_image,
            'short_description': self.short_description,
        }

    def to_vector_metadata(self) -> dict:
        """steam_games 컬렉션(폴백 검색용) 메타데이터. Chroma는 리스트를 못 받아 문자열로 합친다."""
        return {
            'app_id': self.app_id,
            'name': self.name,
            'is_free': self.is_free,
            'final_price': self.final_price,
            'discount_percent': self.discount_percent,
            'review_score': self.review_score,
            'total_reviews': self.total_reviews,
            'positive_ratio': self.positive_ratio,
            'genres': '|'.join(self.genres),
            'player_modes': '|'.join(self.player_modes),
            'header_image': self.header_image,
            'release_date': self.release_date,
        }


GAME_CSV_FIELDS = list(Game.model_fields.keys())


# ==================================
# 리뷰 청크 (reviews.csv 1행)
# ==================================
class ReviewChunk(StrictModel):
    chunk_id: str
    review_id: str
    app_id: str
    name: str
    voted_up: bool
    playtime_hours: float = Field(ge=0.0)
    votes_up: int = Field(ge=0)
    chunk_index: int = Field(ge=0)
    text: str = Field(min_length=1)

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> 'ReviewChunk':
        return cls(
            chunk_id=row['chunk_id'],
            review_id=row['review_id'],
            app_id=row['app_id'],
            name=row['name'],
            voted_up=row['voted_up'] == 'True',
            playtime_hours=float(row['playtime_hours'] or 0.0),
            votes_up=int(row['votes_up'] or 0),
            chunk_index=int(row['chunk_index'] or 0),
            text=row['text'],
        )

    def to_csv_row(self) -> dict[str, str]:
        return {
            'chunk_id': self.chunk_id,
            'review_id': self.review_id,
            'app_id': self.app_id,
            'name': self.name,
            'voted_up': str(self.voted_up),
            'playtime_hours': str(self.playtime_hours),
            'votes_up': str(self.votes_up),
            'chunk_index': str(self.chunk_index),
            'text': self.text,
        }

    def to_vector_metadata(self) -> dict:
        """steam_reviews 컬렉션 메타데이터.

        text를 메타데이터에도 넣어두는 이유: Chroma 검색 결과의 document는
        임베딩에 실제로 들어간 문자열 그대로라 후처리(정규화 등)를 거쳤을 수 있다.
        원문을 그대로 근거로 보여주려면 metadata['text']를 쓰는 편이 안전하다.
        """
        return {
            'app_id': self.app_id,
            'name': self.name,
            'review_id': self.review_id,
            'voted_up': self.voted_up,
            'playtime_hours': self.playtime_hours,
            'votes_up': self.votes_up,
            'text': self.text,
        }


REVIEW_CSV_FIELDS = list(ReviewChunk.model_fields.keys())


# ==================================
# 리뷰 집계 기반 취향 검색 결과 (retrieval.py -> tools.py 계약)
# ==================================
class ReviewMatch(StrictModel):
    """벡터 검색으로 걸린 리뷰 1건. 추천 근거로 그대로 노출된다."""
    review_id: str
    app_id: str
    text: str
    voted_up: bool
    playtime_hours: float = Field(ge=0.0)
    similarity: float = Field(ge=-1.0, le=1.0)


class GameVibeScore(StrictModel):
    """리뷰 검색 결과를 app_id별로 묶어 집계한 게임 1건.

    게임 점수 = 매칭된 리뷰 상위 3개 유사도 평균(top3_similarity).
    matched_review_count가 낮으면(예: 1~2건) 신뢰도가 낮다는 뜻이므로
    tools.py가 이 값을 그대로 응답에 실어 LLM이 확신 수준을 밝히게 한다.
    """
    app_id: str
    top3_similarity: float = Field(ge=-1.0, le=1.0)
    matched_review_count: int = Field(ge=1)
    matched_reviews: list[ReviewMatch] = Field(min_length=1)
