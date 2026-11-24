[English](ARCHITECTURE.md) | 한국어

# 에이전트 구조

모델은 다음 행동과 도구 입력을 결정합니다. Harness는 요청을 검사하고 도구를 실행한 뒤 결과를 모델에 전달합니다. 모델은 관찰한 결과를 바탕으로 다음 행동을 선택하거나 최종 답변을 작성합니다.

## 도구 사용 에이전트

| 파일 또는 함수 | 역할 |
|---|---|
| `agents/tool_agent/main.py` | 모델 호출과 MCP 연결을 관리하는 Host |
| `make_client()` | 환경변수로 로컬 모델 클라이언트 생성 |
| `connect()` | MCP 서버 초기화와 도구 목록 수집 |
| `schema()` | MCP 도구 정보를 모델의 함수 호출 형식으로 변환 |
| `call_tool()` | 도구 실행 결과와 오류 반환 |
| `ask()` | 모델 판단과 도구 실행을 반복 |
| `agents/tool_agent/tools.py` | MCP 도구 구현 |

MCP 연결은 `initialize`, `tools/list`, `tools/call` 순서로 진행됩니다. 서버 이름을 도구 이름의 접두어로 붙여 이름 충돌을 방지합니다. 최대 모델 호출 횟수는 `MAX_TURNS`에서 설정합니다.

| 도구 | 기능 |
|---|---|
| `tools__open_webpage` | 기본 브라우저에서 웹페이지 열기 |
| `tools__search_wikipedia` | 한국어 위키백과 검색과 요약 조회 |
| `tools__create_excel` | CSV 표를 Excel 파일로 저장하고 열기 |
| `fetch__fetch` | 웹페이지 내용 조회 |

## 다중 에이전트

기획자가 후보를 제안하고, 예산 담당이 비용을 계산하며, 검토자가 조건을 검사합니다. 역할별 결과는 공유 작업판으로 전달합니다.

| 파일 또는 구성 | 역할 |
|---|---|
| `agents/team_agent/config.py` | 도구 사용 여부와 모델 설정 |
| `agents/team_agent/runner.py` | 모델 생성, 실행, 결과 조회 명령 |
| `agents/team_agent/harness.py` | 역할, 도구, 모델 클라이언트와 실행 루프 |
| `agents/team_agent/modelfiles/` | 역할별 모델의 파라미터와 시스템 프롬프트 |
| `ROLES` | 역할별 목표와 도구 권한 |
| `ToolRegistry.execute()` | 허용 도구와 입력값 검사 |
| `run_agent()` | 계획, 실행, 결과 확인과 종료 제어 |
| `run_case()` | 역할별 실행과 공유 작업판 전달 |

기본 선택 예제는 인원수, 예산, 비건 조건을 만족하는 간식 세트를 고릅니다. 각 역할은 자신의 대화 기록을 유지하고, 앞선 역할의 결과는 `shared_board`로 전달받습니다. 대회 문제에 맞게 역할과 도구를 교체할 수 있습니다.

## 기록

| 로그 태그 | 내용 |
|---|---|
| `[MODEL]` | 모델 호출 |
| `[PLAN]` | 작업 계획 |
| `[TOOL CALL]` | 실행할 도구 |
| `[TOOL RESULT]` | 도구의 실행 결과 |
| `[HANDOFF]` | 다음 역할로 전달 |
| `[FINAL]` | 최종 답변 |
| `[VERIFY]` | 조건 검사 결과 |
