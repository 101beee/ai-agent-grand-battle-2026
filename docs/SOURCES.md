# 자료 출처와 변경 내역

## 제공 자료

| 공개 위치 | 제공 원본 | 용도 |
|---|---|---|
| `materials/final-project.pdf` | `TalkFile_Final Project_주탐세2_2026.pdf.pdf` | 목표·일정·평가·팀 구성 |
| `materials/week3-agent-harnessing.pdf` | `Week3_Agent_Harnessing.pdf` | Harness 실습 설명 |
| `materials/week4-mcp.pdf` | `Week4_MCP.pdf` | MCP 실습 설명 |
| `assets/poster.jpg` | `KakaoTalk_20261124_155121523.jpg` | 대회명·캐치프레이즈·행사 정보 |
| `labs/week3_agent_harness/` | `week3_agent_harness/week3_agent_harness/` | 제공 수업 코드 |
| `labs/week4_mcp/` | `Week4_MCP_Code/week4_mcp/` | 제공 수업 코드 |

PDF와 포스터는 파일명만 정리하고 내용을 변경하지 않았습니다. 실습 코드를 옮기되 Week 3 `record_plan`의 1~3개 입력 제한을 고쳤습니다. 원본은 4개 이상을 조용히 잘라 JSON Schema 및 동봉 테스트와 불일치했으므로, 범위 밖 입력을 오류로 돌려주도록 수정했습니다. 나머지 Python·Modelfile은 유지했고, 실습 README 끝에 대회 적용 주의를 추가했습니다. `__MACOSX`, `.DS_Store`, `__pycache__`, 실행 이력 `runs/`는 배포에서 제외했습니다. 실행 이력에는 수업 예제 응답이 담겨 있어 대회 성적으로 오인되지 않도록 포함하지 않았습니다.

`starter/agent.py`, 리더보드 스크립트와 문서는 이 저장소를 위해 정리했습니다. `starter/my_server.py`는 제공된 Week 4 파일과 같습니다. 규정은 Final Project PDF, 사용자 전달 공지와 추가 제한을 바탕으로 작성했습니다.

## README 구성 참고

- [Taekmino/craip](https://github.com/Taekmino/craip): Overview, Setup, 모듈 설명, Mission, Competition Results 구성
- [kyungrokrho/make_ai_robot](https://github.com/kyungrokrho/make_ai_robot): 단계별 환경 설정, 모듈 설명, 미션별 안내, 결과 영상·표 구성

참고 저장소의 소스코드·이미지·대회 점수는 복제하지 않았습니다. 제공 수업 자료의 저작권·재배포 조건은 원권리자에게 있으며 이 저장소에서 임의의 오픈소스 라이선스를 부여하지 않습니다.
