"""검색 성능 평가 - 설명만 임베딩 vs 리뷰 집계를 같은 문항으로 비교한다."""
import pandas as pd
import plotly.express as px
import streamlit as st
from common import setup_page

setup_page('검색 성능 평가', '📊')

from src.eval.questions import (
    RECALL_QUESTIONS,
    REVIEW_QUESTIONS,
    THRESHOLD_QUESTIONS,
)

st.title('검색 성능 평가')
st.caption(
    '"리뷰를 근거로 쓰면 정말 나아지는가"를 같은 문항으로 두 번 재서 확인했습니다. '
    '아래 수치는 버튼을 누르면 그 자리에서 다시 계산됩니다.'
)

# ---------------------------------------------------------------------------
st.header('1. 라벨링 방법')

left, right = st.columns([2, 1])

with left:
    st.markdown(
        f"""
        Recall@5용 문항 **{len(RECALL_QUESTIONS)}개**에 정답 게임을 손으로 붙였습니다.
        중요한 것은 **정답 라벨을 검색 시스템을 거치지 않고 만들었다**는 점입니다.
        `games.csv`를 이름·장르 키워드로 훑어 정답을 먼저 적고, 그다음에 검색을 돌렸습니다.

        시스템 출력으로 라벨을 만들면 Recall이 1.0으로 나오지만 아무것도 측정하지 못합니다.
        평가 지표가 자기 자신을 채점하는 셈이 됩니다.

        문항에는 의도적으로 세 종류를 섞었습니다.

        - **정답이 전부 리뷰 없는 게임** (기차 시뮬레이터, 방치형 클리커) → 설명 폴백이 작동해야만 맞습니다
        - **상점 설명에 없는 속성** (핵이 많은 게임, 최적화가 나쁜 게임) → 리뷰 집계만 맞힐 수 있습니다
        - 일반적인 장르·소재 질문 → 두 방식 모두 어느 정도 맞힙니다
        """
    )

with right:
    label_rows = []
    for question, answers in RECALL_QUESTIONS:
        label_rows.append({'질문': question, '정답 수': len(answers)})
    st.dataframe(pd.DataFrame(label_rows), width='stretch', hide_index=True, height=380)

# ---------------------------------------------------------------------------
st.divider()
st.header('2. Recall@5 - 설명만 vs 리뷰 집계')

st.caption(
    f'문항 {len(RECALL_QUESTIONS)}개를 세 방식으로 검색합니다. '
    '임베딩 호출이 있어 30초 안팎 걸리고, 한 번 계산하면 캐시됩니다.'
)


@st.cache_data(show_spinner=False)
def run_recall() -> tuple[pd.DataFrame, pd.DataFrame]:
    from src.agent.retrieval import search_by_description, search_by_vibe, search_games
    from src.eval.recall import evaluate

    results = [
        evaluate('설명만', lambda question: search_by_description(question, threshold=0.0)),
        evaluate('리뷰집계', lambda question: search_by_vibe(question, threshold=0.0)),
        evaluate('실제경로', lambda question: search_games(question)[0]),
    ]
    summary = pd.DataFrame([
        {
            '방식': result['name'],
            'Hit@5': round(result['hit_rate'], 3),
            'P@5': round(result['precision'], 3),
            'R@5': round(result['recall'], 3),
        }
        for result in results
    ])
    detail = pd.DataFrame({
        '질문': [row['question'] for row in results[0]['rows']],
        '정답 수': [len(row['answers']) for row in results[0]['rows']],
        **{
            result['name']: [row['precision'] for row in result['rows']]
            for result in results
        },
    })
    return summary, detail


if st.button('평가 실행', type='primary'):
    st.session_state.recall_done = True

if st.session_state.get('recall_done'):
    with st.spinner('15문항 × 3방식 검색 중...'):
        summary, detail = run_recall()

    columns = st.columns(3)
    baseline = summary[summary['방식'] == '설명만'].iloc[0]
    current = summary[summary['방식'] == '실제경로'].iloc[0]
    columns[0].metric('Hit@5', current['Hit@5'], f"{current['Hit@5'] - baseline['Hit@5']:+.3f}")
    columns[1].metric('P@5', current['P@5'], f"{current['P@5'] - baseline['P@5']:+.3f}")
    columns[2].metric('R@5', current['R@5'], f"{current['R@5'] - baseline['R@5']:+.3f}")

    st.dataframe(summary, width='stretch', hide_index=True)

    melted = detail.melt(
        id_vars=['질문', '정답 수'],
        value_vars=['설명만', '리뷰집계'],
        var_name='방식',
        value_name='P@5',
    )
    figure = px.bar(
        melted, x='질문', y='P@5', color='방식', barmode='group',
        title='문항별 P@5 - 설명만 vs 리뷰 집계',
    )
    figure.update_layout(xaxis_tickangle=-30, height=460)
    st.plotly_chart(figure, width='stretch')

    detail['차이'] = detail['리뷰집계'] - detail['설명만']
    gained = detail[detail['차이'] > 0].sort_values('차이', ascending=False)
    lost = detail[detail['차이'] < 0].sort_values('차이')

    left, right = st.columns(2)
    with left:
        st.subheader('리뷰 집계가 이긴 문항')
        st.dataframe(gained[['질문', '설명만', '리뷰집계']], width='stretch', hide_index=True)
        st.markdown(
            '`난이도가 극악인`, `핵과 부정행위` 처럼 **개발사가 상점 설명에 쓸 리 없는 말**에서 '
            '격차가 벌어집니다. RAG가 왜 필요한지를 그대로 보여주는 부분입니다.'
        )
    with right:
        st.subheader('설명 임베딩이 이긴 문항')
        st.dataframe(lost[['질문', '설명만', '리뷰집계']], width='stretch', hide_index=True)
        st.markdown(
            '정답 게임이 전부 리뷰 없는 게임인 문항들입니다. '
            '리뷰 경로에는 애초에 존재하지 않아 0점이 나옵니다. '
            '**점수 비교 라우팅은 바로 이 두 문항을 되찾으려고 넣었습니다.**'
        )

    st.info(
        '원래 목표는 P@5 0.35 → 0.7x였는데 실제는 0.32 → 0.55입니다. '
        '정답 라벨을 문항당 4~10개로 넉넉히 잡아 R@5의 상한이 구조적으로 낮습니다. '
        '숫자를 키우려고 라벨을 줄이지는 않았습니다.'
    )
else:
    st.info('버튼을 누르면 그 자리에서 15문항을 다시 검색해 채점합니다.')

# ---------------------------------------------------------------------------
st.divider()
st.header('3. 임계값은 어떻게 정했나')

st.caption(
    f'관련 질문과 무관 질문을 섞어 점수 분포를 재고, 그 사이 빈 구간에 임계값을 놓았습니다. '
    f'(취향 {len(THRESHOLD_QUESTIONS)}문항 / 리뷰 질의 {len(REVIEW_QUESTIONS)}문항)'
)


@st.cache_data(show_spinner=False)
def run_threshold() -> pd.DataFrame:
    from src.eval.threshold import collect_description, collect_review, collect_vibe

    rows = []
    for label, collect in (
        ('취향 검색', collect_vibe),
        ('설명 폴백', collect_description),
        ('리뷰 질의', collect_review),
    ):
        for name, score, should_pass in collect():
            rows.append({
                '경로': label,
                '질문': name,
                '점수': score,
                '유형': '관련' if should_pass else '무관',
            })
    return pd.DataFrame(rows)


if st.button('임계값 분포 측정'):
    st.session_state.threshold_done = True

if st.session_state.get('threshold_done'):
    with st.spinner('관련/무관 질문 점수 분포 측정 중...'):
        distribution = run_threshold()

    figure = px.strip(
        distribution, x='점수', y='경로', color='유형',
        stripmode='overlay', title='관련 질문과 무관 질문의 점수 분포',
        hover_data=['질문'],
    )
    figure.update_layout(height=340)
    st.plotly_chart(figure, width='stretch')

    summary_rows = []
    for path in distribution['경로'].unique():
        subset = distribution[distribution['경로'] == path]
        relevant = subset[subset['유형'] == '관련']['점수']
        irrelevant = subset[subset['유형'] == '무관']['점수']
        gap = relevant.min() - irrelevant.max()
        summary_rows.append({
            '경로': path,
            '관련 최저': round(relevant.min(), 4),
            '무관 최고': round(irrelevant.max(), 4),
            '빈 구간': round(gap, 4),
            '판정': '단일 임계값으로 분리 가능' if gap > 0 else '겹쳐서 분리 불가',
        })
    st.dataframe(pd.DataFrame(summary_rows), width='stretch', hide_index=True)

    st.markdown(
        """
        **취향 검색**은 빈 구간이 0.0795로 넉넉해 20문항 전부 정확히 갈립니다.
        **설명 폴백**은 0.0277로 좁아 판별력이 떨어지는데, 이것 자체가
        "설명 임베딩만으로는 부족하다"는 근거이기도 합니다.

        **리뷰 질의**는 관련과 무관이 겹칩니다. `app_id`로 한 게임에 좁힌 뒤라
        후보 리뷰가 전부 그 게임 얘기여서, 유사도가 *질문에 답이 되는가* 가 아니라
        *이 게임 얘기인가* 만 반영하기 때문입니다.
        어떤 값을 잡아도 20문항 중 17개가 최선이었고,
        그래서 이 경로는 임계값 대신 프롬프트로 막았습니다.
        """
    )
else:
    st.info('버튼을 누르면 관련/무관 질문의 점수 분포를 측정합니다.')
