[English](SETUP.md) | 한국어

# 설치 및 실행

## 요구 환경

- Python 3.10 이상
- Ollama 0.12.7 이상
- 도구 호출을 지원하는 로컬 모델
- 브라우저나 Excel 파일을 열기 위한 데스크톱 환경

## 설치

```bash
git clone https://github.com/101beee/ai-agent-grand-battle-2026.git
cd ai-agent-grand-battle-2026
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
ollama pull qwen3-vl:2b-instruct
```

Windows PowerShell에서는 다음 명령으로 가상환경을 만듭니다.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe agents/tool_agent/main.py --tools
```

## 모델 설정

| 환경변수 | 기본값 | 용도 |
|---|---|---|
| `LOCAL_LLM_MODEL` | `qwen3-vl:2b-instruct` | 실행 모델 |
| `LOCAL_LLM_URL` | `http://127.0.0.1:11434` | Ollama 호환 서버 주소 |
| `LOCAL_LLM_API_KEY` | 빈 값 | 도구 사용 에이전트의 Bearer 인증 키 |

macOS와 Linux의 bash에서는 `.env.example`을 복사해 설정할 수 있습니다.

```bash
cp .env.example .env
# .env를 수정한 뒤 환경변수로 불러옵니다.
set -a
source .env
set +a
```

`.env` 파일은 자동으로 불러오지 않습니다. PowerShell에서는 `$env:LOCAL_LLM_MODEL = 'qwen3-vl:2b-instruct'` 형식으로 설정합니다. 인증 키가 담긴 파일은 저장소에 올리지 마세요.

## 도구 사용 에이전트

```bash
python agents/tool_agent/main.py --tools
python agents/tool_agent/main.py "위키백과에서 서울대학교를 찾아 두 문장으로 알려줘"
python agents/tool_agent/main.py "월요일부터 금요일까지 프로젝트 일정표를 Excel로 만들어 열어줘"
```

`--tools`는 모델을 호출하지 않고 연결된 MCP 도구 목록을 출력합니다. 질문을 전달하면 모델이 도구를 선택하고 실행 결과를 확인해 답변합니다.

생성한 Excel 파일은 `agents/tool_agent/outputs/`에 저장됩니다. MCP 서버 로그는 `agents/tool_agent/mcp_servers.log`에 기록됩니다.

## 다중 에이전트

기획자, 예산 담당, 검토자가 조건 기반 선택 문제를 함께 해결하는 구성입니다.

```bash
python agents/team_agent/runner.py --check
python agents/team_agent/runner.py --step inspect
python agents/team_agent/runner.py --step models
python agents/team_agent/runner.py --step run
python agents/team_agent/runner.py --step cases
python agents/team_agent/runner.py --step report
```

`config.py`의 `USE_TOOLS`로 도구 사용 여부를 설정합니다. 역할별 기본 모델은 `AGENT_BASES`에서 지정합니다. 실행 기록은 `agents/team_agent/runs/`에 저장됩니다.

모델 없이 실행 흐름을 확인하려면 `--mode replay`를 사용합니다. 이 모드는 고정 응답을 재생합니다.

## 서버 연결 방식

두 에이전트는 Ollama API를 사용합니다. 다른 프로토콜의 로컬 서버를 연결할 때는 모델 클라이언트와 메시지 변환을 해당 서버의 규격에 맞게 구현합니다.

## 도구 확장

`agents/tool_agent/tools.py`에 `@mcp.tool()` 함수를 추가합니다. 함수의 입력 타입과 설명을 작성한 뒤 `--tools` 명령으로 등록 여부를 확인합니다. 다른 MCP 서버를 연결하려면 `agents/tool_agent/main.py`의 `SERVERS`에 실행 설정을 추가합니다.

메일 예약과 발송, 이미지 처리, 기존 Excel 파일 읽기는 팀별로 필요한 도구를 구현해 연결합니다.

## 검사

```bash
python -m unittest discover -s tests -v
python scripts/update_leaderboard.py --check
python scripts/check_repository.py
```
