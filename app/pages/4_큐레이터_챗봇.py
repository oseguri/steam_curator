"""큐레이터 챗봇 - LLM이 툴을 고르는 과정을 사이드바에 그대로 노출한다."""
import pandas as pd
import streamlit as st
from common import interactions_frame, render_game_card, render_trace, setup_page

setup_page('큐레이터 챗봇', '💬')

from src.agent.orchestrator import ask

st.title('큐레이터 챗봇')
st.caption('LLM이 선택한 툴과 인자, 검증 결과가 사이드바에 실시간으로 표시됩니다.')

EXAMPLES = [
    ('정형 조건', '3만원 이하 액션 게임 5개 알려줘'),
    ('취향', '혼자 조용히 힐링되는 게임 추천해줘'),
    ('하이브리드', '3만원 이하인데 스토리가 감동적인 게임 있어?'),
    ('평판 질의', 'Counter-Strike 2 핵 많아?'),
    ('환각 차단', '그란 투리스모 8 재밌어?'),
]


def cards_for(answer: dict) -> list[dict]:
    """답변과 어긋나지 않는 카드만 고른다.

    규칙이 둘이다.

    1) 마지막으로 부른 툴의 결과만 본다.
       app_id를 모르면 LLM은 검색 -> 리뷰 조회 순으로 두 번 부르는데,
       앞선 검색은 app_id를 찾으려는 것이라 그 결과까지 그리면
       답변은 한 게임 얘기인데 카드는 5장이 뜬다.

    2) 그중 답변 본문에 이름이 나온 게임만 그린다.
       툴은 임계값을 넘은 5개를 돌려주지만 LLM이 전부 소개하지는 않는다.
       "그란 투리스모 8" 질문에는 "데이터에 없다"고 답하면서
       레이싱 게임 5장이 뜨던 문제가 여기서 걸린다.
    """
    results = answer.get('results') or []
    if not results:
        return []
    text = answer.get('answer') or ''
    return [game for game in results[-1].get('games', []) if game['name'] in text]


if 'messages' not in st.session_state:
    st.session_state.messages = []   # 화면에 그릴 기록 (게임 카드 포함)
if 'history' not in st.session_state:
    st.session_state.history = []    # LLM에 넘길 이력 (텍스트만)
if 'last_trace' not in st.session_state:
    st.session_state.last_trace = None

# ==================================
# 사이드바 - 툴 호출 추적
# ==================================
with st.sidebar:
    st.header('툴 호출 추적')
    if st.session_state.last_trace is None:
        st.caption('질문을 입력하면 LLM이 고른 함수와 인자가 여기에 표시됩니다.')
    else:
        render_trace(st.session_state.last_trace)

    st.divider()
    if st.button('대화 초기화', width='stretch'):
        st.session_state.messages = []
        st.session_state.history = []
        st.session_state.last_trace = None
        st.rerun()

# ==================================
# 예시 질문
# ==================================
st.caption('예시 질문')
columns = st.columns(len(EXAMPLES))
pending = None
for column, (label, question) in zip(columns, EXAMPLES):
    if column.button(label, width='stretch', help=question):
        pending = question

# ==================================
# 대화 기록
# ==================================
for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['text'])
        for game in message.get('games', []):
            render_game_card(game)
            if st.button(
                f"{game['name']} 상세 보기",
                key=f"detail-{message['key']}-{game['app_id']}",
            ):
                st.session_state.selected_app_id = game['app_id']
                st.switch_page('pages/5_게임_상세.py')

typed = st.chat_input('어떤 게임을 찾으세요?')
question = pending or typed

if question:
    st.session_state.messages.append({'role': 'user', 'text': question})
    with st.chat_message('user'):
        st.markdown(question)

    with st.chat_message('assistant'):
        with st.spinner('검색 중...'):
            answer = ask(question, history=st.session_state.history)

        st.markdown(answer['answer'] or '(답변 없음)')

        games = cards_for(answer)
        for game in games:
            render_game_card(game)

    st.session_state.messages.append({
        'role': 'assistant',
        'text': answer['answer'] or '(답변 없음)',
        'games': games,
        'key': answer['interaction_id'],
    })
    # LLM에 넘기는 이력에는 텍스트만 넣는다. 함수 응답까지 쌓으면 토큰이 불어난다
    st.session_state.history.append({'role': 'user', 'text': question})
    st.session_state.history.append({'role': 'model', 'text': answer['answer'] or ''})
    st.session_state.last_trace = answer['trace']
    st.rerun()

# ==================================
# 질의 기록
# ==================================
st.divider()

interactions = interactions_frame()
if interactions.empty:
    st.caption('질문하시면 `data/interactions.jsonl`에 대화 및 툴 호출 기록이 저장됩니다.')
else:
    with st.expander(f'지금까지의 질의 기록 {len(interactions)}건'):
        st.dataframe(
            pd.DataFrame({
                '시각': interactions['asked_at'],
                '질문': interactions['question'],
                '사용한 툴': interactions['trace'].apply(
                    lambda trace: ', '.join(entry['function'] for entry in trace) or '-'
                ),
                '결과': interactions['result_count'],
            }).iloc[::-1],
            width='stretch',
            hide_index=True,
        )
