# Week 4 · MCP로 도구 연결하기

`qwen3-vl:2b-instruct`가 MCP 도구로 웹페이지를 열고, 위키백과를 검색하고, 엑셀 파일을 만들어 엽니다.

| 파일 | 내용 |
|---|---|
| `agent.py` | MCP 서버에 연결해 도구를 쓰는 Agent |
| `my_server.py` | 직접 만든 MCP 서버 (웹페이지 열기 · 위키백과 검색 · 엑셀) |
| `outputs/` | 만들어진 엑셀 파일 (자동 생성) |

## 준비 (macOS)

Python 3.10 이상이 필요합니다. `python3 --version`이 3.9 이하라면 아래처럼 3.11로 만드세요.
- conda 사용: `conda create -y -p ./.venv python=3.11`
- conda 없음: python.org에서 Python 3.12 설치 후 `python3.12 -m venv .venv`

```bash
python3 -m venv .venv
.venv/bin/pip install "mcp>=1.10,<2" mcp-server-fetch ollama openpyxl
```

Windows: `py -m venv .venv` → `.\.venv\Scripts\pip install "mcp>=1.10,<2" mcp-server-fetch ollama openpyxl`
(이후 `.venv/bin/python` 대신 `.\.venv\Scripts\python.exe`)

Ollama 앱을 켜 두고(메뉴바 라마 아이콘) `ollama list`에 `qwen3-vl:2b-instruct`가 있어야 합니다.

## 실행

```bash
.venv/bin/python agent.py --tools
.venv/bin/python agent.py "MCP 공식 사이트 https://modelcontextprotocol.io 를 브라우저로 열어줘"
.venv/bin/python agent.py "위키백과에서 서울대학교를 찾아서 두 문장으로 알려줘"
.venv/bin/python agent.py "월요일부터 금요일까지 조별 프로젝트 일정표를 엑셀로 만들어서 열어줘"
```

## 도구 추가

`my_server.py`에 `@mcp.tool()`을 붙인 함수를 추가하면 바로 새 도구가 됩니다. 함수 설명(docstring)이 모델에게 전달됩니다.

`mcp`는 2 미만으로 고정합니다. 공식 `mcp-server-fetch` 서버가 아직 mcp 2.0과 맞지 않습니다.


## 대회 적용 안내

이 폴더는 Week 4 수업 실습 코드입니다. 실습용 데이터·모델·실행 방법은 대회 규정과 구분하세요.
대회에서는 [룰북](../../docs/RULEBOOK.md)이 적용됩니다. 로컬 데이터·RAG를 사용하지 마세요.
실습의 간식 데이터와 replay 정답은 학습용이며 실전 문제셋이나 대회 성적이 아닙니다.
범용 출발점은 [starter](../../starter/README.md)를 참고하세요.
