from __future__ import annotations #아직 정의되지 않은 타입명을 평가하지 말고, 문자열처럼 다뤄서 에러나지 않도록 처리 

import queue #queue 모듈은 스레드간 안전하게 데이터를 주고받기 위한 큐(Queue)를 제공 
            #여기서는 백그라운드 스레드가 생성한 AI 응답 정보를 메인 UI스레드로 전달하는 용도로 사용할 예정

import threading # threading 모듈은 별도의 작업 스레드를 만들기 위해 사용 
import tkinter as tk
from tkinter import ttk # ttk는 tkinter의 theme widgets 임, 
                        # 기본 tkinter 위젯보다 운영체제 스타일에 더 자연스럽고 보기 좋은 위젯 제공 
from tkinter.scrolledtext import ScrolledText
from typing import List, Dict #타입 힌트를 지원하는 List, Dict 가져오기 
from chat_service import stream_chat 
from config import APP_TITLE, DEFAULT_MODEL,UI_POLL_INTERVAL_MS
from ollama_api import fetch_model_names, build_connection_error_message
Message = Dict[str, str] #Dict[str, str]을 매번 쓰기 번거로우니 Message 라는 짧고 이해하기 쉬운 Alas 를 붙임 


class ChatUI:

    def __init__(self, root:tk.Tk):
        self.root=root #전달 받은 창 대입
        self.root.title(APP_TITLE)
        self.root.geometry("980x720")
        
        # 대화 history를 저장할 리스트 
        # 대화내역의 범위는 [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}] 처럼 
        # 지금까지 나눈 모든 대화가 누적된 리스트
        self.history: List[Message]=[] 

        self.stream_queue: queue.Queue = queue.Queue() #백그라운드 스레드에서 메인 UI 스레드로 데이터를 전달하는 Queue 

        # 파이썬의 Type Hint, |는 Optional[threading.Thread]를 줄여서 쓴 기호
        # 나중에 스레드 사용시 스레드가 있는지 확인하고 나서(안전성 때문에 사용) 실행하는 코드를 작성할 수 있음 (None 체크)
        # if self.worker_thread is not None:
        #    self.worker_thread.join() # 스레드가 있을 때만 안전하게 종료        
        self.worker_thread: threading.Thread | None = None 
        self.is_busy=False # 현재 AI 가 응답 중인지 여부를 나타내는 플래그값 , True이면 전송 버튼 등을 잠가 중복 요청을 막음 
        self.model_names: List[str]=[] #Ollama 에서 조회한 모델 이름 목록을 저장할 리스트 
        self.selected_model_var=tk.StringVar() #tkinter 위젯과 값을 바인딩 해주는 변수 객체 
        self.status_var = tk.StringVar(value="준비완료")

        #------------UI 구성 시작 ---------------------
        self._build_top_frame()
        self._build_chat_area()
        self._build_input_frame()
        self._build_status_bar()

        # 프로그램 시작 시 설치된 모델 목록을 불러옵니다.
        self._load_models()

        # 일정 주기로 Queue를 확인하여 스트리밍 응답을 화면에 출력합니다.
        self._poll_stream_queue()

    # ---------------------------------------
    # 1. 상단 영역 생성 (모델 선택 드롭다운, 모델 새로 고침 버튼, 대화 초기화 버튼)
    # ---------------------------------------
    def _build_top_frame(self) -> None:

        # 상단 영역을 담을 프레임(Frame)을 생성합니다.
        # padding=10 은 내부 여백을 의미합니다.
        top_frame = ttk.Frame(self.root, padding=10)

        # fill=tk.X 는 가로 방향으로 꽉 채우라는 뜻입니다.
        top_frame.pack(fill=tk.X)

        # "모델 선택:" 이라는 라벨(Label)을 생성합니다.
        model_label = ttk.Label(top_frame, text="모델 선택:")

        # side=tk.LEFT 는 왼쪽부터 차례대로 배치하겠다는 뜻입니다.
        model_label.pack(side=tk.LEFT)

        # 모델 선택용 콤보박스(Combobox)를 생성합니다.
        # textvariable=self.selected_model_var :
        #   콤보박스의 현재 선택값을 selected_model_var 와 연결합니다.
        # state="readonly" :
        #   사용자가 직접 텍스트를 입력하지 못하고 목록에서만 선택하게 합니다.
        # width=35 :
        #   대략적인 폭 설정
        self.model_combo = ttk.Combobox(
            top_frame,
            textvariable=self.selected_model_var,
            state="readonly",
            width=35,
        )

        # 왼쪽에 배치하고, 좌우 여백을 약간 줍니다.
        self.model_combo.pack(side=tk.LEFT, padx=(8, 12))

        # 모델 목록 새로고침 버튼 생성
        refresh_button = ttk.Button(
            top_frame,
            text="모델 목록 새로고침",
            command=self._load_models,  # 버튼 클릭 시 _load_models 실행
        )

        # 왼쪽에 배치하고 오른쪽에 약간 여백 추가
        refresh_button.pack(side=tk.LEFT, padx=(0, 8))

        # 대화 초기화 버튼 생성
        clear_button = ttk.Button(
            top_frame,
            text="대화 초기화",
            command=self._clear_chat,  # 버튼 클릭 시 _clear_chat 실행
        )

        # 왼쪽에 배치
        clear_button.pack(side=tk.LEFT)    

    # ---------------------------------------
    # 2. 중앙 채팅 출력창 생성 
    # ---------------------------------------
    def _build_chat_area(self) -> None:
        """
        중앙 채팅 출력창 생성

        ScrolledText는 스크롤 가능한 텍스트 영역입니다.
        사용자 메시지와 AI 메시지를 태그로 구분하여 시각적으로 보기 좋게 출력합니다.
        """

        # 채팅 영역 전체를 담을 프레임 생성
        # padding=(10, 0, 10, 10)은 좌,상,우,하 느낌으로 여백을 줍니다.
        chat_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))

        # fill=tk.BOTH : 가로/세로 모두 확장
        # expand=True : 남는 공간을 차지하도록 확장
        chat_frame.pack(fill=tk.BOTH, expand=True)

        # 실제 채팅 출력창인 ScrolledText 생성
        # wrap=tk.WORD : 줄바꿈 시 단어 단위로 감쌉니다.
        # font=("Arial", 13) : 글꼴과 크기
        # state=tk.NORMAL : 현재 편집 가능한 상태
        self.chat_area = ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("Arial", 13),
            state=tk.NORMAL,
        )

        # 프레임 안에 채팅창을 가득 채워 배치
        self.chat_area.pack(fill=tk.BOTH, expand=True)

        # 태그별 스타일 지정
        # user_name 태그가 붙은 텍스트는 굵게 표시
        self.chat_area.tag_config("user_name", font=("Arial", 13, "bold"))

        # ai_name 태그가 붙은 텍스트도 굵게 표시
        self.chat_area.tag_config("ai_name", font=("Arial", 13, "bold"))

        # system_name 태그는 약간 작은 크기의 굵은 글씨
        self.chat_area.tag_config("system_name", font=("Arial", 12, "bold"))

        # 시작 안내 메시지 출력
        self._append_system_message(
            "프로그램이 시작되었습니다.\n"
            "질문을 입력하고 Enter 또는 전송 버튼을 누르세요."
        )

    # ---------------------------------------
    # 3. 하단 입력 영역 생성 (사용자 입력창, 전송버튼)
    # ---------------------------------------
    def _build_input_frame(self) -> None:
        # 하단 입력 영역용 프레임 생성
        input_frame = ttk.Frame(self.root, padding=10)

        # 가로로 꽉 채우도록 배치
        input_frame.pack(fill=tk.X)

        # 여러 줄 입력이 가능한 Text 위젯 생성
        # height=4 : 4줄 높이 정도
        # font=("Arial", 13) : 폰트 설정
        self.input_box = tk.Text(input_frame, height=4, font=("Arial", 13))

        # 왼쪽에 배치, 가로/세로 확장, 오른쪽에 약간 여백
        self.input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Enter 단독 = 전송
        # Shift + Enter = 줄바꿈
        # 사용자가 Enter 키를 눌렀을 때 _on_enter_pressed 메서드가 호출됩니다.
        self.input_box.bind("<Return>", self._on_enter_pressed)

        # 전송 버튼 생성
        self.send_button = ttk.Button(
            input_frame,
            text="전송",
            command=self._send_message,  # 클릭 시 _send_message 실행
            width=12,
        )

        # 왼쪽에 배치
        self.send_button.pack(side=tk.LEFT)

    # ---------------------------------------
    # 4. 맨 아래 상태 표시 영역 생성 (준비완료, 모델 목록 불러오는 중, AI응답 생성 중..)
    # ---------------------------------------
    def _build_status_bar(self) -> None:

        # 상태 표시줄용 프레임 생성
        status_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))

        # 가로 방향으로 꽉 채움
        status_frame.pack(fill=tk.X)

        # 실제 상태 문구를 보여줄 라벨 생성
        # textvariable=self.status_var :
        # status_var 값이 바뀌면 화면 문구도 자동으로 바뀝니다.
        # anchor="w" 란? 텍스트를 왼쪽(west) 정렬로 배치
        status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            anchor="w",
        )

        # 가로로 꽉 채움
        status_label.pack(fill=tk.X)

    # ------------------------------------------------------------------
    # 5.모델 관리
    # ------------------------------------------------------------------
    def _load_models(self) -> None:

        # 상태 표시줄에 모델 목록을 불러오는 중이라는 메시지를 표시합니다.
        self.status_var.set("모델 목록 불러오는 중...")

        try:
            # ollama_api.py 의 fetch_model_names()를 호출하여 설치된 모델명을 조회합니다.
            names = fetch_model_names()

            # 조회된 모델 목록을 인스턴스 변수에 저장합니다.
            self.model_names = names

            # 콤보박스의 values 속성에 모델 목록을 넣습니다.
            # 이렇게 하면 드롭다운에서 해당 목록을 선택할 수 있습니다.
            self.model_combo["values"] = self.model_names

            # 모델이 하나도 없으면
            if not self.model_names:
                # 선택된 모델 문자열을 비웁니다.
                self.selected_model_var.set("")

                # 시스템 메시지로 모델이 없음을 안내합니다.
                self._append_system_message(
                    "설치된 모델이 없습니다.\n"
                    "예: ollama pull llama3.2"
                )

                # 상태 표시줄에도 모델이 없다고 표시합니다.
                self.status_var.set("설치된 모델 없음")

                # 함수 종료
                return

            # 기본 모델이 있으면 기본 모델 선택, 없으면 첫 번째 모델 선택
            if DEFAULT_MODEL in self.model_names:
                # config에 지정한 기본 모델이 실제 목록에 있으면 그것을 선택합니다.
                self.selected_model_var.set(DEFAULT_MODEL)
            else:
                # llama 이름이 포함된 첫 모델을 우선 찾고, 없으면 첫 번째 모델 사용
                # next(제너레이터, 기본값) 패턴입니다.
                # model_names 안에서 "llama"가 포함된 이름을 먼저 찾고,
                # 없으면 첫 번째 모델(self.model_names[0])을 사용합니다.
                llama_candidate = next(
                    (name for name in self.model_names if "llama" in name.lower()),
                    self.model_names[0],
                )

                # 최종 선택 모델로 설정합니다.
                self.selected_model_var.set(llama_candidate)

            # 상태 표시줄을 정상 완료로 갱신합니다.
            self.status_var.set("모델 목록 준비 완료")

        except Exception as exc:
            # 예외가 발생하면 선택 모델을 비웁니다.
            self.selected_model_var.set("")

            # 콤보박스 목록도 비웁니다.
            self.model_combo["values"] = []

            # 예외 내용을 사용자 친화적인 에러 메시지로 바꿔 시스템 메시지에 출력합니다.
            self._append_system_message(build_connection_error_message(exc))

            # 상태 표시줄에 실패 메시지를 표시합니다.
            self.status_var.set("모델 목록 조회 실패")

    # ------------------------------------------------------------------
    # 채팅창 출력 유틸리티
    # ------------------------------------------------------------------
    def _append_system_message(self, message: str) -> None:
        # "SYSTEM: " 문자열을 system_name 태그 스타일로 삽입합니다.
        self.chat_area.insert(tk.END, "SYSTEM: ", "system_name")

        # 실제 메시지 본문을 삽입하고, 뒤에 빈 줄 하나를 둡니다.
        self.chat_area.insert(tk.END, message + "\n\n")

        # 채팅창 스크롤을 맨 아래로 이동시켜 최신 메시지가 보이도록 합니다.
        self.chat_area.see(tk.END)

    # ---------------------------------------
    # 사용자 메시지를 채팅창에 추가
    # ---------------------------------------
    def _append_user_message(self, message: str) -> None:
        # 사용자 이름 영역 출력
        self.chat_area.insert(tk.END, "USER: ", "user_name")

        # 사용자 실제 메시지 출력
        self.chat_area.insert(tk.END, message + "\n\n")

        # 맨 아래로 스크롤 이동
        self.chat_area.see(tk.END)

    # ---------------------------------------
    # AI 응답 시작 시 "AI: " 라벨을 먼저 출력합니다.
    # ---------------------------------------
    def _start_ai_message(self) -> None:
        self.chat_area.insert(tk.END, "AI: ", "ai_name")

        # 현재 텍스트 끝 인덱스를 저장합니다.
        # 이 값은 현재 코드에서는 큰 활용이 없지만,
        # 나중에 특정 AI 응답 구간 편집 같은 기능을 추가할 때 유용할 수 있습니다.
        self.current_ai_start_index = self.chat_area.index(tk.END)

        # 맨 아래로 스크롤 이동
        self.chat_area.see(tk.END)

    # ---------------------------------------
    # AI가 스트리밍으로 보낸 텍스트 조각(piece)을 그대로 이어붙입니다.
    # ---------------------------------------
    def _append_ai_stream_piece(self, piece: str) -> None:
        
        self.chat_area.insert(tk.END, piece)

        # 맨 아래로 스크롤 이동
        self.chat_area.see(tk.END)

    # ---------------------------------------
    # # AI 응답이 끝났을 때 줄바꿈 2개를 추가해 다음 메시지와 구분합니다.
    # ---------------------------------------
    def _end_ai_message(self) -> None:
        
        self.chat_area.insert(tk.END, "\n\n")

        # 맨 아래로 스크롤 이동
        self.chat_area.see(tk.END)            

    # ------------------------------------------------------------------
    # 입력/전송 관련
    # ------------------------------------------------------------------
    def _on_enter_pressed(self, event) -> str:

        # event.state 비트마스크를 통해 Shift 키가 눌렸는지 확인합니다.
        # 0x0001 비트를 검사하여 Shift 상태를 판별합니다.
        shift_pressed = (event.state & 0x0001) != 0

        # Shift+Enter 라면
        if shift_pressed:
            # 기본 동작(줄바꿈)을 허용합니다.
            return None

        # 그냥 Enter 라면 메시지 전송 실행
        self._send_message()

        # "break"를 반환하면 tkinter 기본 Enter 동작(줄바꿈)을 막습니다.
        return "break"

    # ---------------------------------------
    # 입력창의 전체 텍스트를 읽어와 앞뒤 공백을 정리합니다.
    # Text 위젯은 '1.0'부터 'end-1c'까지 읽는 패턴을 사용합니다.
    # ---------------------------------------
    def _get_input_text(self) -> str:
        # "1.0" 은 첫 번째 줄, 첫 번째 문자 위치입니다.
        # "end-1c" 는 맨 끝의 자동 개행 문자 1개를 제외한 실제 끝을 의미합니다.
        # strip() 으로 앞뒤 공백/개행을 제거합니다.
        return self.input_box.get("1.0", "end-1c").strip()

    # ---------------------------------------
    # 입력창의 내용을 처음부터 끝까지 모두 삭제합니다.
    # ---------------------------------------
    def _clear_input(self) -> None:
        self.input_box.delete("1.0", tk.END)

    # ---------------------------------------
    # 상태를 작업 중으로 놓기
    # ---------------------------------------
    def _set_busy(self, busy: bool) -> None:        
        self.is_busy = busy

        # busy=True 이면
        if busy:
            # 전송 버튼 비활성화
            self.send_button.config(state=tk.DISABLED)

            # 모델 콤보박스도 비활성화
            self.model_combo.config(state="disabled")

            # 상태 표시줄 갱신
            self.status_var.set("AI 응답 생성 중...")
        else:
            # 작업 완료 시 전송 버튼 다시 활성화
            self.send_button.config(state=tk.NORMAL)

            # 콤보박스는 readonly 상태로 복구
            self.model_combo.config(state="readonly")

            # 상태를 준비 완료로 표시
            self.status_var.set("준비 완료")

    # ------------------------------------------------------------------
    # 백그라운드 스레드
    # ------------------------------------------------------------------
    def _send_message(self) -> None:

        # 이미 처리 중이면 중복 전송을 막기 위해 바로 종료합니다.
        if self.is_busy:
            return

        # 입력창의 현재 텍스트를 가져옵니다.
        user_message = self._get_input_text()

        # 비어 있는 메시지면 전송하지 않습니다.
        if not user_message:
            return

        # 현재 선택된 모델명을 읽어오고 앞뒤 공백 제거
        selected_model = self.selected_model_var.get().strip()

        # 선택된 모델이 없으면 사용자에게 안내 메시지 출력
        if not selected_model:
            self._append_system_message("선택된 모델이 없습니다. 먼저 모델 목록을 확인하세요.")
            return

        # 사용자 메시지를 history에 추가하기 전에 화면에도 먼저 출력합니다.
        self._append_user_message(user_message)

        # 입력창 비우기
        self._clear_input()

        # 스트리밍 받을 AI 메시지의 시작점 생성
        # 즉 화면에 "AI: " 를 먼저 찍어 둡니다.
        self._start_ai_message()

        # UI 잠금
        self._set_busy(True)

        # 백그라운드 스레드 시작
        # target : 스레드에서 실행할 함수
        # args : 전달할 인자들
        # daemon=True :
        #   메인 프로그램 종료 시 이 스레드도 함께 종료되도록 설정
        self.worker_thread = threading.Thread(
            target=self._worker_stream_chat,
            args=(selected_model, user_message),
            daemon=True,
        )

        # 실제 스레드 시작
        self.worker_thread.start()

    # --------------------------------------------------------------------------------------------------------
    # 질문 전송 후 응답 정보 만들기 
    # --------------------------------------------------------------------------------------------------------
    def _worker_stream_chat(self, selected_model: str, user_message: str) -> None:
        
        ai_full_response_parts: List[str] = [] # "안", "녕", "하", "세", "요" 와 같은 AI가 보내는 응답 조각들을 모아서 최종 
                                                #완성문장을 만들 리스트

        try:
            # [목적] 
            #  - 현재 history의 스냅샷(snapshot, 복사본)을 만듦

            # [이유]
            #  - 백그라운드 스레드가 history를 읽어서 AI에게 보내는 동안, 사용자가 메인 스레드(UI)에서 새로운 메시지를 입력하여 history에
            #     add()를 해버리면 데이터가 꼬이거나 에러가 날 수 있기 때문, 따라서 안전하게 현재 시점 기준 복사본을 사용하기 위해

            # [자바와 비교]
            #  - 자바에서 ArrayList 같은 컬렉션을 여러 스레드가 동시에 수정할 때 발생하는 ConcurrentModificationException 상황을 
            #    방지하기 위해 new ArrayList<>(originalList)로 복사본을 만들어 작업하듯, 파이썬도 읽기 전용 스냅샷을 만들어 백그라운드
            #    스레드에 던져주는 것            
            history_snapshot = list(self.history) #이것을 얕은 복사(Shallow Copy) 라고 부름 
            # 얕은 복사로 처리하는 이유는? 백그라운드 스레드가 복사본을 가져가서 읽기만 할뿐 내용을 절대 수정할 목적은 아니므로...

            # stream_chat() 이 yield 하는 텍스트 조각들을 하나씩 순회합니다.
            for piece in stream_chat(model=selected_model,user_message=user_message,history=history_snapshot):
                
                ai_full_response_parts.append(piece) # 응답 조각을 리스트에 모아서 "문장을 완성"

                #-----------------------------------
                # 화면에 바로 반영하기 위한 데이터 큐에 추가
                #-----------------------------------                
                self.stream_queue.put(("piece", piece)) #여기서 ("piece", piece) 는 파이썬의 자료구조 중 튜플임
                                                        #소괄호로 감싸져 있으며, java의 List와 비슷하지만 한번 정하면 내용을 
                                                        # 바꿀 수 없는 특징이 있음        

            # 모든 스트리밍이 끝나면 조각들을 합쳐 하나의 완성된 답변 문자열로 만들기
            # ai_full_response_parts 는 루프가 끝난 시점에 ["안", "녕", "하", "세", "요"] (글자 조각들의 리스트) 상태에 있을뿐 
            # 아직 하나의 완성된 문장은 아니기 때문
            final_answer = "".join(ai_full_response_parts).strip() # join() 을 이용하면 반복문을 사용하지 않고도 리스트의 
                                                           # 모든 문자열을 하나로 연결해줌 "".join()을 수행하면 
                                                           # 빈칸 없이 연결함. 공백을 넣어서 붙일때는 " ".join() 으로 처리     
            #-----------------------------------
            # 완성된 문자, history 에 저장하기 위해 큐에 추가
            #-----------------------------------
            self.stream_queue.put(("done", {"user_message": user_message, "assistant_message": final_answer}))

        except Exception as exc:
            # 백그라운드 작업 중 예외가 발생하면 사용자용 에러 메시지 생성
            error_message = build_connection_error_message(exc)

            # 에러 이벤트를 Queue에 넣어 메인 스레드가 출력하도록 합니다.
            self.stream_queue.put(("error", error_message))

    # --------------------------------------------------------------------------------------------------------
    # Queue 처리
    # --------------------------------------------------------------------------------------------------------
    def _poll_stream_queue(self) -> None:

        try:
            # 큐에 쌓인 데이터가 하나도 남지 않을 때까지 최대한 빨리 다 처리
            while True:
                # get_nowait()는 데이터가 있으면 가져오고, 없으면 기다리지 않고 즉시 예외를 던짐, UI 스레드가 큐를 기다리느라 멈추면 
                # (blocking) 화면이 얼어버리기 때문에 이 방식을 사용함
                event_type, payload = self.stream_queue.get_nowait() # 튜플반환 및 unpacking 기능으로 튜플 안의 데이터를
                                                                     # 각각 event_type, payload에 대입

                # 스트리밍 응답 조각 도착
                if event_type == "piece":                    
                    self._append_ai_stream_piece(payload) # AI 출력창에 바로 이어붙입니다.

                # 전체 응답 완료 이벤트
                elif event_type == "done":                    
                    self._end_ai_message()# 스트리밍 종료 시 줄바꿈 마무리
            
                    user_message = payload["user_message"] #사용자 질문
                    assistant_message = payload["assistant_message"] #ai 답변
                    
                    self.history.append({"role": "user", "content": user_message}) # 사용자 질문을 history에 저장
                    self.history.append({"role": "assistant", "content": assistant_message})#AI 답변을 history에 저장

                    # UI 잠금 해제
                    self._set_busy(False)

                # 에러 이벤트
                elif event_type == "error":
                    
                    self._append_ai_stream_piece("\n" + payload)# 이미 "AI: "는 출력 시작된 상태이므로 에러 내용을 그 뒤에 덧붙입니다.
                    self._end_ai_message() # 줄바꿈 마무리
                    self._set_busy(False)# UI 잠금 해제

        except queue.Empty:            
            pass # 읽을 데이터가 없으면 그냥 넘어감(pass는 아무것도 하지 말라는 뜻)

        # Java의 Timer.schedule() 이나 JavaScript의 setTimeout()과 같음
        # UI_POLL_INTERVAL_MS 밀리초 후에 _poll_stream_queue() 함수를 다시 실행하라고 예약함
        # 이 구조 덕분에 메인 스레드는 주기적으로 Queue를 확인하면서 백그라운드 스레드가 넣은 데이터를 안전하게 UI에 반영할 수 있음
        self.root.after(UI_POLL_INTERVAL_MS, self._poll_stream_queue)

    # ------------------------------------------------------------------
    # 부가 기능
    # ------------------------------------------------------------------

    def _clear_chat(self) -> None:

        # AI 응답 생성 중이면 초기화를 막습니다.
        # 이유:
        #   스트리밍 중에 채팅창/히스토리를 지우면 상태가 꼬일 수 있기 때문입니다.
        if self.is_busy:
            self._append_system_message("현재 AI 응답 생성 중이므로 지금은 초기화할 수 없습니다.")
            return

        # 채팅 출력창 전체 삭제
        self.chat_area.delete("1.0", tk.END)

        # 대화 history 리스트도 비움
        self.history.clear()

        # 시스템 메시지로 초기화 완료를 알림
        self._append_system_message("대화가 초기화되었습니다.")

        # 상태 표시줄 갱신
        self.status_var.set("대화 초기화 완료")        