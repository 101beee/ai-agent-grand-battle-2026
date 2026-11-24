"""수업 중 수정할 곳은 아래 한 줄입니다."""

USE_TOOLS = True

# 아래 설정은 그대로 둡니다.
MODEL = "qwen3-vl:2b-instruct"
OLLAMA_URL = "http://127.0.0.1:11434"

# Agent별 기본 모델. 도구 호출을 지원하는 다른 모델로 바꿀 수 있습니다.
AGENT_BASES = {"planner": MODEL, "budget": MODEL, "reviewer": MODEL}
