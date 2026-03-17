"""
[파일명] chat_service.py

[역할]
    chat_ui.py는 디자인, 즉 View 영역이므로, api를 직접적으로 다루게 되면 즉 너무 전문적인 지식을 보유해야 하므로
    추후 디자인이 교체될 경우 api 연동 로직도 함께 날아감..(디자인과 로직은 분리시켜야 하므로 service 계층이 필요함)
"""
from ollama_api import stream_chat_api  # 스트리밍 방식으로 응답을 받아오는 함수 가져오기
from typing import Generator ,Dict,List
from config import MAX_HISTORY_MESSAGES,SYSTEM_PROMPT

Message = Dict[str,str]



#-------------------------------------------------------
# 대화 내역에 대한 정제 처리 ( 시간이 지날 수록 대화내역 리스트가 너무 방대해지므로, 최근 내역 N 건을 보내고 처리)
#-------------------------------------------------------
def _normalize_history(history: List[Message])-> List[Message]:
    cleand: List[Message]=[]    # 최근 대화 N건을 넣게 될 리스트 ( 정제용)

    # 매개변수로 전달받은 대화 내역인 history 리스트를 하나씩 처리
    for item in history :
        role =str(item.get("role","")).strip()
        content = str(item.get("content","")).strip()

        if not role or not content:
            continue

        cleand.append({
            "role":role,
            "content": content
        }) # java의 List.add() 동일

    return cleand[ -MAX_HISTORY_MESSAGES: ] # 끝에 기준으로 부터 (MAX_HISTORY_MESSAGES) 건





#-------------------------------------------------------
#   ai 모델은 사용자의 질문을 기억하는 능력이 없다. 따라서 채팅 시 사용자와의 대화 맥락(Context)을 유지
#   기존 대화 내역을 함께 전송해야 한다.
#   최종 프롬프트 생성 함수( 시스템 프롬포트 (페르소나)+ 최근 대화 내역 이력)
#-------------------------------------------------------        
def build_message(user_message:str,history:List[Message]) -> List[Message]:

    # /api/chat 으로 보낼 메시지 목록 보관용 리스트
    messages: List[Message] =[]

    #------------------
    #   1) 시스템 프롬포트
    #------------------
    messages.append({
        "role":"system",
        "content":SYSTEM_PROMPT.strip()
    })

    #------------------
    #   2) 최근 대화 이력
    #------------------
    safe_history = _normalize_history(history) # 정제처리된 최근 대회 이력이 반환

    if safe_history: # 이전 대화가 존재할 경우만..
        for msg in safe_history:
            role=msg["role"]
            content=msg["content"]

            if role in ("user","assistant","system"):
                messages.append({
                    "role":role,
                    "content":content
                })
            else:
                messages.append({
                    "role":"user",
                    "content":content
                })



    #------------------
    #   3) 현재 사용자 질문
    #------------------
    messages.append({
        "role":"user",
        "content":user_message
    })

    return messages

#---------------------------------------------------------
# 최종적으로 생성된 프롬포트를 이용한 서버 전송
# 이 함수는 UI 에서 호출함, 만일 이 함수가 존재하지 않으면 View 영역인 chat_up.py 가 직접 api 제어
#---------------------------------------------------------
def stream_chat(model: str, user_message: str,history:List[Message]) -> Generator[str, None, None]:

    # gen = stream_generate(model, user_message)

    # for piece in gen:

    messages = build_message(user_message=user_message,history=history)

    for piece in stream_chat_api(model,messages):
        yield piece

    
    