"""
[파일명] chat_service.py

[ 역할 ]
    chat_ui.py는 디자인, 즉 View 영역이므로, api직접 적으로 다루게 되면 즉 너무 전문적인 지식을 보유해야 하므로 
    추후 디자인이 교체될 경우 api 연동 로직도 함께 날아감..(디자인과 로직은 분리시켜야 하므로 service 계층이 필요함)
"""
from ollama_api import stream_chat_api #스트리밍 방식으로 응답을 받아오는 함수 가져오기 
from typing import Generator,Dict,List,Any
from config import MAX_HISTORY_MESSAGES,SYSTEM_PROMPT
import json
from desktop_tools import OLLAMA_TOOL_DEFINITION, execute_tool

Message=Dict[str, str] #메시지 한건이 담김

#---------------------------------------------------------------------
# 대화내역에 대한 정제처리(시간이 지날수록 대화내역 리스트가 너무 방대해지므로, 최근 내역 N건을 보내도록 처리...)
#---------------------------------------------------------------------
def _normalize_history(history: List[Message])-> List[Message]:
    cleaned: List[Message]=[] #정제된 대화를 담게될 리스트 

    #매개변수로 전달받은 대화내역인 history 리스트를 하나씩 처리 
    for item in history:
        role =str(item.get("role","")).strip()
        content = str(item.get("content", "")).strip()

        if not role or not content:
            continue

        cleaned.append({
            "role":role,
            "content": content
        })  #java의 List .add() 동일

    #현재 cleaned 에 누적된 대화내역중 최근 MAX_HISTORY_MESSAGES 갯수만큼만 잘라서 반환
    return cleaned[-MAX_HISTORY_MESSAGES]

#---------------------------------------------------------------------
# ai 모델은 사용자의 질문을 기억하는 능력이 없다. 따라서 채팅 시 사용자와의 대화 맥락(Context)을
# 유지하려면, 기존 대화 내역을 함께 전송해야 한다..
# 최종 프롬프트 생성 함수 (시스템 프롬프트(페르소나)+최근대화이력+현재 사용자질문)
#---------------------------------------------------------------------
def build_final_prompt(user_message:str, history:List[Message]) -> List[Message] :

    messages: List[Message]=[] # /api/chat 으로 보낼 메시지 목록 보관용 리스트 

    #------------------------
    # 1) 시스템 프롬프트
    #------------------------
    messages.append({
        "role":"system",
        "content":SYSTEM_PROMPT.strip()
    })

    #------------------------
    # 2) 최근 대화 이력
    #------------------------
    safe_history =_normalize_history(history) # 정제처리된 최근 대화이력이 반환..

    if safe_history: #이전 대화가 존재할 경우만..
        for msg in safe_history:
            role=msg["role"]
            content=msg["content"]

            if role in ("user", "assistant", "system"):
                messages.append({
                    "role":role,
                    "content":content
                })
            else:
                messages.append({
                    "role":"user",
                    "content":content
                })
    #------------------------
    # 3) 현재 사용자질문
    #------------------------
    messages.append({
        "role":"user",
        "content":user_message
    })    

    return messages

#---------------------------------------------------------------------
# 모델이 전송한 메시지 목록을 실제 파이썬 함수로 실행 
# 다시 모델에게 전다랄 tool 메시지 목록을 작성 
#---------------------------------------------------------------------
def _execute_tool_calls(tool_calls: List[Dict[str, Any]]) -> List[Message] :
    tool_message = List[Message] =[] #  tool 실행 후 그 결과 메시지를 담을 리스트

    #ai 모델이 요청한 여러개의 도구 호출 명령(tool_calls)을 하나씩 꺼내어 처리..
    for tool_call  in tool_calls:
        function_info = tool_call.get("function",{})
        function_name=str(function_info.get("name", "")).strip()  #모델이 실행하라고 한 함수의 이름 추출        
        arguments   = function_info.get("arguments", {})  

        #일부 모델은 arguments 를 문자열로 json 형태로 주는 경우가 있으므로, 그럴 경우를 대비해 파이썬 딕셔너리로 변환
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)     
            except Exception as e:
                arguments={} #에러가 나더라도 빈값으로 처리 

        #개발자가 정의해놓은 파이선 함수를 실행하고, 그 결과를 받음
        result = execute_tool(function_name=function_name, arguments=arguments)

        #ai에게 보낼 메시지 작성 
        tool_message.append({
            "role":"tool",
            "content" :  str(result)
        })        

    return tool_message

#---------------------------------------------------------------------
# 사용자의 메시지가 메모장에 대한 요청인지 판별 
#---------------------------------------------------------------------
def _is_editor_request(user_message: str) -> bool:
    
    #사용자가 입력한 메시지에 대한 공백, 소문자 처리 
    msg=user_message.strip().lower()

    #메모장 자체를 의미하는 단어 목록
    target_keywords=[
        "메모장", "notepad", "노트패드", "editor", "에디터","텍스트 편집기", "memo장"
    ]

    #실제로 열어달라는 동작을 의미하는 단어 목록
    action_keywords=[
        "열어", "열어줘", "열어줄래?", "실행", "실행해", "실행해줘", "켜", "켜줘", "띄워", "띄워줘", "open", "run","start","launch"
    ]

    #any: 단 하나라도 True가 있는가? 를 판단하는 파이썬 내장 함수 , 조건이 하나라도 True이면 전체 True
    has_target = any(keyword in msg for keyword  in target_keywords)        
    has_action = any(keyword in msg for keyword  in action_keywords)            

    return has_target and has_action




#---------------------------------------------------------------------
# 최종적으로 생성된 프롬프트를 이용한 서버 전송 
# 이 함수는 UI에서 호출함, 만일 이 함수가 존재하지 않으면 View영역인 chat_up.py가 직접 api를 제어하는 일이 발생함..
#---------------------------------------------------------------------
def stream_chat(model: str, user_message: str, history: List[Message]) -> Generator[str, None, None]:
    
    #최종 프롬프트인 List
    messages = build_final_prompt(user_message=user_message, history=history)

    #Ollama 서버에 메시지를 전송하기 전에, tool calling인지 여부를 판단
    tools = OLLAMA_TOOL_DEFINITION if _is_editor_request(user_message) else None

    # Tool calling 이 필요없는 일반 대화라면 기존처럼 바로 스트리밍 응답만 처리
    if tools is None:
        for chunk in stream_chat_api(model, messages, tools=None):
            piece = str(chunk.get("content",""))     
            if piece:
                yield piece
        return #일반 메시지일경우 더이상 코드 진행하지 않음..

    collected_tool_calls: List[Dict[str, Any]]=[]

    #Tool calling일 경우의 처리 시작 
    for chunk in stream_chat_api(model, messages, tools=tools):
        piece = str(chunk.get("content")) #ai 의 답변 메시지안에 있는 내용 꺼내기 

        if piece:
            #........
            yield piece #사용자 화면에 반영할 메시지 조각 반환

        tool_calls = chunk.get("tool_calls") or []       

        #만일 ai가 tool을 호출햇다면...
        if tool_calls:
            collected_tool_calls.extend(tool_calls) #List 요소추가할때 add(), extend()
            print(f"{collected_tool_calls}")

    #위의 for문 실행 후에도 collected_tool_calls 안에 아무것도 채워진 것이 없다면, ai 도구 실행을 호출하지 않음으로 본다
    if not collected_tool_calls:
        return

    _execute_tool_calls(collected_tool_calls)