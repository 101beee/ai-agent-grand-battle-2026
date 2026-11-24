# 검증 기록

검증일: 2026-11-24

- Week 3 동봉 unittest 7개 통과: 간식 정답, 입력 오류, replay, handoff, 가짜 Ollama HTTP 스트리밍.
- 저장소 unittest 6개 통과: 리더보드 공란·정렬·동률·잘못된 결과, 실제 MCP stdio 서버 초기화와 고정 응답 모델의 tool 메시지 왕복, 호출 한도와 MCP 오류 전달.
- Week 3 record_plan의 1~3개 입력 제한 불일치를 수정했습니다. 자세한 내용은 [출처와 변경 내역](SOURCES.md)을 참고하세요.
- 실제 로컬 LLM과 제공 Qwen 서버의 추론·응답 품질은 검증하지 않았습니다. MCP 구조 검증에 사용하는 모델 응답은 고정된 테스트 응답입니다.
- 인터넷 검색 결과, 브라우저/Excel 앱 열기, 메일 발송, 이미지 미션은 실행하지 않았습니다. 후자의 메일·이미지 미션은 기본 코드의 구현 범위에도 포함되지 않습니다.
- 재현용 의존성 버전은 requirements-lock.txt에 기록했습니다. 기본 설치 범위는 requirements.txt를 참고하세요.

저장소 루트에서 재현:

```bash
python -m pip install -r requirements-lock.txt
python -m unittest discover -s tests -v
python -m unittest discover -s labs/week3_agent_harness -v
python starter/agent.py --tools
python scripts/update_leaderboard.py --check
python -c "from pathlib import Path; Path('starter/mcp_servers.log').unlink(missing_ok=True)"
python scripts/check_repository.py
```

검증은 온라인 모델 API를 사용하지 않습니다. `.github/workflows/checks.yml`에 같은 핵심 검사들을 등록했습니다.
