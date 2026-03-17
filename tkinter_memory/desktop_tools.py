from __future__ import annotations

import platform
import subprocess
from typing import Any, Dict, List

def open_editor() -> str:
    #현재 파이썬이 실행되고 있는 플랫폼 조사 
    system = platform.system.lower() # Window-> window, Darwin-> darwin     

    try:
        if system=="windows":
            subprocess.Popen(["notepad.exe"]) 
            return "윈도우 메모장을 열었습니다"  
        
        elif system=="darwin":
            subprocess.Popen(["open", "-a", "TextEdit"])
            return "텍스트 에디터 열었습니다"
        
        else:         
            return f"{system}은 지원하지 않는 운영체제 입니다"
    except FileNotFoundError as e:
        return "실행 파일을 찾을 수  없습니다." 
    except Exception as e:
        return f"에러 발생{str(e)}"               
    
#--------------------------------------------------------
# 사용자가 어떠한 질문을 햇을때, ai가 툴을 실행해야 할지를 알려줌
# 즉 ai에게 "야, 사용자가 이런 질문을 하면 ,넌 실행할 함수명을 나한테 다시 보내.."
#--------------------------------------------------------
OLLAMA_TOOL_DEFINITION: List[Dict[str, Any]] =[
    {
        "type": "function",
        "function": {
            "name":"open_editor",
            "description": "사용자가 메모장, 노트패드, notepad, editor, texteditor, 텍스트 편집기를 열어 달라고 요청했을때 해당 os의 메모장을 실행해",
            "parameters" :{
                "type":"object",
                "properties":{},
                "required":[]    
            }
        }
    }
]

#--------------------------------------------------------
# 모델이 우리가 정해놓은 규칙대로, 함수 실행을 원할때, 함수명과 실제 함수와의 연결
#--------------------------------------------------------
def execute_tool(function_name:str, arguments: Dict[str, Any] | None =None) -> str:
    safe_arguments = arguments or {}       

    #ai는 우리가 정해놓은 함수를 직접 호출할 권한이 없기 때문에, ai 전송한 메시지를 통해, 함수호출은 개발자가 진행
    if function_name == "open_editor":
        return open_editor()
    
    return f"{function_name}알 수 없는 도구 호출입니다."
