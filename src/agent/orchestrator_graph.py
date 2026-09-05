'''LLM 오케스트레이션 langgraph'''
import json
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages

from config import GEMINI_API_KEY, GEMINI_MODEL
from src.agent.constant import MAX_TURNS
from src.agent.orchestrator import execute_call
from src.agent.registry import ARGUMENT_MODELS, FUNCTION_MAP, TOOLS
from src.agent.utils import finish

SYSTEM_PROMPT = """너는 Steam 게임 큐레이터다. 한국어로 답한다.

## 반드시 지킬 것

1. 툴이 돌려준 결과만 근거로 답한다. 네가 알고 있는 게임 지식으로 보충하지 않는다.
   우리 데이터에 없는 게임은 존재하더라도 언급하지 않는다.
2. 근거에 없는 내용은 지어내지 않는다. 리뷰에 언급이 없으면
   "리뷰에서는 그 부분을 찾지 못했다"고 그대로 말한다.
3. 툴 결과가 success=False면 reason을 사용자에게 그대로 전달한다.
   다른 툴로 억지로 답을 만들어내지 않는다.
4. app_id를 모르면 추측하지 말고 먼저 검색 툴로 찾는다.

## 답변 방식

- 게임을 추천할 때는 리뷰 원문을 짧게 인용해 왜 그 게임인지 보여준다.
- match_count가 2 이하면 "근거가 적어 확신은 낮다"고 밝힌다.
- 가격은 원 단위로, 무료면 "무료"라고 쓴다.
- 결과가 없으면 없다고 말하고, 조건을 어떻게 바꾸면 좋을지 한 줄 제안한다.
"""


class AgentState(TypedDict):
    '''Graph State'''
    messages: Annotated[list[BaseMessage], add_messages] #대화 이력
    interaction_id: str
    trace: list[dict]
    results: list[dict]
    question: str
    answer: str
    loop_count: int

def get_strutured_tools() -> list[StructuredTool]:
    '''tools 하위 tool들을 langchain의 StrucuredTool 리스트로 반환'''
    langchain_tools = []

    for name, run_fn in FUNCTION_MAP.items():
        desc = next(
            t['description']
            for t in TOOLS if t['name'] == name
        )
        lc_tool = StructuredTool(
            name=name,
            description=desc,
            func=run_fn,
            args_schema=ARGUMENT_MODELS[name],
        )
        langchain_tools.append(lc_tool)

    return langchain_tools

llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    google_api_key=GEMINI_API_KEY,
    temparature=0,
)

llm_with_tools = llm.bind_tools(get_strutured_tools())

#==============================================================
# LLM 호출 노드
#==============================================================
def call_llm(state: AgentState):
    '''llm 호출 노드'''
    system_msg = SystemMessage(content=SYSTEM_PROMPT)
    response = llm_with_tools.invoke([system_msg] + state['messages'])
    return {'messages': [response]}

#==============================================================
# tool 실행 노드
#==============================================================
def execute_tools(state: AgentState):
    '''tool 실행 노드'''
    last_message = state['messages'][-1]
    tool_calls = last_message.tool_calls

    new_messages = []
    new_trace = []
    new_results = []

    for call in tool_calls:
        call_name = call['name']

        result, entry = execute_call(call)
        new_trace.append(entry)

        if result.get('sucess'):
            new_results.append(result)

        new_messages.append(
            ToolMessage(
                content=json.dumps(
                    {'result': result},
                    ensure_ascii=False
                ),
                name=call_name,
                tool_call_id=call['id']
            )
        )

        return {
            'messages': new_messages,
            'trace': state['trace'] + new_trace,
            'results': state['results'] + new_results,
            'loop_count': state['loop_count'] + 1
        }

#==============================================================
# 강제 답변 생성 노드(max turn 넘어가는 경우)
#==============================================================
def force_final_answer(state: AgentState):
    '''max turn 넘는 경우 강제 답변 생성 노드'''
    system_message = SystemMessage(content=SYSTEM_PROMPT)
    response = llm.invoke([system_message] + state['messages'])
    return {'messages': [response], 'answer': response.content}

#==============================================================
# 답변 마무리 및 로그 기록 노드
#==============================================================
def finalize(state: AgentState):
    '''답변 마무리 및 로그 기록 노드'''
    answer_text = state['messages'][-1].content

    finish(
        interaction_id=state['interaction_id'],
        question=state['question'],
        answer=answer_text,
        trace=state['trace'],
        results=state['results'],
    )

    return {'answer': answer_text}

#==============================================================
# 분기 결정
#==============================================================
def should_continue(state: AgentState):
    '''분기 결정 함수'''
    last_message = state['messages'][-1]

    # 도구 호출 없는 경우 finalize 노드로 라우팅
    if not getattr(last_message, 'tool_calls', None):
        return 'end'

    # 루프 횟수 초과 시 force_final_answer 노드로 라우팅
    if state['loop_count'] >= MAX_TURNS:
        return 'force_final_answer'

    # 이외 execute_call로 함수 호출
    return 'execute_call'
