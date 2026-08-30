"""데이터 - 수집 규모와 분포."""
import pandas as pd
import plotly.express as px
import streamlit as st
from common import games_frame, quality_frame, reviews_frame, setup_page

setup_page('데이터', '🗂️')

st.title('데이터')

games = games_frame()
reviews = reviews_frame()
issues = quality_frame()
reviewed = reviews['app_id'].nunique()

columns = st.columns(4)
columns[0].metric('게임', f'{len(games):,}')
columns[1].metric('리뷰 청크', f'{len(reviews):,}')
columns[2].metric('리뷰 보유 게임', f'{reviewed:,}')
columns[3].metric('품질 이슈', f'{len(issues)}')

st.warning(
    f'리뷰가 있는 게임은 {reviewed}개이며, 나머지 {len(games) - reviewed:,}개는 상점 설명만 있습니다. '
    '취향 검색은 리뷰에 주로 의존하므로 이 게임들은 설명 검색 경로로 추천됩니다.'
)

# ---------------------------------------------------------------------------
st.divider()

left, right = st.columns(2)

with left:
    coverage = pd.DataFrame({
        '구분': ['리뷰 있음', '리뷰 없음'],
        '게임 수': [reviewed, len(games) - reviewed],
    })
    figure = px.pie(coverage, names='구분', values='게임 수', hole=0.5, title='리뷰 수집 범위')
    figure.update_layout(height=340)
    st.plotly_chart(figure, width='stretch')

with right:
    genre_counts = (
        games['genres'].str.split('|').explode().str.strip()
        .replace('', pd.NA).dropna().value_counts().head(10).reset_index()
    )
    genre_counts.columns = ['장르', '게임 수']
    figure = px.bar(genre_counts, x='게임 수', y='장르', orientation='h', title='장르별 게임 수')
    figure.update_layout(yaxis={'categoryorder': 'total ascending'}, height=340, yaxis_title=None)
    st.plotly_chart(figure, width='stretch')

left, right = st.columns(2)

with left:
    paid = games[~games['is_free']]
    figure = px.histogram(
        paid, x='final_price', nbins=40,
        title=f'유료 게임 가격 (무료 {int(games["is_free"].sum())}개 제외)',
        labels={'final_price': '원'},
    )
    figure.update_layout(height=320, yaxis_title=None)
    st.plotly_chart(figure, width='stretch')

with right:
    sentiment = pd.DataFrame({
        '평가': ['긍정', '부정'],
        '리뷰 수': [int(reviews['voted_up'].sum()), int((~reviews['voted_up']).sum())],
    })
    figure = px.bar(sentiment, x='평가', y='리뷰 수', title='리뷰 긍정·부정', text='리뷰 수')
    figure.update_layout(height=320, xaxis_title=None, yaxis_title=None)
    st.plotly_chart(figure, width='stretch')

st.caption(
    f'수집된 리뷰의 {reviews["voted_up"].mean():.0%}가 긍정 평가입니다. '
    '단순 top-k 검색 시 요약이 긍정으로 치우칠 수 있어, 리뷰 질의 시 긍정과 부정을 각각 분리하여 검색합니다.'
)

# ---------------------------------------------------------------------------
st.divider()
st.subheader('알려진 데이터 특이사항')

st.markdown(
    """
    - 수집 원본 11,410건 중 페이지네이션 겹침으로 인한 `chunk_id` 중복 3,008건을 제거하여 8,402건을 유지하고 있습니다.
    - `genres`가 비어 있는 게임 4건, `player_modes`가 비어 있는 게임 11건이 존재합니다.
    - `review_score = 0`인 게임 23건은 실제 평가가 나쁜 것이 아니라 요약 수집에 실패한 데이터입니다.
    """
)

if not issues.empty:
    with st.expander(f'품질 이슈 {len(issues)}건'):
        st.dataframe(issues, width='stretch', hide_index=True)
