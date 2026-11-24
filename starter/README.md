# MCP 기본 코드

제공 Week 4 실습을 바탕으로 만든 로컬 **Ollama 호환** Agent입니다. 대회용 범용 출발점이며 전체 미션 해답은 아닙니다. [룰북](../docs/RULEBOOK.md)을 먼저 읽으세요.

## 준비와 실행

저장소 루트에서 Python 3.10 이상으로 실행합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
ollama pull qwen3-vl:2b-instruct
python starter/agent.py --tools
python starter/agent.py "위키백과에서 서울대학교를 찾아 두 문장으로 알려줘"
python starter/agent.py "월요일부터 금요일까지 프로젝트 일정표를 엑셀로 만들어 열어줘"
```

`--tools`는 로컬 모델을 호출하지 않고 MCP 서버의 연결·도구 목록을 확인합니다. 실제 질문에는 Ollama와 로컬 모델이 필요합니다. 생성 Excel은 `starter/outputs/`, MCP 서버 로그는 `starter/mcp_servers.log`에 저장되며 Git에서 제외됩니다. Excel과 브라우저 열기는 데스크톱 기본 앱이 필요합니다.

| 환경변수 | 기본값 | 의미 |
|---|---|---|
| `LOCAL_LLM_MODEL` | `qwen3-vl:2b-instruct` | 강의 실습 모델. 제공 서버의 실제 모델 ID와 다름 |
| `LOCAL_LLM_URL` | `http://127.0.0.1:11434` | Ollama 호환 로컬 서버 |
| `LOCAL_LLM_API_KEY` | 빈 값 | 필요할 때 Bearer 인증 헤더에만 사용 |

bash에서 `.env.example`을 복사해 설정하려면:

```bash
cp .env.example .env
# .env의 값을 자신의 로컬 환경에 맞게 수정
set -a
source .env
set +a
python starter/agent.py --tools
```

`.env`는 자동 로드되지 않습니다. 실제 키를 커밋하지 마세요. PowerShell은 `$env:LOCAL_LLM_MODEL = 'qwen3-vl:2b-instruct'` 형태로 환경변수를 설정합니다. Python은 `.\.venv\Scripts\python.exe`로 직접 실행할 수도 있습니다.

## 제공 서버 연결

1. **eTL 8주차**의 조별 local LLM API key와 접속 안내를 확인합니다.
2. 실제 API 프로토콜, base URL, 모델 ID를 확인합니다. 공지의 모델명 `Qwen3.8-27B`는 표시명일 수 있으므로 API ID를 추정하지 마세요.
3. 서버가 **Ollama 호환**이면 위 환경변수로 연결합니다.
4. 서버가 OpenAI 호환 또는 별도 프로토콜이면 `make_client()`와 `ask()`의 모델 호출·메시지 변환을 해당 규격에 맞게 교체해야 합니다. 현재 코드는 OpenAI 호환 `/v1/chat/completions` 어댑터를 구현하지 않습니다.

제공 서버의 주소·프로토콜·모델 ID·키가 자료에 없어 실제 제공 모델 연결은 검증하지 않았습니다. 설정만으로 온라인 모델 서버 사용이 허용되는 것은 아닙니다.

## 구성과 확장

`agent.py`가 MCP Host이며, `my_server.py`와 공식 `mcp_server_fetch`를 stdio로 실행합니다. `initialize → tools/list → tools/call` 순서로 연결하고, 도구 반환값을 tool 메시지로 넣어 모델이 다음 행동을 정하게 합니다.

| 모델에 보이는 이름 | 실제 도구 |
|---|---|
| `my_tools__open_webpage` | 브라우저 열기 |
| `my_tools__search_wikipedia` | 한국어 위키백과 검색·요약 |
| `my_tools__create_excel` | CSV로 Excel 생성·열기 |
| `fetch__fetch` | 웹 원문 조회 (설치된 공식 서버가 노출하는 이름 기준) |

직접 도구를 추가하려면 `my_server.py`에 `@mcp.tool()` 함수를 작성하고 입력 타입·반환값·docstring을 명시하세요. `agent.py --tools`로 노출을 확인합니다. 다른 MCP 서버는 `SERVERS`에 추가할 수 있습니다. 추가 서버가 온라인 모델이나 RAG를 호출하지 않는지 확인하세요.

현재 메일 예약·발송, 이미지 인식, 기존 Excel 읽기는 구현되어 있지 않습니다. MCP 결과는 텍스트만 모델에 전달하므로 이미지 도구를 추가할 때는 이미지 입력 경로도 별도로 구현해야 합니다. 최대 8회 모델 호출 후에도 최종 답이 없으면 실패로 종료합니다. 이는 코드의 기본 종료 설정이며 대회 제한 시간이 아닙니다.
