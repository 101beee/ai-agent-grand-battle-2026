"""실제 MCP stdio 서버와 고정 응답 모델로 Agent의 도구 왕복을 확인한다."""
import asyncio
from contextlib import AsyncExitStack, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import unittest

from ollama import ChatResponse

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tool_agent", ROOT / "agents/tool_agent/main.py")
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)


class ToolAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_mcp_connection_and_model_tool_round_trip(self):
        class ScriptedClient:
            def __init__(self):
                self.count = 0
                self.checked = False

            def chat(self, **kwargs):
                self.count += 1
                self.kwargs = kwargs
                if self.count == 1:
                    names = [t["function"]["name"] for t in kwargs["tools"]]
                    assert "tools__search_wikipedia" in names
                    assert "fetch__fetch" in names
                    return ChatResponse(message={"role": "assistant", "content": "", "tool_calls": [
                        {"function": {"name": "not_a_registered_tool", "arguments": {}}}]})
                result = json.loads(kwargs["messages"][-1]["content"])
                assert "error" in result
                self.checked = True
                return ChatResponse(message={"role": "assistant", "content": "도구를 사용할 수 없습니다."})
        client = ScriptedClient()
        with redirect_stdout(io.StringIO()):
            answer = await agent.ask("모델 없이 연결 구조만 점검", client)
        self.assertEqual(answer, "도구를 사용할 수 없습니다.")
        self.assertTrue(client.checked)

    async def test_tool_errors_are_observations(self):
        class Result:
            isError = True
            content = []
        class Session:
            async def call_tool(self, name, arguments):
                return Result()
        class Tool:
            name = "dummy"
        data = await agent.call_tool({"test": (Session(), Tool())}, "test", {})
        self.assertTrue(json.loads(data)["isError"])

    async def test_limit_does_not_execute_unobserved_final_tool(self):
        class Loops:
            def chat(self, **kwargs):
                return ChatResponse(message={"role": "assistant", "content": "", "tool_calls": [
                    {"function": {"name": "absent", "arguments": {}}}]})
        with redirect_stdout(io.StringIO()) as output:
            with self.assertRaisesRegex(RuntimeError, "最終|최종"):
                await agent.ask("호출 한도 확인", Loops())
        self.assertEqual(output.getvalue().count("[TOOL CALL]"), agent.MAX_TURNS - 1)


if __name__ == "__main__":
    unittest.main()
