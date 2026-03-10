
#아직 정의되지 않은 타입명을 내부적으로 문자열 처리해서 , 에러를 일으키지마 , 미래에 정의할꺼야
from __future__ import annotations

from typing import List,Generator
from config import (
    OLLAMA_BASE_URL,OLLAMA_TAGS_URL,REQUEST_TIMEOUT_SECONDS,OllAMA_GENERATE_URL
)
import requests

#queue 모듈안의 요소들을 모두 가져온다 .. (BUT 반드시 사용시엔 [queue.fisrt, queue.함수()] 식으로 사용)
# import queue

import json # Spring 의 ObjectMapper 와 목적이 동일한 모듈
            # json.load(), json.dump()

#------------------------------------------
#   Ollama에 현재 설치되어 있는 모델 목록을 조회하는 함수 정의
#   주의) Ollama 서버가 꺼져있거나 연결이 안되면 예외 발생
#------------------------------------------
def fetch_model_names() -> List[lst]: # list -> List 최신

    #Ollama 으로부터 ai 모델 목록 가져오기 (Http 통신) 
    response = requests.get(OLLAMA_TAGS_URL,timeout=30)    # 요청 후 최대 30초 동안만 응답 대기

    response.raise_for_status() # 200 번대가 아닌 400~500 번대가 응답코드로 오면 예외를 발생 throw 와 동일

    # 예외가 발생하지 않았다면, json 으로 구성된 문자열 응답정보를 python 자료형 중 가장 흡사한 자료형인
    # 딕셔너리로 변환
    data = response.json()     # json -> dictionaly
    models = data.get("models",[])   # 딕셔너리 데이터 중 models 라는 키값으로 데이터 추출,
                            # 원래는 List 가 반환되어야 하지만
                            # 만일 존재하지 않을 경우 [] 비어있는 리스트로 대신
    

    #  names 는 이름만 담아진 리스트임
    #   실행 순서, 뒤에오는 for 문 먼저 수행하되 조건에 맞는 키만 추출, 그리고 나서 for 문 앞의 동작
    #   name 값이 없을경우 공백문자로 대신, 있을 경우 앞뒤 공백 제거하여 반환...
    #   이러한 선언적 프로그래밍 방식의 리스트 처리문장을 가리켜 List Comprehension 이라 함
    names = [model.get("name","").strip() for model in models if model.get("name")]


    # "llama3.1","llama3.1","llama3.2" 등 반환 될수도 (중복제거 필요)
    # 중복 제거 + 오름차순 정렬 까지 포함한 처리
    unique_sorted_names = sorted(set(names))
    return unique_sorted_names

#------------------------------------------
#   Ollama의 /api/generate 앤드포인트로 스트리밍 방식으로 호출
#   [Generater 란?] 
#       1) 함수를 제너레이터로 선언하면 일반 함수와는 틀리게 동작, 즉 호출되는 순간 제너레이터 객체를 반환
#       2) 함수의 내부에서 yield가 호출될때 마다 값을 반환하고, 잠시 정지함(우리의 경우 main() 함수가 업무를 할때까지 기다려줌)
#       3) 멈춰있다가, 호출한 쪽에서 이 제너레이터 메서드를 다시 호출하는 순간 재동작
#    반복문이 한꺼번에 돌지 않고, 외부의 실행부에서 호출될때마다 어디까지 반복됬는지를 기억해서 그 다음 반복을 수행
#------------------------------------------
def stream_generate(model:str , prompt:str) -> Generator[str,None,None]:
    #서버에 전달할 질문 즉 프롬포트를 생성하자
    payload={
        "model": model,
        "prompt": prompt,
        "stream": True # 응답을 한번에 받는게 아니라, 생성되는 텍스트를 조금씩 실시간으로 받겠다는 뜻

    }

    #Post 로 요청하기
    with requests.post(
        OllAMA_GENERATE_URL,
        json=payload,
        stream=True,
        timeout=REQUEST_TIMEOUT_SECONDS
        ) as response :
        response.raise_for_status() # 예외 발생 코드

        # iter_lines() 는 서버가 보낸 응답을 한줄씩 읽어옴
        # decode_unicode=True 바이트(bytes)가 아닌 문자열로 디코딩해서 받겠다는 뜻
        for line in response.iter_lines(decode_unicode=True):
            
            # 스트리밍 중간에 공백 줄이 들어올 수 있으므로 방어적으로 처리하는 코드
            if not line:
                continue

            data = json.loads(line)
            piece=data.get("response","") # data 딕셔너리 안에 key 값이 response 인 값을 꺼내기

            if piece:
                yield piece # return 이 생략되어 있음, piece는 호출부로 반환됨


#------------------------------------------
#   연결 실패 시 사용자에게 보여줄 친절한 에러 메시지 처리 함수
#------------------------------------------
def build_connection_error_message(e: Exception) -> str:
    return (f"에러 발생 함:{str(e)}")
            
