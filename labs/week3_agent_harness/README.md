# Week 3 · Agent Harness 실습

세 Agent가 각자 자기 모델로 간식 세트를 고릅니다.

```
snack-planner (기획자) → snack-budget (예산 담당) → snack-reviewer (검토자)
```

| 파일 | 내용 |
|---|---|
| `student_config.py` | 수정할 설정 (`USE_TOOLS`) |
| `run_lab.py` | 단계별 실행 |
| `harness.py` | Agent, 도구, 실행 루프 |
| `modelfiles/` | Agent별 모델 정의 (`--step models`가 생성) |
| `runs/` | 실행 기록 (자동 생성) |

## 준비

- Python 3.10 이상, Ollama 0.12.7 이상
- 모델: `ollama pull qwen3-vl:2b-instruct`
- pip 설치는 필요 없습니다.

## 실행 순서 (macOS · Linux)

Windows는 `.venv/bin/python`을 `.\.venv\Scripts\python.exe`로, `python3`을 `py`로 바꿉니다.

```bash
python3 -m venv .venv
.venv/bin/python run_lab.py --check
.venv/bin/python run_lab.py --step inspect
.venv/bin/python run_lab.py --step models
ollama list
.venv/bin/python run_lab.py --step run
```

`student_config.py`에서 `USE_TOOLS = True`로 바꾸고 저장합니다.

```bash
.venv/bin/python run_lab.py --step run
.venv/bin/python run_lab.py --step cases
.venv/bin/python run_lab.py --step report
```

| 단계 | 하는 일 |
|---|---|
| `--check` | Ollama 연결과 도구 호출 1회 점검 |
| `--step inspect` | 데이터와 Agent 구성 확인 (모델 호출 없음) |
| `--step models` | Agent별 모델 3개 생성 → `ollama list`로 확인 |
| `--step run` | 문제 1을 세 모델로 실행 |
| `--step cases` | 문제 1·2·3 실행 |
| `--step report` | 저장된 결과 비교 |

## 문제

| 세트 | 1인 가격 | 만족도 | 비건 |
|---|---:|---:|---|
| A 빵+주스 | 2,500원 | 5 | X |
| B 바나나+두유 | 2,000원 | 4 | O |
| C 크래커+생수 | 1,500원 | 2 | O |

8명 기준, 조건을 만족하는 세트 중 만족도가 가장 높은 세트를 고릅니다.

| 문제 | 예산 | 비건 필수 |
|---|---:|---|
| 1 | 24,000원 | X |
| 2 | 14,000원 | X |
| 3 | 24,000원 | O |

## 로그 태그

| 태그 | 의미 |
|---|---|
| `[AGENT]` | 실행 중인 Agent와 모델 |
| `[MEMORY]` | 앞서 작업판에 기록한 Agent |
| `[PLAN]` | 작업 계획 |
| `[TOOL CALL]` / `[TOOL RESULT]` | 모델의 도구 요청 / 실제 실행 결과 |
| `[TOOL ERROR]` | 잘못된 도구 요청 (모델에게 돌려줘 다시 호출) |
| `[HANDOFF]` | 다음 Agent로 전달 |
| `[FINAL]` / `[VERIFY]` | 최종 답 / Python 채점 |

## 막힐 때

| 증상 | 확인 |
|---|---|
| `command not found: ollama` | Ollama 앱 실행 후 터미널 새로 열기 |
| 모델이 없다는 오류 | `ollama pull qwen3-vl:2b-instruct` |
| `snack-... 모델이 없습니다` | `--step models` 먼저 실행 |
| 수정이 반영되지 않음 | `student_config.py` 저장 여부 |

Ollama 없이 구조만 보려면 명령 뒤에 `--mode replay`를 붙입니다. 정해 둔 요청을 재생하므로 모델의 판단은 없습니다.

모델 없이 코드 점검: `.venv/bin/python -m unittest -v`


## 대회 적용 안내

이 폴더는 Week 3 수업 실습 코드입니다. 실습용 데이터·모델·실행 방법은 대회 규정과 구분하세요.
대회에서는 [룰북](../../docs/RULEBOOK.md)이 적용됩니다. 로컬 데이터·RAG를 사용하지 마세요.
실습의 간식 데이터와 replay 정답은 학습용이며 실전 문제셋이나 대회 성적이 아닙니다.
범용 출발점은 [starter](../../starter/README.md)를 참고하세요.
