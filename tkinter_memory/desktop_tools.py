from __future__ import annotations
import platform
import subprocess
from typing import Any, Dict, List

#---------------------------------------------------------------------
# [추가 코드]
# Tool Calling 에서 사용할 실제 파이썬 도구 모음 파일
#---------------------------------------------------------------------

def open_editor() -> str:
    """운영체제에 따라 윈도우 메모장 또는 맥 TextEdit를 실행합니다."""
    system = platform.system().lower()

    try:
        if system == "windows":
            # 윈도우용 메모장 실행
            subprocess.Popen(["notepad.exe"])
            return "윈도우 메모장을 성공적으로 열었습니다."
        
        elif system == "darwin":
            # macOS용 TextEdit 실행
            subprocess.Popen(["open", "-a", "TextEdit"])
            return "맥(macOS) TextEdit를 성공적으로 열었습니다."
        
        else:
            return f"지원하지 않는 운영체제({system})입니다."
            
    except FileNotFoundError:
        return "실행 파일을 찾을 수 없습니다."
    except Exception as e:
        return f"에러가 발생했습니다: {str(e)}"


#---------------------------------------------------------------------
# [추가 코드]
# Ollama 에게 알려줄 도구 정의 목록
#---------------------------------------------------------------------
OLLAMA_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "open_editor",
            "description": "사용자가 메모장, 노트패드, notepad, editor, 텍스트 편집기를 열어 달라고 요청했을 때 윈도우 메모장을 실행합니다.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


#---------------------------------------------------------------------
# [추가 코드]
# 모델이 요청한 함수명을 실제 파이썬 함수와 연결하여 실행
#---------------------------------------------------------------------
def execute_tool(function_name: str, arguments: Dict[str, Any] | None = None) -> str:
    safe_arguments = arguments or {}

    if function_name == "open_editor":
        return open_editor()

    return f"알 수 없는 도구 호출입니다: {function_name}, arguments={safe_arguments}"