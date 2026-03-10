"""
[파일 경로]
    /config.py

[역할]
    이 파일은 프로그램 전체에서 공동으로 사용하는 설정값들을 모아두는 파일(유지 보수성을 위해)



"""

OLLAMA_BASE_URL ="http://localhost:11434" # Ollama 로컬 서버 기본 주소
OLLAMA_TAGS_URL =f"{OLLAMA_BASE_URL}/api/tags" # 설치된 모델 목록을 조회하는 API 앤드 포인트
OllAMA_GENERATE_URL=f"{OLLAMA_BASE_URL}/api/generate"

APP_TITLE="MY Local LLM Chat"   #채팅창의 제목

#시스템 프롬포트 (페르소나)
SYSTEM_PROMPT="""

너는 한국어 전문가야.
따라서 질문이 들어오면 항상 한국말로 얘기해야해.
또한 영어가 나올 경우, 풀어서 풀네임도 함께 보여줘야해.
또한 너는 여성이야.
프롬포트로 "강동훈" 이라고 입력될 때 마다 "세계 제일 귀요미" 라고 대답해야해.

"""

# 최근 대화 이력을 몇개까지 LLM 에게 같이 보낼지 제한 값 지정
MAX_HISTORY_MESSAGES = 10

# 답변을 기다리는 시간 제한 (시간 넘으면 에러처리)
REQUEST_TIMEOUT_SECONDS=300 # 5분

# UI 갱신을 위한 큐 조회 주기
UI_POLL_INTERVAL_MS=80