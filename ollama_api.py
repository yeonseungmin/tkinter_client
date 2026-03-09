


"""
[파일경로]
    /ollama_api.py

[역할]
    Ollama 로컬 서버에 HTTP 요청을 보내 LLM 을 호출하는 모듈
    현재는 llama 모델을 사용

[사용 API]
    POST http://localhost:11434/api/generate    Ollama가 기본으로 제공하는 api


"""

import requests

OLLAMA_URL="http://localhost:11434/api/generate"

# 인공지능 모델에게 질문하기
def ask(prompt:str, model:str="llama3.2:3b") -> str:
    """
        함수의 목적 : Ollama 서버에 질문을 보내고, 응답을 받아오는 함수
        파라미터 1 - 사용자 질문 prompt
        파라미터 2 - 사용할 모델 명 model (기본 llama)
        리턴값 - 모델 응답 텍스트

    """

# 파이썬에서는 자료구조 중 JSON 과 거의 일치하는 자료형이 있다. (dicktionaly)
    payload={
        "model": model,
        "prompt": prompt,
        "stream": False     # 스트리밍 방식이 아닌, 한꺼번에 응답 받기 

    }

    try: 
        response = requests.post(OLLAMA_URL, json = payload)     #POST 요청 dicktionaly -> json 자동변환
        response.raise_for_status() # raise 는 java throw 와 동일 (예외 발생)
                                    # 서버로부터 받은 응답 상태 코드를 확인
                                    # 만약 성공(200) 이 아닌 400,500번대 라면 raise 에러를 발생시켜 
                                    # except 블록으로 넘김 ( catch 문과 유사 )

        data= response.json() # 서버가 보내온 json 문자열을 다시 딕셔너리 형태로 변환
        return data["response"]   # response에 들어있는 여러정보 중 key 값이 response 인 것 추출
    except Exception as e:  # catch 와 유사
        return f"[Ollama Error] {str(e)}"


        