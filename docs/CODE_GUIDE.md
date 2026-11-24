# 코드 안내

강의 PDF의 개념과 실제 파일을 연결합니다. 두 실습은 서로 독립적으로 실행할 수 있습니다.

## Week 3 · Agent Harnessing

근거: [강의 PDF](../materials/week3-agent-harnessing.pdf), 4~6쪽(tool calling·harness·handoff), 10~11쪽(파일·실행 과정), 20~25쪽(로그·대화 기록·검증).

```text
planner → shared_board → budget → shared_board → reviewer
```

| 파일 / 함수 | 역할 |
|---|---|
| `student_config.py` | `USE_TOOLS`, 기본 모델, Ollama URL, 역할별 기본 모델 |
| `run_lab.py` | `inspect`, `models`, `run`, `cases`, `report` 단계와 로그 저장 |
| `harness.py: ROLES / role_prompt` | Persona, 역할별 도구 권한, 최종 JSON 형식 |
| `OllamaClient.chat` | Ollama 응답 스트림에서 텍스트·tool_calls 수집 |
| `ToolRegistry.execute` | 허용 도구·입력 필드 검사 후 Python 함수 실행 |
| `run_agent` | messages 구성, 계획 기록, 호출 제한·오류 복구, 최종 답 검증 |
| `run_case` | 세 Agent를 순서대로 실행하고 shared_board로 handoff |
| `verify_selection` | 모델 답과 독립적으로 조건·최적 선택 계산 |
| `modelfiles/` | FROM + PARAMETER + SYSTEM, 역할별 모델 정의 |
| `test_harness.py` | 모델 없이 논리·오류·HTTP 스트리밍 동작 검증 |

간식 선택의 데이터는 A(2,500원·만족도 5·비건 아님), B(2,000원·4·비건), C(1,500원·2·비건)입니다. 8명 기준 예산 24,000원 → A/20,000원, 예산 14,000원 → C/12,000원, 비건 필수·예산 24,000원 → B/16,000원이 됩니다.

강의 슬라이드는 `USE_TOOLS=False`에서 `True`로 변경하는 과정을 설명하지만, **제공된 실제 파일의 초기값은 이미 `True`**입니다. 도구 유무를 비교할 때만 직접 변경하세요. `--mode replay`는 고정 응답 재생이며 실제 LLM의 추론이 아닙니다. 실습 로그와 정답은 대회 성적이 아닙니다.

```bash
cd labs/week3_agent_harness
python run_lab.py --check
python run_lab.py --step inspect
python run_lab.py --step models
python run_lab.py --step run
python run_lab.py --step cases
python run_lab.py --step report
python -m unittest -v
```

## Week 4 · MCP

근거: [강의 PDF](../materials/week4-mcp.pdf), 3~5쪽(MCP 구조와 흐름), 7~13쪽(설치·실행·서버 구현).

```text
Host(agent.py) → ClientSession → stdio → MCP Server
                 initialize → tools/list → tools/call
```

| 파일 / 구성 | 역할 |
|---|---|
| `agent.py: SERVERS` | 직접 만든 `my-tools` 서버와 공식 fetch 서버 실행 설정 |
| `connect` | 서버 초기화 후 tools/list로 도구 목록 수집 |
| `to_ollama` | MCP inputSchema를 Ollama function schema로 변환 |
| `ask` | 질문과 도구 목록 전달 → tool_calls 처리 → 결과 재입력 |
| `my_server.py: @mcp.tool()` | Python 함수를 MCP 도구로 등록 |
| `open_webpage` | 사용자 기본 브라우저로 URL 열기 |
| `search_wikipedia` | 한국어 위키백과 검색과 요약 조회, 외부 LLM 호출 없음 |
| `create_excel` | CSV 표를 xlsx로 저장하고 기본 앱으로 열기 |

모델은 함수를 직접 실행하지 않습니다. 실행 요청은 Host가 MCP Client를 통해 Server로 전달합니다. 도구의 docstring과 JSON Schema가 모델이 도구를 선택하는 데 쓰입니다.

```bash
python labs/week4_mcp/agent.py --tools
python labs/week4_mcp/agent.py "위키백과에서 서울대학교를 찾아 두 문장으로 알려줘"
```

## 대회용 출발점

[starter](../starter/README.md)는 Week 4를 바탕으로 환경변수 설정과 종료·오류 처리를 보강한 코드입니다. `my_server.py`의 세 도구와 공식 fetch 서버를 사용합니다. 메일·이미지·기존 Excel 읽기 등의 추가 기능은 포함하지 않습니다.

| 차이 | 내용 |
|---|---|
| 설정 | `LOCAL_LLM_MODEL`, `LOCAL_LLM_URL`, `LOCAL_LLM_API_KEY` 환경변수 |
| 모델 호출 | 명시적 Ollama `Client`, 비동기 루프를 막지 않도록 thread로 호출 |
| 도구 이름 | 서버 이름을 접두어로 붙여 충돌 방지 |
| 자원 관리 | AsyncExitStack으로 세션·프로세스·로그 종료 |
| 오류 | MCP 오류 상태를 모델에 전달, 호출 한도에 도달하면 실패 종료 |
| 범위 | Week 3 입력 개수 검증 오류 1건 수정, 나머지 실습 Python은 유지 |

이 코드는 규정 준수를 자동 인증하지 않습니다. 설정된 모델의 실제 전체 파라미터 수, 연결 대상이 로컬 모델인지, 추가 도구가 온라인 AI를 호출하지 않는지는 팀이 확인해야 합니다.
