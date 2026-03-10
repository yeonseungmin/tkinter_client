
from ollama_api import fetch_model_names
from ollama_api import stream_generate
def main():
    # models = fetch_model_names() # 현재 우리가 Ollama에 설치한 ai 모델들의 이름을 보유한 List반환
    # for model in models:
    #     print(model)

    generate=stream_generate("llama3.2:3b","아시아의 경재력 상위 3개국")
    for piece in generate:
        # 파이썬의 print() 자동으로 줄바꿈이 포함되어 있다.. 따라서 줄바꿈 없애기
        print(piece, end="",flush=True)



# 아래의 main() 호출 코드는 , 외부에서 from으로
# main 함수 호출일 경우에만 동작하라!!
# 모든 파이썬 .py 안에는 __name__ 변수 기본적으로 선언되어 있다.
# 만일 개발자가 터미널에서 python main.py 를 실행하면 이때 __name__ 변수에는 __main__ 값이 자동으로 채워짐

if __name__ =="__main__":
    main()