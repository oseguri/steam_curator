"""검색 성능 평가 - 설명만 임베딩 vs 리뷰 집계."""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from common import setup_page

setup_page('검색 성능 평가', '📊')

RESULT_PATH = Path(__file__).resolve().parents[2] / 'src' / 'eval' / 'recall_result.json'

st.title('검색 성능 평가')
st.caption('`uv run python -m src.eval.recall` 실행 결과입니다. 문항 15개에 정답 게임 91개를 매칭하여 채점했습니다.')

if not RESULT_PATH.exists():
    st.error('평가 결과 파일이 없습니다. `uv run python -m src.eval.recall`을 먼저 실행해주세요.')
    st.stop()

result = json.loads(RESULT_PATH.read_text(encoding='utf-8'))
summary = pd.DataFrame(result['summary'])
detail = pd.DataFrame(result['per_question'])

# ---------------------------------------------------------------------------
base = summary[summary['name'] == '설명만'].iloc[0]
now = summary[summary['name'] == '실제경로'].iloc[0]

columns = st.columns(3)
columns[0].metric('Hit@5', f"{now['hit_rate']:.3f}", f"{now['hit_rate'] - base['hit_rate']:+.3f}")
columns[1].metric('P@5', f"{now['precision']:.3f}", f"{now['precision'] - base['precision']:+.3f}")
columns[2].metric('R@5', f"{now['recall']:.3f}", f"{now['recall'] - base['recall']:+.3f}")

st.dataframe(
    pd.DataFrame({
        '방식': summary['name'],
        'Hit@5': summary['hit_rate'].round(3),
        'P@5': summary['precision'].round(3),
        'R@5': summary['recall'].round(3),
    }),
    width='stretch',
    hide_index=True,
)

st.markdown(
    """
    | 지표 | 뜻 |
    |---|---|
    | Hit@5 | 상위 5개에 정답이 하나라도 포함된 문항 비율 |
    | P@5 | 추천된 5개 중 실제 정답 비율 |
    | R@5 | 전체 정답 중 상위 5개에 포함된 비율 (정답이 문항당 4~10개라 상한이 낮습니다) |
    """
)

# ---------------------------------------------------------------------------
st.divider()
st.subheader('문항별 평가 결과')

melted = detail.melt(
    id_vars=['question'], value_vars=['설명만', '리뷰집계'],
    var_name='방식', value_name='P@5',
)
figure = px.bar(melted, x='question', y='P@5', color='방식', barmode='group')
figure.update_layout(xaxis_tickangle=-30, height=420, xaxis_title=None)
st.plotly_chart(figure, width='stretch')

detail['차이'] = detail['리뷰집계'] - detail['설명만']

left, right = st.columns(2)
with left:
    st.markdown('**리뷰 집계가 우세했던 문항**')
    gained = detail[detail['차이'] > 0].sort_values('차이', ascending=False)
    st.dataframe(
        gained[['question', '설명만', '리뷰집계']].rename(columns={'question': '질문'}),
        width='stretch', hide_index=True,
    )
    st.caption('난이도, 핵, 최적화처럼 상점 설명에 적히지 않는 속성에서 격차가 벌어집니다.')

with right:
    st.markdown('**설명 임베딩이 우세했던 문항**')
    lost = detail[detail['차이'] < 0].sort_values('차이')
    st.dataframe(
        lost[['question', '설명만', '리뷰집계']].rename(columns={'question': '질문'}),
        width='stretch', hide_index=True,
    )
    st.caption('정답 게임이 모두 리뷰가 없는 게임입니다. 검색 경로 동적 선택을 통해 되찾은 문항입니다.')

# ---------------------------------------------------------------------------
st.divider()
st.subheader('정답 라벨을 작성한 방법')

st.info(
    '정답 라벨은 검색 시스템을 거치지 않고 직접 작성했습니다. games.csv를 이름·장르 키워드로 검토하여 '
    '정답을 먼저 정의한 뒤 검색을 수행했습니다. 시스템 출력을 바탕으로 라벨을 작성하면 '
    'Recall이 1.0으로 왜곡되어 유의미한 측정이 불가능합니다.'
)

st.dataframe(
    detail[['question', 'answer_count']].rename(columns={'question': '질문', 'answer_count': '정답 수'}),
    width='stretch', hide_index=True, height=300,
)
