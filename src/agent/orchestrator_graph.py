'''LLM 오케스트레이션 langgraph'''
import json
import operator
import uuid
from typing import Annotated, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

from config import GEMINI_API_KEY, GEMINI_MODEL
from src.agent.constant import MAX_TURNS, SYSTEM_PROMPT
from src.agent.registry import ARGUMENT_MODELS, FUNCTION_MAP, TOOLS
from src.agent.utils import execute_call_by_name, finish


class AgentState(TypedDict):
    '''Graph State'''
    messages: Annotated[list[BaseMessage], add_messages] #대화 이력
    interaction_id: str
    trace: Annotated[list[dict], operator.add]
    results: Annotated[list[dict], operator.add]
    question: str
    loop_count: Annotated[int, operator.add]

def get_structured_tools() -> list[StructuredTool]:
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
    temperature=0,
)

llm_with_tools = (
    llm
    .bind_tools(get_structured_tools())
    .with_retry(stop_after_attempt=3)
)

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
        call_args = call['args']
        result, entry = execute_call_by_name(call_name, call_args)
        new_trace.append(entry)

        if result.get('success'):
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
        'trace': new_trace,
        'results': new_results,
        'loop_count': 1
    }

#==============================================================
# 강제 답변 생성 노드(max turn 넘어가는 경우)
#==============================================================
def force_final_answer(state: AgentState):
    '''max turn 넘는 경우 강제 답변 생성 노드'''
    system_message = SystemMessage(content=SYSTEM_PROMPT)
    response = llm.invoke([system_message] + state['messages'])
    return {'messages': [response]}

#==============================================================
# 답변 마무리 및 로그 기록 노드
#==============================================================
def finalize(state: AgentState):
    '''답변 마무리 및 로그 기록 노드'''
    answer_text = state['messages'][-1].text

    finish(
        interaction_id=state['interaction_id'],
        question=state['question'],
        answer=answer_text,
        trace=state['trace'],
        results=state['results'],
    )

    return {}

#==============================================================
# 분기 결정
#==============================================================
def should_continue(state: AgentState):
    '''분기 결정 함수'''
    last_message = state['messages'][-1]

    # 도구 호출 없는 경우 finalize 노드로 라우팅
    if not getattr(last_message, 'tool_calls', None):
        return 'end'
    # 이외 execute_call로 함수 호출
    return 'execute_tools'

def after_tools(state: AgentState):
    '''Turn 확인'''
    # 루프 횟수 초과 시 force_final_answer 노드로 라우팅
    if state['loop_count'] >= MAX_TURNS:
        return 'force_final_answer'

    return 'call_llm'

def get_graph() -> CompiledStateGraph:
    '''workflow 조립 후 그래프 반환'''
    workflow = StateGraph(AgentState)

    workflow.add_node('call_llm', call_llm)
    workflow.add_node('execute_tools', execute_tools)
    workflow.add_node('force_final_answer', force_final_answer)
    workflow.add_node('finalize', finalize)

    workflow.add_edge(START, 'call_llm')
    workflow.add_conditional_edges(
        'call_llm',
        should_continue,
        {
            'execute_tools': 'execute_tools',
            'end': 'finalize',
        }
    )

    workflow.add_conditional_edges(
        'execute_tools',
        after_tools,
        {
            'call_llm': 'call_llm',
            'force_final_answer': 'force_final_answer'
        }
    )

    workflow.add_edge('force_final_answer', 'finalize')
    workflow.add_edge('finalize', END)

    return workflow.compile()

graph = get_graph()

def ask(
    question: str,
    history: list[dict] | None = None,
) -> dict:
    """질문 하나 처리 / history는 {'role', 'text'} 목록"""
    interaction_id = uuid.uuid4().hex[:12]

    messages = []

    for item in history or []:
        if item['role'] == 'user':
            messages.append(HumanMessage(content=item['text']))
        elif item['role'] in ('model', 'assistant'):
            messages.append(AIMessage(content=item['text']))

    messages.append(HumanMessage(content=question))

    initial_state = AgentState(
        messages=messages,
        interaction_id=interaction_id,
        trace=[],
        results=[],
        question=question,
        loop_count=0
    )

    result_state = graph.invoke(initial_state)

    return {
        'answer': result_state['messages'][-1].text,
        'trace': result_state['trace'],
        'results': result_state['results'],
        'interaction_id': result_state['interaction_id'],
    }
