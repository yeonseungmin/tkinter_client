
from ollama_api import stream_generate

def main():
    #gen=stream_generate("llama3.2:3b", "아시아의 경제력 상위 5개국을 알려줄래?")

    #for piece in gen:
        #파이썬의 print() 자동으로 줄바꿈이 포함되어 있다..따라서 줄 
        #end=""에 의해 줄바꿈을 처리하지 않아도, 현재 스트림에 들어있는 데이터를 바로 바로 화면에 출력
    #    print(piece, end="", flush=True)

    #models=fetch_model_names() #현재 우리가 Ollama에 설치한 ai모델들의 이름을 보유한 List반환 
    
    #for model in models:
    #    print(f"ai모델명 : {model}")

#아래의 main()호출 코드는, 외부에서 from으로 임포트할때가 아닌, 
#main함수 호출일 경우에만 동작하라!!
#모든 파이썬 .py 파일안에는 __name__ 변수 기본적으로 선언되어 있다..
#만일 개발자가 터미널에서 python  main.py를 실행하면 이때 __name__변수에는 __main__ 값이 자동으로
#채워지게 되어있기 때문에, 아래의 조건을 이용하여 메인 실행할때만 원하는 코드가 실행될 수 있도록 처리 가능
if __name__ =="__main__":
    main()    