"""데이터 현황 - 무엇을 얼마나 모았고, 어디가 비어 있는가."""
import pandas as pd
import plotly.express as px
import streamlit as st
from common import (
    games_frame,
    interactions_frame,
    quality_frame,
    reviews_frame,
    setup_page,
)

setup_page('데이터 현황', '🗂️')

st.title('데이터 현황')
st.caption('에이전트가 답할 수 있는 범위는 결국 여기까지입니다. 무엇이 있고 무엇이 없는지 밝혀둡니다.')

games = games_frame()
reviews = reviews_frame()
issues = quality_frame()

reviewed = reviews['app_id'].nunique()
columns = st.columns(4)
columns[0].metric('게임', f'{len(games):,}건')
columns[1].metric('리뷰 청크', f'{len(reviews):,}건')
columns[2].metric('리뷰 보유 게임', f'{reviewed:,}개', f'{reviewed - len(games):,}')
columns[3].metric('품질 이슈', f'{len(issues)}건')

st.warning(
    f'**리뷰가 있는 게임은 {reviewed}개뿐입니다.** 나머지 {len(games) - reviewed:,}개는 상점 설명만 있습니다. '
    '취향 검색은 리뷰에만 의존하므로, 이 게임들은 설명 폴백 경로로만 추천될 수 있습니다. '
    '검색 경로를 점수 비교로 고르게 바꾼 이유가 여기 있습니다.'
)

# ---------------------------------------------------------------------------
st.divider()
st.header('1. 리뷰 중복 제거')

st.markdown(
    """
    수집한 리뷰 원본은 11,410건이었는데 `chunk_id` 중복이 **3,008건** 있었습니다.
    페이지네이션이 겹치면서 같은 리뷰를 두 번 가져온 것입니다.

    `chunk_id`를 Chroma의 문서 id로 쓰는데, **중복 id로 `add`하면 예외도 갱신도 없이 조용히 무시됩니다.**
    그대로 넣었다면 11,410건을 넣었다고 생각하면서 실제로는 8,402건만 들어가고,
    7분짜리 임베딩을 다 돌린 뒤에야 알게 됐을 겁니다.
    """
)

before, after = 11410, len(reviews)
positive_after = int(reviews['voted_up'].sum())
columns = st.columns(3)
columns[0].metric('중복 제거 전', f'{before:,}건')
columns[1].metric('중복 제거 후', f'{after:,}건', f'{after - before:,}')
columns[2].metric('긍정 비율', f'{positive_after / after:.1%}', '60.5% → 65.2%')

st.caption(
    '중복이 섞인 상태에서 계산한 긍정 비율 60.5%는 틀린 값이었습니다. '
    '실제는 65.2%입니다. 리뷰 요약이 긍정으로 기우는 것을 막는 설계의 전제가 되는 숫자입니다.'
)

# ---------------------------------------------------------------------------
st.divider()
st.header('2. 분포')

left, right = st.columns(2)

with left:
    genre_counts = (
        games['genres'].str.split('|').explode().str.strip()
        .replace('', pd.NA).dropna().value_counts().head(12).reset_index()
    )
    genre_counts.columns = ['장르', '게임 수']
    figure = px.bar(genre_counts, x='게임 수', y='장르', orientation='h', title='장르별 게임 수')
    figure.update_layout(yaxis={'categoryorder': 'total ascending'}, height=380)
    st.plotly_chart(figure, width='stretch')

with right:
    paid = games[~games['is_free']]
    figure = px.histogram(
        paid, x='final_price', nbins=40,
        title=f'유료 게임 가격 분포 (무료 {int(games["is_free"].sum())}개 제외)',
        labels={'final_price': '최종 가격(원)'},
    )
    figure.update_layout(height=380)
    st.plotly_chart(figure, width='stretch')

left, right = st.columns(2)

with left:
    discounted = games[games['discount_percent'] > 0]
    figure = px.histogram(
        discounted, x='discount_percent', nbins=20,
        title=f'할인율 분포 (할인 중 {len(discounted)}개)',
        labels={'discount_percent': '할인율(%)'},
    )
    figure.update_layout(height=340)
    st.plotly_chart(figure, width='stretch')

with right:
    playtime = reviews[reviews['playtime_hours'] > 0]
    figure = px.histogram(
        playtime, x='playtime_hours', nbins=50, log_y=True,
        title='리뷰 작성자 플레이타임 (로그 스케일)',
        labels={'playtime_hours': '플레이 시간'},
    )
    figure.update_layout(height=340)
    st.plotly_chart(figure, width='stretch')

# ---------------------------------------------------------------------------
st.divider()
st.header('3. 품질 이슈')

if issues.empty:
    st.success('기록된 품질 이슈가 없습니다.')
else:
    st.caption(
        '표준화 단계에서 규칙에 걸린 건들입니다. 게임을 버리지 않고 기록만 남겼습니다 — '
        '대부분 장르 태그가 우리 enum에 없는 경우라 검색에는 영향이 없습니다.'
    )
    st.dataframe(issues, width='stretch', hide_index=True)

st.markdown(
    """
    이 외에 알고 있는 빈틈입니다.

    - `genres`가 빈 게임 4건, `player_modes`가 빈 게임 11건 — Chroma는 빈 리스트를 거부하고,
      키를 아예 빼면 이전 인덱싱의 값이 같은 id에 되살아나는 버그가 있어 빈 문자열로 채웠습니다
    - `review_score = 0`인 게임 23건 — "평가 나쁨"이 아니라 요약 수집 실패입니다
    - 8,000자짜리 도배 리뷰 2건 — 임베딩은 통과하므로 그대로 뒀습니다
    """
)

# ---------------------------------------------------------------------------
st.divider()
st.header('4. 질의 기록')

interactions = interactions_frame()
if interactions.empty:
    st.info('아직 기록이 없습니다. 큐레이터 챗봇에서 질문하면 여기에 쌓입니다.')
else:
    st.caption(
        f'챗봇에 들어온 질문 {len(interactions)}건입니다. '
        '`data/interactions.jsonl`에 한 줄씩 남습니다.'
    )
    view = pd.DataFrame({
        '시각': interactions['asked_at'],
        '질문': interactions['question'],
        '툴 호출': interactions['trace'].apply(len),
        '결과 건수': interactions['result_count'],
        '사용한 툴': interactions['trace'].apply(
            lambda trace: ', '.join(entry['function'] for entry in trace) or '-'
        ),
    })
    st.dataframe(view.iloc[::-1], width='stretch', hide_index=True)

    used = [
        entry['function']
        for trace in interactions['trace']
        for entry in trace
    ]
    if used:
        counts = pd.Series(used).value_counts().reset_index()
        counts.columns = ['툴', '호출 수']
        figure = px.bar(counts, x='툴', y='호출 수', title='툴별 호출 횟수')
        figure.update_layout(height=320)
        st.plotly_chart(figure, width='stretch')
