# 아직 정의 되지 않은 타입명을 평가하지 말고, 일단 내부적으로 문자열처럼 다뤄서 에러나지 않도록 처리
#from __future__ import annotations

#class Dog:
#  def __init__(self, dog:Dog): # dog 변수에 Dog 파이선 입장에서는 
                                # 모순(자바랑 다르게 정의하고 써야함) 그래서 "Dog"

#queue 모듈안의 요소들을 모두 가져온다..( but반드시 사용시엔 queue.x, queue.함수() )
from __future__ import annotations
import json # spring 의 ObjectMapper 와 목적이 동일한 모듈
            # json.load(), json.dump()
from typing import Generator, List, Dict
import requests




from config import (
  OLLAMA_BASE_URL, 
  OLLAMA_TAGS_URL,
  OLLAMA_GENERATE_URL,
  OLLAMA_CHAT_URL,
  REQUEST_TIMEOUT_SECONDS
)
# 딕셔너리를 가리키는 alias 기법 DTO 처럼 사용
Message = Dict[str,str]

#-----------------------------------------------------
# Qllama에 현재 설치되어 있는 모델 목록을 조회하는 함수 정의
# 반환값 예) "llama3.2:3b", "llama3.1"
# 주의) Ollama 서버가 꺼져 있거나 연결이 안되면 예외 발생 
# --> 구글클라우드에 ai 설치X, 로컬로 개발할때만
#-----------------------------------------------------

# list(전통), List는 목적이 같은 리스트 이지만, 
# List는 java의 제너릭처럼 타입을 강제할 수 있음(신규 제너릭타입 명시)
def fetch_model_names() -> List[str]: 
  
  # Ollama으로 부터 ai모델 목록 가져오기(Http통신)
  response = requests.get(OLLAMA_TAGS_URL, timeout=30) #요청후 후 최대 30초 동안만 응답을 기다림..
  response.raise_for_status() #400, 500 번대가 응답코드로 받아오게되면 예외를 발생시킴 raise=java throws

  # 예외가 발생하지 않았다면, json 으로 구성된 문자열 응답정보를 python 자료형 중 
  # 가장 흡사한 자료형인 딕셔너리로 변환
  data = response.json() #json -> dict
  models = data.get("models", [])  # 딕셔너리 데이터 중 models 라는 키값으로 데이터 추출, 원래는 List가 반환되어야 하지만
                          # 만일 존재하지 않을 경우 [] 비어있는 리스트로 대신
  
  # names 는 이름만 담아진 리스트임
  # 실행순서 , 뒤에 오는 for문을 먼저 수행하되 조건에 맞는 키만 추출, 그리고 나서 for문 앞의 처리가 동작
  # name값이 없을 경우 공백문자로 대신, 있을 경우 앞뒤 공백 제거하여 반환..
  # 이러한 선언적 프로그래밍 방식의 리스트 처리 문장을 가리켜 ★★★ List Comprehension 이라함..
  names = [ model.get("name","").strip() for model in models if model.get("name") ]

  # 추출한 요소들이 중복일 경우 중복 제거 및 요소들간 정렬까지 .. "llama3.1", "llama3.1", "llama3.2"
  # 중복제거+오름차순 정렬 까지 포함한 처리 ..
  unique_soreted_names = sorted(set(names))
  return unique_soreted_names

#-----------------------------------------------------
# 연결 실패시 사용자에게 보여줄 친절한 에러 메시지 처리 함수
#-----------------------------------------------------
def build_connection_error_message(e) -> str:
  return (f"에러 발생함: {str(e)}")

#-----------------------------------------------------
# Ollama의 /api/generate 앤드포인로 스트리밍 방식으로 호출
# [Generator]
# 1) 함수를 제너레이터로 선언하면 일반 함수와는 틀리게 동작, 호출되는 순간 제너레이터 객체를 반환
# 2) 함수의 내부에서 yield가 호출될때마다 값을 반환하고 잠시 정지한다(우리의 경우 main() 함수가 업무를 할떄까지 기다려줌)
# 3) 멈춰있다가, 호출한쪽에서 이 제너레이터 메서드를 다시 호출하는 순간 멈춤이 풀리고(재개됨) 다음 yield를 만날때까지..
#    반복문이 한꺼번에 돌지 않고, 외부의 실행부에서 호출할때 마다 어디까지 반복했는지를 기억해서 그 다음 반복을 수행..
#-----------------------------------------------------
"""
def stream_generate(model:str, prompt:str) -> Generator[str, None, None]: # -> 반환형!!
  
  #서버에 전달할 질문 즉 프롬프트를 생성하자
  payload = {
    "model": model, 
    "prompt": prompt,
    "stream": True # 응답을 한번에 다 받는게 아니라, 생성되는 텍스트를 조금씩 실시가능로 받겠다는 뜻..
  }

  # 질문할때 POST 요청하기
  with requests.post(
    OLLAMA_GENERATE_URL, 
    json = payload, stream=True, 
    timeout = REQUEST_TIMEOUT_SECONDS) as response :
      response.raise_for_status() # 400 또는 500 애러코드 발생시 예외 발생 시킴

      # iter_lines()는 서버가 보낸 응답을 한줄씩 읽어옴
      # decode_unicode=True 는 바이트(bytes) 가 아닌 문자열로 디코딩해서 받겠다는 뜻
      for line in response.iter_lines(decode_unicode=True):
         
        #스트리밍 중간에 공백 줄이 들어올 수 있으므로 방어적으로 처리하는 코드
        if not line:
          continue # 반복문 건너띠어서 코딩
        
        data=json.loads(line)
        piece=data.get("response", "") #data 딕셔너리 안의 key response 인 값을 꺼내기

        if piece:
          yield piece # 쉰다(양보), return이 생략되어 있다 할지라도 , piece는 호출부로 반환됨



"""
#-----------------------------------------------------
# Ollama의 /api/chat 앤드 포인트를 이용한 스트리밍 방식의 채팅
# [Generator]
# 인수 1 - 제너레이터를 통해 외부에 내보낼 데이터 타입
# 인수 2 - 제너레이터로 전달할 데이터를 받을 파라미터 (현재로는 사용안함)
# 인수 3 - 제너레이터 반복을 마치고 최종적으로 리턴할 데이터의 자료형
#-----------------------------------------------------
def stream_chat_api(model:str,messages:List[Message] ) -> Generator[str,None,None]:

  payload={
    "model": model,
    "messages": messages,
    "stream": True
  }
  
  #Post 로 요청하기
  with requests.post(OLLAMA_CHAT_URL,json=payload,stream=True,timeout=REQUEST_TIMEOUT_SECONDS) as response:
    response.raise_for_status() # 400,500 코드 발생시 예외 발생 시킴

    #서버가 보내온 응답 정보 읽기 iter_lines()
    # decode_unicode = True 바이트가 아닌 문자열로 디코딩하여 받겠다.
    for line in response.iter_lines(decode_unicode=True) :
      if not line:
        continue
      
      #json 으로 전송된 문장을 딕셔너리로 변환
      data =json.loads(line) # json -> dict 로 변환
      message_obj=data.get("message",{})
      piece =message_obj.get("content","")

      if piece:
        yield piece  #piece 반환하면서 잠시 멈춤
      
      
