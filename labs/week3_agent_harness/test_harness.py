"""Ollama 없이 핵심 동작을 점검한다:  python -m unittest -v"""
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest

from harness import (LabError, OllamaClient, ToolRegistry, get_case, native_call,
                     run_agent, run_case, verify_selection)
from run_lab import main


def silent(*args):
    pass


class FakeOllama:
    """정해진 응답(NDJSON 스트림)을 돌려주는 가짜 Ollama 서버."""
    def __init__(self, replies):
        self.replies, self.received = list(replies), []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.received.append((self.path, body))
                if self.path == "/api/create":
                    chunks = [{"status": "success"}]
                else:
                    chunks = outer.replies.pop(0)
                data = "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def msg(content="", tool_calls=None, done=True):
    m = {"role": "assistant", "content": content}
    if tool_calls:
        m["tool_calls"] = tool_calls
    return {"message": m, "done": done, "done_reason": "stop" if done else None}


class LogicTests(unittest.TestCase):
    def test_answers_for_three_cases(self):
        for case_id, (set_id, total) in {1: ("A", 20000), 2: ("C", 12000), 3: ("B", 16000)}.items():
            r = verify_selection(get_case(case_id), set_id)
            self.assertTrue(r["optimal"])
            self.assertEqual(r["total_krw"], total)
        self.assertFalse(verify_selection(get_case(2), "A")["budget_ok"])
        self.assertFalse(verify_selection(get_case(3), "A")["vegan_ok"])

    def test_tool_inputs_are_checked(self):
        tools = ToolRegistry(get_case(1), ("quote_sets", "check_constraints"), silent)
        for name, args in [("delete_file", {}), ("quote_sets", {"people": 9}), ("quote_sets", {"people": 8, "x": 1}),
                           ("check_constraints", {"case_id": 2, "set_id": "A"})]:
            with self.assertRaises(LabError):
                tools.execute(name, args)

    def test_replay_team_runs_three_cases_with_separate_boards(self):
        cases = [run_case(i, True, "replay", None, silent) for i in (1, 2, 3)]
        self.assertEqual([c["status"] for c in cases], ["success"] * 3)
        self.assertEqual([c["final"]["set_id"] for c in cases], ["A", "C", "B"])
        for i, c in enumerate(cases, 1):
            self.assertEqual([a["model"] for a in c["agents"]],
                             ["snack-planner (replay)", "snack-budget (replay)", "snack-reviewer (replay)"])
            self.assertTrue(all(e["final"] for e in c["shared_board"]))
            last_context = json.loads(c["agents"][2]["messages"][0]["content"])
            self.assertEqual(len(last_context["shared_board"]), 2)

    def test_bad_tool_input_is_returned_to_model(self):
        class Fixes:
            turn = 0
            def chat(self, messages, tools):
                self.turn += 1
                if self.turn == 1:
                    return {"role": "assistant", "content": "", "tool_calls": [native_call("record_plan", {"steps": list("abcd")})]}
                if self.turn == 2:
                    self.error = json.loads(messages[-1]["content"])
                    return {"role": "assistant", "content": "", "tool_calls": [
                        native_call("record_plan", {"steps": ["목록 확인"]}), native_call("list_snack_sets", {})]}
                return {"role": "assistant", "content": '{"set_id":"A","summary":"A"}'}
        client = Fixes()
        result = run_agent("planner", get_case(1), [], client, True, silent)
        self.assertEqual(result["final"]["set_id"], "A")
        self.assertIn("error", client.error)

    def test_missing_tools_and_call_limit_are_errors(self):
        class NoTool:
            def chat(self, messages, tools):
                return {"role": "assistant", "content": '{"set_id":"A","summary":"A"}'}
        with self.assertRaisesRegex(LabError, "빠졌"):
            run_agent("planner", get_case(1), [], NoTool(), True, silent)
        class Loop:
            def chat(self, messages, tools):
                return {"role": "assistant", "content": "", "tool_calls": [native_call("list_snack_sets", {})]}
        with self.assertRaisesRegex(LabError, "끝나지 않았"):
            run_agent("planner", get_case(1), [], Loop(), True, silent, max_model_calls=2)

    def test_cli_replay_cases_and_report(self):
        with TemporaryDirectory() as temp, redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["--step", "cases", "--mode", "replay", "--solution", "--runs-dir", temp]), 0)
            self.assertEqual(main(["--step", "report", "--mode", "replay", "--runs-dir", temp]), 0)
        self.assertEqual(out.getvalue().count("success"), 3)


class OllamaTransportTests(unittest.TestCase):
    def test_streamed_tool_calls_and_agent_model(self):
        fake = FakeOllama([
            [msg(tool_calls=[native_call("record_plan", {"steps": ["목록 확인"]})], done=False),
             msg(tool_calls=[native_call("list_snack_sets", {})])],
            [msg('{"set_id":"A",', done=False), msg('"summary":"A 제안"}')],
        ])
        try:
            OllamaClient("x", fake.url).create_model("snack-planner", "qwen3-vl:2b-instruct", "역할")
            client = OllamaClient("snack-planner", fake.url)
            result = run_agent("planner", get_case(1), [], client, True, silent)
            self.assertEqual(result["final"]["set_id"], "A")
            create = [b for p, b in fake.received if p == "/api/create"][0]
            self.assertEqual((create["model"], create["from"]), ("snack-planner", "qwen3-vl:2b-instruct"))
            chats = [b for p, b in fake.received if p == "/api/chat"]
            self.assertTrue(all(b["model"] == "snack-planner" and b["stream"] for b in chats))
            self.assertEqual(chats[0]["messages"][0]["role"], "user")       # 역할은 모델 SYSTEM에 있음
            tool_msgs = [m for m in chats[1]["messages"] if m["role"] == "tool"]
            self.assertEqual([m["tool_name"] for m in tool_msgs], ["record_plan", "list_snack_sets"])
        finally:
            fake.close()


if __name__ == "__main__":
    unittest.main()
