"""
[파일경로]  /config.py

[역할]
    이 파일은 프로그램 전체에서 공통으로 사용하는 설정값들을 모아두는 파일 (유지보수성을 위해 하드코딩 안함)
"""

OLLAMA_BASE_URL="http://localhost:11434" #Ollama 로컬 서버 기본 주소
OLLAMA_TAGS_URL=f"{OLLAMA_BASE_URL}/api/tags" #설치된 모델 목록을 조회하는 API 앤드포인트
OLLAMA_GENERATE_URL=f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_CHAT_URL=f"{OLLAMA_BASE_URL}/api/chat"
DEFAULT_MODEL="llama3.2:3b"

APP_TITLE="My Local LLM Chat" #채팅창의 제목 

#시스템 프롬프트 (페르소나)
SYSTEM_PROMPT="""
너는 한국어 교사야.
따라서 학생들에게 친절한 한국말로 존댓말로 얘기해.
또한 영어 약어가 나올 경우, 풀어서 풀네임도 함께 보여줘.
또한 너는 여성이야
"""

MAX_HISTORY_MESSAGES=10         #대화 이력을 몇개까지 LLM에게 같이 보낼지 제한 값 지정
REQUEST_TIMEOUT_SECONDS=300 #답변을 기다리는 시간 제한 
UI_POLL_INTERVAL_MS=80             #UI 갱신을 위한 큐 조회 주기

MAX_TOOL_CALL_ROUNDS=3 #최대 툴 실행횟수 제한 
