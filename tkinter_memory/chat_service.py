"""
파일명: chat_service.py

[역할]
    이 파일은 채팅 서비스 계층(Service Layer, 서비스 계층)
"""
from __future__ import annotations
import json
from typing import Any, Dict, Generator, List
from config import MAX_HISTORY_MESSAGES, SYSTEM_PROMPT
from desktop_tools import OLLAMA_TOOL_DEFINITIONS, execute_tool
from ollama_api import stream_chat_api #스트리밍 방식으로 응답을 받아오는 함수 가져오기

Message=Dict[str, Any] #대화 한 건을 표현하는 딕셔너리 예) {"role":"user", "content":"hello"} 

#---------------------------------------------------------------------
# [ history 자료 정제 ]
#   - role, content 키가 있는 항목만 추려냄
#   - 너무 긴 전체 history 중 최근 N개만 남김
#---------------------------------------------------------------------
def _clean_history(history: List[Message])-> List[Message]:

    cleaned: List[Message]=[]

    #전달받은 history 리스트를 하나씩 검사
    for item in history:
        # item 딕셔너리에서 key가 role인 값을 꺼내되, 값이 없으면 "" 빈 문자열 사용
        # str()로 문자열 변환하면서 앞뒤 공백 제거 
        role = str(item.get("role","")).strip()
        content = str(item.get("content","")).strip()

        # role 또는 content 가 비어 있으면 아래 처리 무시하고 다음번 수행으로 진행 
        if not role or not content: 
            continue

        cleaned.append({"role":role, "content":content})

    # 최근 MAX_HISTORY_MESSAGES 건만 사용함 
    # 예를 들어 MAX_HISTORY_MESSAGES =6 이라면 가장 최근 6개의 대화만 사용
    # 파이썬의 슬라이싱 문법(slicing)- 리스트의 일부분을 쉽게 잘라내는 방법 
    # 사용법 cleaned[시작:끝] 
    # 인덱스: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    # 데이터: [A, B, C, D, E, F, G, H, I, J]
    # cleaned[-6:] 일 경우 제일뒤를 -1로 생각함 따라서 ['E', 'F', 'G', 'H', 'I', 'J']가 추출됨
    return cleaned[-MAX_HISTORY_MESSAGES:]

#---------------------------------------------------------------------
# [ 최종 프롬프트를 생성하는 함수 ]
#   - 최종 프롬프트 = 시스템 프롬프트 + 최근 대화 이력 + 현재 사용자 질문
#   - LLM은 상태를 기억하지 않으므로 이전 대화를 다시 보내야 문맥(Context)을 유지할 수 있음
#---------------------------------------------------------------------
def build_final_prompt(user_message:str, history:List[Message])-> List[Message]:
    
    safe_history = _clean_history(history) #먼저 history 데이터를 안전하게 정리 
    messages: List[Message]=[] # /api/chat 으로 보낼 메시지 목록

    # ---------------------------------------
    # 1. 시스템 지시문 추가
    #  system role 은 모델에게 전체 대화에 대한 규칙/행동지침을 전달하는 용도 
    # ---------------------------------------
    messages.append({
        "role":"system",
        "content": SYSTEM_PROMPT.strip()
    })

    # ---------------------------------------
    # 2. 이전 대화 이력 추가
    # ---------------------------------------
    if safe_history: #이전 대화가 존재하는 경우 

        # 대화 하나씩 순회
        for msg in safe_history:
            # role과 content 추출 
            role=msg["role"]
            content=msg["content"]

            if role in ("user", "assistant", "system"):
                messages.append({
                    "role": role,
                    "content":content
                })            
            else:
                #그 외의 role (예: custom role 등)
                messages.append({
                    "role":"user",
                    "content": content
                })
    
    # ---------------------------------------
    # 3. 현재 질문 추가
    # ---------------------------------------
    messages.append({
        "role":"user",
        "content": user_message.strip()
    })
    
    return messages



######################################################################
# 매개변수로 넘어오는 [ tool_calls 데이터 샘플 ] 
# [
#     {
#         "id": "call_1",
#         "type": "function",
#         "function": {
#             "name": "open_program",
#             "arguments": {
#                 "program_name": "notepad"
#             }
#         }
#     },
#     {
#         "id": "call_2",
#         "type": "function",
#         "function": {
#             "name": "open_program",
#             "arguments": {
#                 "program_name": "calculator"
#             }
#         }
#     }
# ]

# 1) 모델이 답변으로 보내온 tool 목록을 실제 파이썬 함수로 실행
# 2) 다시 모델에게 전달할 메시지 목록 반환
######################################################################
def _execute_tool(tool_calls: List[Dict[str, Any]]) -> List[Message]:

    tool_messages: List[Message] = [] #tool 실행 결과를 담을 리스트 

    # ai 모델이 요청한 여러 개의 도구 수 만큼 반복하여 툴 호출
    for tool_call in tool_calls:         
        function_info = tool_call.get("function", {}) # 호출할 함수의 정보(이름, 매개변수)를 가져오기
        function_name = str(function_info.get("name", "")).strip() #모델이 실행하라고 한 함수의 이름 추출
        arguments = function_info.get("arguments", {}) or {} # 함수의 매개변수를 가져오기, 없으면 빈 딕셔너리로 대체

        # 일부 모델은 arguments 를 문자열 JSON 형태로 주는 경우가 있으므로, 그럴 경우를 대비해 파이썬 딕셔너리로 변환
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except Exception:
                arguments = {} #에러 나면 빈 값으로 처리 

        #만약 어떻게든 딕셔너리 형태가 아니라면 안전하게 빈 딕셔너리로 초기화
        if not isinstance(arguments, dict):
            arguments = {}

        #-----------------------------------------------------    
        # [1] 툴 실행 - 우리가 정의해 둔 파이썬 함수(open_editor)를 실행하고 결과값을 받음
        #-----------------------------------------------------
        result = execute_tool(function_name=function_name, arguments=arguments)

        #-----------------------------------------------------    
        # [2] 모델에게 전달할 메시지 생성 (AI 가 요청한 툴을 실행했고 그 결과는 이것이다 라고 알려주기 위함)
        #-----------------------------------------------------
        tool_messages.append({
            "role": "tool",
            "content": str(result)
        })
    return tool_messages

######################################################################
# [ 메모장 실행 요청인지 1차 판별 ]
######################################################################
def _is_editor_request(user_message: str) -> bool:
    text = user_message.strip().lower()

    # 메모장 자체를 의미하는 단어 목록
    target_keywords = [
        "메모장", "notepad", "노트패드", "editor", "에디터", "텍스트 편집기"
    ]

    # 실제로 열어달라는 동작을 의미하는 단어 목록
    action_keywords = [
        "열어", "열어줘","열어줄래?" ,"실행", "실행해", "실행해줘", "켜", "켜줘",
        "띄워", "띄워줘", "open", "run", "start", "launch"
    ]

    # any : 단 하나라도 True 가 있는가? 파이썬 내장 함수 - 조건이 하나라도 True이면 True을 반환
    # 1) for keyword in target_keywords : 리스트에 있는 단어들을 하나씩 꺼내어 keyword에 담음
    # 2) keyword in text : 꺼낸 그 단어(keyword) 가 text에 포함되어 있는지 확인
    has_target = any(keyword in text for keyword in target_keywords)
    has_action = any(keyword in text for keyword in action_keywords)

    return has_target and has_action


#---------------------------------------------------------------------
# 1) 최종 프롬프트로 모델에게 메시지 전송하고, 스트리밍 방식으로 답변 처리하기
# 2) tool calling의 경우 툴 호출하기
#---------------------------------------------------------------------
def stream_chat(model:str, user_message:str, history: List[Message])-> Generator[str, None, None]:

    #-------------------------------------------
    # [1] 최종 프롬프트 생성 및 Tool 정보 담기
    #-------------------------------------------    
    final_prompt = build_final_prompt(user_message=user_message, history=history) #최종 프롬프트 생성
    
    # Tool Calling 여부 판단 및 Tool 정보 담기
    tools = OLLAMA_TOOL_DEFINITIONS if _is_editor_request(user_message) else None # 파이썬의 삼항연산자(조건부 표현식)
                                                                            # _is_editor_request()가 True이면 tools에 
                                                                            # OLLAMA_TOOL_DEFINITIONS 담고 아니면, None 담음
    #-------------------------------------------
    # [2] Tool Calling 이 아닌 경우, AI 모델에게 메시지만 보내기
    #-------------------------------------------
    # Tool Calling 이 필요 없는 일반 대화라면 기존처럼 바로 스트리밍 응답만 처리
    if tools is None: #tool calling 요청이 아니라면
        for chunk in stream_chat_api(model=model, messages=final_prompt, tools=None):
            piece = str(chunk.get("content", ""))
            if piece:
                yield piece
        return

    #-------------------------------------------
    # [3] Tool Calling 인 경우, Tool 정보 포함시켜 보내고 답변 받기
    #-------------------------------------------
    tool_result_messages: List[str] = [] # AI에 보낼 메시지 모아놓을 곳
    tool_list: List[Dict[str, Any]] = [] # AI의 Took calling 호출 명령들을 담을 리스트(_execute_tool 호출 시 사용)

    # 채팅 메시지와 도구 정보를 보내고, 답변을 스트리밍으로 받기
    for chunk in stream_chat_api(model=model, messages=final_prompt, tools=tools):
        # chunk에 담겨진 데이터 예시    
        # {
        #   "role": "assistant",
        #   "content": "",
        #   "tool_calls": [
        #     {
        #       "id": "call_123",
        #       "type": "function",
        #       "function": {
        #         "name": "open_editor",
        #         "arguments": "{}"
        #       }
        #     }
        #   ]
        # }

    #-------------------------------------------
    # [4] AI의 답변정보 및 AI가 답변한 툴 정보 꺼내기
    #-------------------------------------------
        piece = str(chunk.get("content", "")) # 답변 내용 꺼내기 

        if piece: 
            tool_result_messages.append(piece) #AI 에게 보낼 메시지 리스트에 추가 
            yield piece #사용자 화면으로 즉시 반환

        tool_calls = chunk.get("tool_calls") or [] # AI 답변한 Tool 호출 정보 꺼내기

        if tool_calls: #도구 호출 명령이 있다면
            tool_list.extend(tool_calls) # []에서 벗겨내고, 리스트에 추가 

    # 위 반복문 실행 뒤에, 모델의 도구 호출이 발견되지 않으면 여기서 종료
    if not tool_list:
        return

    #-------------------------------------------
    # [5] 툴 실행하고 AI 모델에게 툴 수행 결과 메시지 보내기
    #-------------------------------------------
    result=_execute_tool(tool_list) # 툴 실행

    # 메시지 만들기
    final_prompt.append({
        "role": "assistant",
        "content": "".join(tool_result_messages).strip(), #모아놓은 대화내용
        "tool_calls": tool_list, #모아놓은 도구 명령어 내용
    })
    
    final_prompt.extend(result) # 실제 파이썬 함수 실행하고 그 결과 메시지를  final_prompt 에 추가    

    # tool 실행 결과를 모델에게 다시 보내 최종 자연어 답변을 받음, ai모델은 "아 메모장이 열렸구나!" 라는 사실을 알게되고 , 
    # 이제 사용자에게 최종적으로 자연스러운 마무리 답변을 보내옴
    for chunk in stream_chat_api(model=model, messages=final_prompt, tools=None):
        piece = str(chunk.get("content", ""))
        if piece:
            yield piece