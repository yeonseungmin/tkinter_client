"""
[파일 경로]
    /chat_service.py

[역할]
    GUI인 즉 View 영역에서 모델 영역의 지식을 너무 많이 갖게 하지 않게 위함 
    DI 를 낮추기 위함

"""
from ollama_api import ask
#-----------------------------------------------
# Ai 의 역할을 부여하는 페르소나 설정!! 
#-----------------------------------------------
SYSTEM_PROMPT="""
너는 반드시 무조건 존댓말로 답변해야 해
답변 끝에는 Sir를 붙여서 대답해
답변은 반드시 한국어로 해줘
너의 성별은 여자이다.
강동훈 이라고 입력하면 "세계 최고 귀요미" 라고 답해야 해
"""
#-----------------------------------------------
# 서버로 전송할 프롬프트 만들어 주는 함수
#    서버로 내용이 전송되기 때문에 들여쓰기 = 메모리 낭비
#-----------------------------------------------
def build_prompt(user_message:str)-> str:
    prompt = f"""
{SYSTEM_PROMPT}

사용자 질문
{user_message}

답변:
    """
    return prompt

def chat(user_mesaage: str) -> str:
    # 원하는 메세지를 넣으면, 프롬프트 생성
    prompt = build_prompt(user_mesaage)

    response =ask(prompt) # 페르소나 + 질문과 함께 Ollama 서버에 전송
    return response