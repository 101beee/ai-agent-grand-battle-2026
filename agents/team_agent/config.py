"""다중 에이전트의 모델과 실행 설정."""
import os

USE_TOOLS = True
MODEL = os.environ.get("LOCAL_LLM_MODEL", "qwen3-vl:2b-instruct")
OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://127.0.0.1:11434")
AGENT_BASES = {"planner": MODEL, "budget": MODEL, "reviewer": MODEL}
