"""큐레이터 챗봇 - LLM이 툴을 고르는 과정을 사이드바에 그대로 노출한다."""
import streamlit as st
from common import render_game_card, render_trace, setup_page

setup_page('큐레이터 챗봇', '💬')

from src.agent.orchestrator import ask

st.title('큐레이터 챗봇')
st.caption(
    'LLM이 질문을 보고 어떤 툴을 고르는지, 어떤 인자를 만들어내는지, '
    '검증을 통과했는지를 사이드바에서 실시간으로 볼 수 있습니다.'
)

EXAMPLES = [
    ('정형 조건', '3만원 이하 액션 게임 5개 알려줘'),
    ('취향', '혼자 조용히 힐링되는 게임 추천해줘'),
    ('하이브리드', '3만원 이하인데 스토리가 감동적인 게임 있어?'),
    ('평판 질의', 'Counter-Strike 2 핵 많아?'),
    ('환각 차단', '그란 투리스모 8 재밌어?'),
]

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
                st.switch_page('pages/4_게임_상세.py')

typed = st.chat_input('어떤 게임을 찾으세요?')
question = pending or typed

if question:
    st.session_state.messages.append({'role': 'user', 'text': question})
    with st.chat_message('user'):
        st.markdown(question)

    with st.chat_message('assistant'):
        with st.spinner('툴을 고르고 검색하는 중...'):
            answer = ask(question, history=st.session_state.history)

        st.markdown(answer['answer'] or '(답변을 생성하지 못했습니다)')

        # 툴이 돌려준 결과는 results[*]['games']에 들어 있다
        games = [
            game
            for result in answer['results']
            for game in result.get('games', [])
        ]
        for game in games:
            render_game_card(game)

    st.session_state.messages.append({
        'role': 'assistant',
        'text': answer['answer'] or '(답변을 생성하지 못했습니다)',
        'games': games,
        'key': answer['interaction_id'],
    })
    # LLM에 넘기는 이력에는 텍스트만 넣는다. 함수 응답까지 쌓으면 토큰이 불어난다
    st.session_state.history.append({'role': 'user', 'text': question})
    st.session_state.history.append({'role': 'model', 'text': answer['answer'] or ''})
    st.session_state.last_trace = answer['trace']
    st.rerun()
