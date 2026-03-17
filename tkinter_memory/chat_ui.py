from __future__ import annotations # 문자열로
import tkinter as tk # AWT tkinter를 tk라 부르겠다.
from tkinter import ttk  # ttk 는 tkinter의 theme widget임
                        # 기본 tkinter 위젯보다 운영체제 스타일에 더 자연스럽고 보기좋음

from tkinter.scrolledtext import ScrolledText

# APP_TITLE이 정의된 config 파일이 있어야 합니다.
from config import DEFAULT_MODEL, APP_TITLE 
from ollama_api import fetch_model_names, build_connection_error_message
import threading  # threading 모듈은 별도의 작업 쓰레드를 만들기 위해 사용(즉, 메인쓰레드 보호하려고..)
from chat_service import stream_chat
from typing import Dict,List
import queue

Message = Dict[str,str]

class ChatUI:
  def __init__(self, root:tk.Tk): # root=window  tkinter 안에 있는 자료형 Tk
    
    self.root = root # 전달받은 창 대입
    self.root.title(APP_TITLE)
    self.root.geometry("980x720")

    self.selected_model_var=tk.StringVar() # tkinter위젯과 값을 바인딩 해주는 객체
    self.status_var = tk.StringVar(value = "준비완료")

    self.model_names: List[str] = []  # Ollama 서버에서 조회한 ai모델명을 담게 될 리스트
    self.is_busy = False  # 현재 AI가 응답 중인지 여부를 나타내는 플래그값, True인 경우 전송 버튼을 막아서 중복 전송 방지를 위함

    self.history: List[Message]=[]  # 대화 내역을 쌓아놓을 리스트
    self.history:List[str]=[]
    self._worker_thread: threading.Thread | None=None # 메인쓰레드 대신 업무를 수행할 별도 쓰레드

    self.stream_queue: queue.Queue = queue.Queue()
    

    #--------------UI 부착---------------------
    self._build_top_frame()
    self._build_chat_area()
    self._build_input_frame()
    self._build_status_bar()

    self._load_models() # 프로그램 시작 시 설치된 모델 목록 보여주기
    self._poll_stream_queue() # 메인 쓰레드로 하여금, 큐를 실시간 감시하도록 폴링 처리

  #----------------------------------------------------------
  # 안내 메시지(프로그램 즉 시스템에서 사용자에게 가이드하는 목적의 메시지 처리)
  #----------------------------------------------------------
  # _ 를 앞에 붙이면 private
  def _append_system_message(self, message: str) -> None:
    self.chat_area.insert(tk.END, "SYSTEM: ", "system_name")
    self.chat_area.insert(tk.END, message + "\n\n")
    self.chat_area.see(tk.END)  # 글이 쌓이면 맨 마지막줄이 보이게 이동

  #----------------------------------------------------------
  # 채팅 메시지 처리 메서드
  #----------------------------------------------------------
  def _append_user_message(self, message: str) -> None:
    self.chat_area.insert(tk.END, "USER: ", "user_name")  # USER: 에 적용하고 싶은 tag인 user_name이 적용된다. 밑에 self.chat_area.tag_config("user_name", font=("Arial", 13, "bold")) 참조
    self.chat_area.insert(tk.END, message + "\n\n") # message 뒤에 줄바꿈 두 번
    self.chat_area.see(tk.END)

  #----------------------------------------------------------
  # 1. 상단 영역 생성(ai모델 선택 드롭다운, 모델 새로고침 버튼, 대화를 싹 지워버리는 초기화 버튼)
  #----------------------------------------------------------
  def _build_top_frame(self) -> None: # _언더바는 프라이빗
    top_frame = ttk.Frame(self.root, padding = 10)
    top_frame.pack(fill=tk.X)
    
    model_label = ttk.Label(top_frame, text="모델 선택:")
    model_label.pack(side=tk.LEFT)

    # 사용가능한 ai 모델을 보여주는 콤보박스
    self.model_combo = ttk.Combobox(top_frame, textvariable=self.selected_model_var, state="readonly", width=35)
    self.model_combo.pack(side = tk.LEFT, padx = (8,12)) # python (8, 12) tuple은 list와 같지만 값을 못 바꿈

    refresh_button = ttk.Button(top_frame, text="ai 모델 목록 새로고침")
    refresh_button.pack(side = tk.LEFT, padx = (0, 8))

    clear_button = ttk.Button(top_frame, text = "대화 초기화")
    clear_button.pack(side = tk.LEFT)

  #----------------------------------------------------------
  # 2. 중앙 채팅 출력창 생성
  #----------------------------------------------------------
  def _build_chat_area(self) -> None:
    # chat_frame 변수 할당 추가
    chat_frame = ttk.Frame(self.root, padding = (10, 0, 10, 10)) # 시계 방향으로 padding
    chat_frame.pack(fill = tk.BOTH, expand = True)  # BOTH(좌우, 상하 모두), expand 남는 공간을 차지

    # wrap 줄바꿈 시 단어 단위로 감쌈
    # 난 어제 마켓에 가서 밥을 먹었다. 줄이 길어지면 한 단어를 끊지 않는다. 
    # state = tk.NORMAL 현재 편집이 가능한 상태임을 명시
    # font 튜플 내부 쉼표(,) 추가
    self.chat_area = ScrolledText(chat_frame, wrap = tk.WORD, font = ("Arial", 13), state = tk.NORMAL)
    self.chat_area.pack(fill = tk.BOTH, expand=True)

    # 태그 등록 및 스타일 지정
    self.chat_area.tag_config("system_name", font=("Arial", 12, "bold"))
    self.chat_area.tag_config("user_name", font=("Arial", 13, "bold"))
    self.chat_area.tag_config("ai_name", font=("Arial", 13, "bold"))

    # 디폴트 안내 메시지
    self._append_system_message(
      "프로그램이 시작되었습니다\n"
      "질문을 입력하시오 Enter 또는 전송 버튼을 누르세요.."
    )

  #----------------------------------------------------------
  # 3. 하단 입력 영역 생성
  #----------------------------------------------------------
  def _build_input_frame(self) -> None:
    input_frame = ttk.Frame(self.root, padding = 10)
    input_frame.pack(fill = tk.X) # X축 가로로 꽉 채우기..

    self.input_box = tk.Text(input_frame, height = 4, font = ("Arial", 13))
    self.input_box.pack(side = tk.LEFT, fill = tk.BOTH, expand = True, padx = (0, 10))  # 우측만 패딩

    self.send_button = ttk.Button(input_frame, text = "전송", width = 12, command = self._send_message)
    self.send_button.pack(side = tk.LEFT)

  #----------------------------------------------------------
  # 4. 맨 아래 상태 표시 영역
  #----------------------------------------------------------
  def _build_status_bar(self) -> None:
    status_frame = ttk.Frame(self.root, padding = (10, 0, 10, 10))
    status_frame.pack(fill = tk.X)

    # anchor = "w"란? 텍스트 왼쪽(west) 정렬로 배치
    status_label = ttk.Label(status_frame, textvariable = self.status_var, anchor = "w")
    status_label.pack(fill = tk.X)

  #----------------------------------------------------------
  # 모델 정보 관리
  #----------------------------------------------------------
  def _load_models(self) -> None:
    self.status_var.set("설치된 ai 모델 목록을 불러오는 중... ")

    try:
      names = fetch_model_names() # Ollama에 설치되어 있는 ai 모델 담기
      self.model_names = names # 멤버 변수에 보관
      self.model_combo["values"]=self.model_names # 콤보 박스에 출력

      # Ollama 서버에 접속은 성공했으나, 모델이 없는 경우
      if not self.model_names:
        self.selected_model_var.set("")

        self._append_system_message(
          "설치된 ai 모델이 없네요\n"
          "ai와 대화를 나누시려면 모델을 먼저 설치하세요 ex) ollama pull llama3.2:3b"
        )
        self.status_var.set("설치된 모델 없음")
        return
      
      # 개발자가 원하는 기본 모델을 정해놓았다면 해당 모델이 선택되게 처리하고,
      # 없으면 콤보박스의 첫 번째 모델 선택
      if DEFAULT_MODEL in self.model_names:
        self.selected_model_var.set(DEFAULT_MODEL)
      else:
        # llama 라는 이름이 포함된 첫 모델을 우선 찾고, 없으면 첫 번째 모델 사용
        # next(리스트 컴프리헨션, 디폴트값 )
        llama_candidate = next(
          (name for name in self.model_names if "llama" in name.lower()), self.model_names[0]
        )

        # 최종 선택 모델로 선정
        self.selected_model_var.set(llama_candidate)
      # 상태 표시줄에 정상 완료 처리
      self.status_var.set("ai 모델 준비 완료")
      
    
    except Exception as e:
      # 예외가 발생하면 선택 ai 모델 비우기
      self.selected_model_var.set("")

      # 콤보 박스 목록 비우기
      self.model_combo["values"] = []

      # 예외에 대한 메시지 처리
      self._append_system_message(build_connection_error_message(e))

      # 상태 표시줄에 실패 메시지 출력
      self.status_var.set("ai 모듈 목록 조회 실패")

  #----------------------------------------------------------
  # 메시지 전송
  #----------------------------------------------------------
  def _get_input_text(self) -> str:
    # 1.0은 첫 번째 줄, 첫 번째 문자 위치
    return self.input_box.get("1.0", "end-1c").strip()
  
  def _clear_input(self) -> None:
    self.input_box.delete("1.0", tk.END)

  def _start_ai_message(self) -> None:
    self.chat_area.insert(tk.END, "AI: ", "ai_name")  # AI: 에게 ai_name tag 붙이기
    self.chat_area.see(tk.END)

  def _set_busy(self, busy: bool) -> None:
    self.is_busy = busy


    # busy = True이면(UI들을 비활성화)
    if busy:
      self.send_button.config(state = tk.DISABLED)  # 전송 버튼 비활성화
      self.model_combo.config(state = "disabled") # 모델 콤보박스 비활성화
      self.status_var.set("AI 응답 생성 중...") # 상태 표시줄 내용 갱신
    else:
      self.send_button.config(state = tk.NORMAL)  # 전송 버튼 다시 활성화
      self.model_combo.config(state = "readonly") # 콤보박스는 readonly 상태로 복구
      self.status_var.set("준비 완료")  # 상태 표시줄 내용 갱신

  def _send_message(self) -> None:

    # 이미 전송중이면 중복 전송을 막기 위해 바로 이 메서드 호출을 종료
    if self.is_busy:
      return
    
    # 입력박스의 현재 값 얻기
    user_message = self._get_input_text()

    # 메시지가 비어있다면 전송하지 않음
    if not user_message:
      return
    
    # 현재 선택된 모델명을 읽어오되, 혹시 모를 앞뒤 공백제거
    selected_model = self.selected_model_var.get().strip()

    # 선택된 모델이 없으면 사용자에게 안내 메시지 출력
    if not selected_model:
      self._append_system_message("선택된 모델이 없습니다. 먼저 모델 목록을 확인하세요")
      return
    
    self._append_user_message(user_message) # 사용자 메시지를 화면에 출력

    self._clear_input();  # 기존 입력내용 지우기

    self._start_ai_message()  # AI로부터 받은 메시지 출력 준비
    self._set_busy(True)

    # 쓰레드를 이용한 통신 시작
    self._worker_thread = threading.Thread(
      target=self._worker_stream_chat,
      args=(selected_model,user_message),
      daemon=True)
    
    self._worker_thread.start() # java와 동일

    


  #----------------------------------------------------------
  # 메시지 전송 후 응답 정보 처리
  #----------------------------------------------------------
  # 모든 프로그래밍 언어에서 메인 실행부라 불리는 메인 쓰레드는 그 역할과 사용목적상 아래의 업무를 전용으로 함
  # 1) UI (화면 처리 즉 렌더링)
  # 2) 이벤트 처리
  # 3) 애플리케이션 운영
  # 결론) 절대로 무한루프, 네트워크 통신(응답 올 때까지 대기에 빠지므로), 스트림 처리 등등 대기상태에 빠지게 되는 업무는 
  #   시키면 안됨!! (스마트폰에서는 컴파일 불가)

  def _worker_stream_chat(self, selected_model: str, user_message: str) -> None:

    #대화 내역인 history를 다중 쓰레드 환경에서 바로 사용하게 되면 , 대화 내역이 꼬일 수 있음
    # 전통적인 다중 쓰레드 환경에서는 원본을 쓰지않고, 복사본을 사용함 ( 스냅샷 )
    try:
      history_snapshot=list(self.history)

      gen=stream_chat(model=selected_model,
                       user_message=user_message,
                       history=history_snapshot)

      for piece in gen:
        self.stream_queue.put(("piece",piece)) #() 튜플 : List와 흡사하지만, 안의 데이터를 수정 불가
        print(f"{piece}")

    except Exception as e:
      error_message =build_connection_error_message(e) # 예외 객체가 문자열로 반환
      print(f"{error_message}")

  #----------------------------------------------------------
  # Queue 처리
  #----------------------------------------------------------
  def _poll_stream_queue(self) -> None:

    try:
      while True:
        event_type, payload =self.stream_queue.get_nowait()
        if event_type == "piece":
          print(f"{payload}")
        
    except  queue.Empty:
      pass