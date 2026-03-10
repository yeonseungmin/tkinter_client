"""
[파일경로]/chat_ui.py
[역할]
    파이썬의 GUI 패키지인 tkinter를 이용하여 채팅 GUI 를 구성하겠다.

[기능]
    사용자 입력창
    대화 출력창
    전송 버튼
    엔터키 전송

"""
import tkinter as tk

# from 파일 import 함수, 변수
from tkinter.scrolledtext import ScrolledText
from chat_service import chat

class ChatUI: 
    # 파이썬은 메서드 선언 시 def 키워드 사용
    def __init__(self, root):
        self.root= root # 현재 만들고 있는 채팅창이 어느 윈도우에 붙을지 결정
        self.root.title("Local LLM Chat")

        # 채팅 출력창
        self.chat_area = ScrolledText(root, wrap=tk.WORD, height=20, width=70)
        self.chat_area.pack()   # UI 컴포넌트인 위젯을 화면에 배치하는 함수 (pack())

        #채팅 입력창
        self.input_box = tk.Entry(root, width=60)
        self.input_box.pack(side = tk.LEFT,padx=10, pady=10)

        #Enter key 이벤트
        self.input_box.bind("<Return>",self.send_message)

        #메세지 전송 버튼
        self.send_button = tk.Button(root, text="Send",command=self.send_message)
    
    def append_chat(self,sender,message):
        self.chat_area.insert(tk.END,f"{sender}:{message}") # 채팅창의 맨 마지막에 새로운 메시지 껴넣기
        self.chat_area.see(tk.END) # 메시지 추가후 스크롤을 맨 아래로 자동으로 이동시켜 메시지가 보이도록

    def send_message(self,event=None):
    
    # 사용자로부터 입력을 받아 Llama 모델에 질문을 하고 , 이 질문이 Ollama 서버에 전달됨 -> llama에게 전달
        user_message = self.input_box.get()

        if not user_message.strip():    # 빈 칸이거나, 공백일 경우 , 함수종료
            return
    
        self.append_chat("dong",user_message)    # 채팅 창에 메시지 반영
        self.input_box.delete(0,tk.END)     #내가 입력한 채팅 메시지 지우기

        response = chat(user_message) # 모델 호출
        self.append_chat("AI",response)
