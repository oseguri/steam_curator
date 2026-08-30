"""게임 상세 & 근거 리뷰 - 리뷰 RAG가 어떤 근거를 골라오는지 직접 확인한다."""
import streamlit as st
from common import format_price, games_frame, setup_page

setup_page('게임 상세', '🔍')

from src.agent.registry import FUNCTION_MAP
from src.loaders import load_reviews

st.title('게임 상세 & 근거 리뷰')
st.caption('질문에 대해 리뷰 RAG가 어떤 근거를 가져오는지 확인합니다.')

games = games_frame()
reviews = load_reviews()
reviewed_ids = set(reviews['app_id'])

# 챗봇에서 '상세 보기'로 넘어온 경우 그 게임을 미리 골라둔다
options = games['app_id'].tolist()
labels = dict(zip(games['app_id'], games['name']))
selected = st.session_state.get('selected_app_id')
index = options.index(selected) if selected in options else 0

app_id = st.selectbox(
    '게임 선택',
    options=options,
    index=index,
    format_func=lambda value: f"{labels[value]}{'' if value in reviewed_ids else '  (리뷰 없음)'}",
)
st.session_state.selected_app_id = app_id

detail = FUNCTION_MAP['get_game_detail'](app_id=app_id)
if not detail['success']:
    st.error('게임 정보를 찾지 못했습니다.')
    st.stop()

game = detail['game']

# ---------------------------------------------------------------------------
image, body = st.columns([1, 2])

with image:
    if game.get('header_image'):
        st.image(game['header_image'], width='stretch')

with body:
    st.subheader(game['name'])
    st.markdown(format_price(game))
    columns = st.columns(3)
    columns[0].metric('평가', game.get('review_score_desc') or '-')
    columns[1].metric('긍정 비율', f"{(game.get('positive_ratio') or 0):.1%}")
    columns[2].metric('리뷰 수', f"{game.get('total_reviews', 0):,}")
    st.caption(str(game.get('genres', '')).replace('|', ' · '))
    st.write(game.get('short_description', ''))

st.divider()

# ---------------------------------------------------------------------------
st.header('리뷰에게 물어보기')

game_reviews = reviews[reviews['app_id'] == app_id]
if game_reviews.empty:
    st.warning(
        f'리뷰를 수집하지 않은 게임입니다 (수집 대상 {len(reviewed_ids)}개). '
        '질문하시면 근거 없음으로 반환됩니다.'
    )
else:
    st.caption(f'리뷰 청크 {len(game_reviews):,}건에서 긍정·부정 각각 상위 2건을 검색합니다.')

EXAMPLES = ['핵이 많나요?', '최적화는 어떤가요?', '초보자도 할 만한가요?', '스토리가 어떤가요?']
columns = st.columns(len(EXAMPLES))
picked = None
for column, example in zip(columns, EXAMPLES):
    if column.button(example, width='stretch'):
        picked = example

typed = st.text_input('직접 질문하기', placeholder='이 게임 요즘도 할 만해?')
question = picked or typed

if question:
    with st.spinner('검색 중...'):
        answer = FUNCTION_MAP['ask_about_game_reviews'](app_id=app_id, question=question)

    st.markdown(f'**질문**: {question}')

    if not answer['success']:
        st.error(f"근거 없음 — {answer['reason']}")
        st.caption(f"최고 유사도 {answer['best_similarity']:.4f}로 임계값에 미달하여 LLM 생성을 호출하지 않습니다.")
    else:
        st.caption(f"최고 유사도 {answer['best_similarity']:.4f}")
        positive, negative = st.columns(2)

        with positive:
            st.subheader(f"👍 긍정 {len(answer['positive'])}건")
            for item in answer['positive']:
                with st.container(border=True):
                    st.caption(
                        f"유사도 {item['similarity']:.3f} · "
                        f"플레이 {item['playtime_hours']:.0f}시간 · "
                        f"도움됨 {item['votes_up']}"
                    )
                    st.write(item['text'])

        with negative:
            st.subheader(f"👎 부정 {len(answer['negative'])}건")
            for item in answer['negative']:
                with st.container(border=True):
                    st.caption(
                        f"유사도 {item['similarity']:.3f} · "
                        f"플레이 {item['playtime_hours']:.0f}시간 · "
                        f"도움됨 {item['votes_up']}"
                    )
                    st.write(item['text'])

        st.caption(
            '수집된 리뷰의 약 65%가 긍정 평가이므로, 단순 top-k 검색 시 요약이 긍정으로 치우칠 수 있습니다. '
            '긍정과 부정을 각각 임계값으로 필터링하면 한쪽만 통과하여 편향이 심해질 수 있어(`핵이 많나요?` → 긍정 0 / 부정 2), '
            '양측에서 먼저 후보를 선별한 뒤 임계값은 전체 검색 게이트로 활용합니다.'
        )
