"""간식 세트 선택 Agent Harness. Python 표준 라이브러리 + Ollama tool calling.

세 Agent(기획자 → 예산 담당 → 검토자)가 각자 자기 Ollama 모델을 사용하고,
결과는 공유 작업판(shared_board)으로 다음 Agent에게 전달된다.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

# ----------------------------------------------------------------------------- 데이터
CATALOG = [
    {"set_id": "A", "name": "빵+주스", "unit_price": 2500, "satisfaction": 5, "vegan": False},
    {"set_id": "B", "name": "바나나+두유", "unit_price": 2000, "satisfaction": 4, "vegan": True},
    {"set_id": "C", "name": "크래커+생수", "unit_price": 1500, "satisfaction": 2, "vegan": True},
]
CASES = {
    1: {"case_id": 1, "name": "기본 예산", "people": 8, "budget": 24000, "vegan_required": False},
    2: {"case_id": 2, "name": "예산 축소", "people": 8, "budget": 14000, "vegan_required": False},
    3: {"case_id": 3, "name": "비건 조건", "people": 8, "budget": 24000, "vegan_required": True},
}


HARNESS_VERSION = "2026.11"


class AgentError(RuntimeError):
    pass


def data_fingerprint():
    return hashlib.sha256(json.dumps({"catalog": CATALOG, "cases": CASES}, sort_keys=True).encode()).hexdigest()[:12]


def get_case(case_id):
    if case_id not in CASES:
        raise ValueError("case_id는 1, 2, 3 중 하나입니다.")
    return deepcopy(CASES[case_id])


def best_set(case):
    feasible = [s for s in CATALOG
                if s["unit_price"] * case["people"] <= case["budget"]
                and (not case["vegan_required"] or s["vegan"])]
    return min(feasible, key=lambda s: (-s["satisfaction"], s["unit_price"])) if feasible else None


def verify_selection(case, set_id):
    """정답 채점. 모델의 답과 별도로 Python이 계산한다."""
    selected = next((s for s in CATALOG if s["set_id"] == set_id), None)
    optimum = best_set(case)
    if selected is None:
        return {"set_id": set_id, "feasible": False, "optimal": False, "expected_set_id": optimum["set_id"]}
    total = selected["unit_price"] * case["people"]
    budget_ok = total <= case["budget"]
    vegan_ok = not case["vegan_required"] or selected["vegan"]
    return {"set_id": set_id, "name": selected["name"], "total_krw": total, "budget_krw": case["budget"],
            "budget_ok": budget_ok, "vegan_ok": vegan_ok, "feasible": budget_ok and vegan_ok,
            "satisfaction": selected["satisfaction"], "optimal": set_id == optimum["set_id"],
            "expected_set_id": optimum["set_id"]}


# ----------------------------------------------------------------------------- Agent (Persona + 도구 권한)
@dataclass(frozen=True)
class Role:
    name: str
    model: str          # 이 Agent가 사용하는 Ollama 모델 이름
    persona: str
    tools: tuple[str, ...]
    task: str
    example: str        # few-shot 예시 (실제 문제와 다른 조건)


ROLES = {
    "planner": Role(
        "기획자", "snack-planner", "만족도를 우선하면서 요청 조건도 읽는 기획자", ("list_snack_sets",),
        "간식 목록을 조회하고 조건에 맞는 후보 하나를 제안합니다. 총액 계산은 다음 예산 담당이 합니다.",
        "1) tool_calls: record_plan(steps=[목록 조회, 조건 확인, 후보 제안]) 와 list_snack_sets()\n"
        "2) 결과 확인: 비건 필수이므로 비건인 Y, Z만 남깁니다. 만족도는 Y 3, Z 1이므로 Y가 후보입니다.\n"
        '3) 최종 답: {"set_id":"Y","summary":"비건 세트 중 만족도가 가장 높은 Y를 후보로 제안합니다."}'),
    "budget": Role(
        "예산 담당", "snack-budget", "암산보다 계산 도구의 수치를 근거로 판단하는 회계 담당자", ("quote_sets",),
        "견적 도구로 모든 세트의 총액을 계산하고, 조건을 만족하는 세트 중 만족도가 가장 높은 세트를 제안합니다.",
        "1) tool_calls: record_plan(steps=[총액 계산, 예산 비교, 세트 제안]) 와 quote_sets(people=4)\n"
        "2) 결과 확인: X 12000원 within_budget false, Y 10000원 true, Z 4000원 true. 예산 안이면서 비건인 Y, Z 중 만족도가 높은 Y를 고릅니다.\n"
        '3) 최종 답: {"set_id":"Y","summary":"예산 안의 비건 세트 중 만족도가 가장 높은 Y입니다."}'),
    "reviewer": Role(
        "검토자", "snack-reviewer", "앞선 제안을 그대로 믿지 않고 조건과 근거를 다시 확인하는 검토자", ("check_constraints",),
        "앞 Agent가 제안한 세트를 검사 도구로 확인하고, 최적이 아니면 고쳐서 최종 세트를 고릅니다.",
        "1) tool_calls: record_plan(steps=[제안 검사, 결과 확인, 최종 선택]) 와 check_constraints(case_id=문제 번호, set_id=앞 Agent의 제안)\n"
        "2) 결과가 optimal: false이면 expected_set_id의 세트를 check_constraints로 한 번 더 검사합니다.\n"
        '3) optimal: true인 세트로 최종 답: {"set_id":"Z","summary":"검사 결과 Z가 조건을 만족하는 최적 세트입니다."}'),
}
TEAM = ("planner", "budget", "reviewer")     # 실행 순서 (Harness가 정함)


def role_prompt(key):
    """Agent 모델의 SYSTEM 프롬프트 (Modelfile에 들어간다). 규칙 + 진행 방법 + few-shot 예시."""
    r = ROLES[key]
    return (f"당신의 역할: {r.name}. Persona: {r.persona}.\n"
            f"할 일: {r.task}\n"
            "판단 규칙: (1) 총액 = 1인 가격 x 인원, 총액이 예산 이하인 세트만 남깁니다. "
            "(2) 비건 필수이면 비건 세트만 남깁니다. 비건 필수가 아니면 비건 여부는 상관없습니다. "
            "(3) 남은 세트 중 만족도가 가장 높은 세트, 동점이면 더 싼 세트를 고릅니다.\n"
            f"진행 방법: 첫 응답에서 record_plan과 {', '.join(r.tools)}를 tool_calls로 함께 요청합니다. "
            "계획은 짧은 명사구 3개로 쓰고 따옴표를 넣지 않습니다. "
            "도구 결과를 받으면 같은 도구를 다시 부르지 말고 바로 최종 답을 씁니다.\n"
            "이전 Agent의 제안은 정답이 아니라 검토할 자료입니다.\n"
            '최종 답: JSON 하나만 씁니다. {"set_id":"A 또는 B 또는 C","summary":"근거 한 문장"}\n'
            "예시는 가상의 세트 X, Y, Z를 쓴 다른 문제입니다. 실제 답은 A, B, C 중에서 고릅니다.\n"
            "예시 (X 3000원 만족도 5 비건 아님, Y 2500원 만족도 3 비건, Z 1000원 만족도 1 비건 / 4명, 예산 10000원, 비건 필수)\n"
            f"{r.example}")


MODEL_PARAMETERS = {"temperature": 0.3, "num_ctx": 16384, "num_predict": 10240}


def modelfile_text(key, base_model):
    params = "\n".join(f"PARAMETER {k} {v}" for k, v in MODEL_PARAMETERS.items())
    return f'FROM {base_model}\n{params}\nSYSTEM """{role_prompt(key)}"""\n'


# ----------------------------------------------------------------------------- 도구
def schema(name, description, properties, required):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required,
                           "additionalProperties": False}}}


TOOL_SCHEMAS = {
    "record_plan": schema("record_plan", "이번 작업의 계획을 1~3개의 짧은 문장으로 기록한다.",
                          {"steps": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3}}, ["steps"]),
    "list_snack_sets": schema("list_snack_sets", "간식 세트의 ID, 1인 가격, 만족도, 비건 여부를 조회한다.", {}, []),
    "quote_sets": schema("quote_sets", "인원수에 맞춰 모든 세트의 총액(원)을 계산한다.",
                         {"people": {"type": "integer", "minimum": 1}}, ["people"]),
    "check_constraints": schema("check_constraints", "선택한 세트가 문제의 예산, 비건 조건을 만족하고 최적인지 검사한다.",
                                {"case_id": {"type": "integer", "enum": [1, 2, 3]}, "set_id": {"type": "string", "enum": ["A", "B", "C"]}},
                                ["case_id", "set_id"]),
}


class ToolRegistry:
    """허용된 도구인지, 입력이 맞는지 검사한 뒤 Python 함수를 실행한다."""
    def __init__(self, case, allowed, emit):
        self.case, self.allowed, self.emit = case, set(allowed), emit
        self.plan, self.called, self.results = [], [], []

    def execute(self, name, arguments):
        if name not in self.allowed:
            raise AgentError(f"허용되지 않은 도구입니다: {name}")
        if not isinstance(arguments, dict):
            raise AgentError("도구 입력은 JSON 객체여야 합니다.")
        expected = set(TOOL_SCHEMAS[name]["function"]["parameters"]["required"])
        if set(arguments) != expected:
            raise AgentError(f"{name}의 입력 필드는 {sorted(expected)}입니다.")
        self.emit("TOOL CALL", {"tool": name, "arguments": arguments})
        if name == "record_plan":
            steps = arguments["steps"]
            if not isinstance(steps, list) or not 1 <= len(steps) <= 3 or not all(isinstance(s, str) and s.strip() for s in steps):
                raise AgentError("계획은 1~3개의 문장 배열이어야 합니다.")
            self.plan = steps
            self.emit("PLAN", steps)
            result = {"recorded": steps}
        elif name == "list_snack_sets":
            result = {"sets": deepcopy(CATALOG)}
        elif name == "quote_sets":
            people = arguments["people"]
            if people != self.case["people"]:
                raise AgentError(f"이 문제의 인원은 {self.case['people']}명입니다.")
            result = {"people": people, "budget": self.case["budget"],
                      "quotes": [dict(s, total_krw=s["unit_price"] * people,
                                      within_budget=s["unit_price"] * people <= self.case["budget"]) for s in CATALOG]}
        else:
            if arguments["case_id"] != self.case["case_id"]:
                raise AgentError(f"현재 문제 번호는 {self.case['case_id']}입니다.")
            if arguments["set_id"] not in ("A", "B", "C"):
                raise AgentError("set_id는 A, B, C 중 하나입니다.")
            result = verify_selection(self.case, arguments["set_id"])
        self.called.append(name)
        self.results.append({"tool": name, "arguments": deepcopy(arguments), "result": deepcopy(result)})
        self.emit("TOOL RESULT", {"tool": name, "result": result})
        return result


# ----------------------------------------------------------------------------- 모델 클라이언트
class OllamaClient:
    def __init__(self, model, base_url="http://127.0.0.1:11434", timeout=300):
        self.model, self.base_url, self.timeout = model, base_url.rstrip("/"), timeout

    def request(self, path, payload=None):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        req = Request(self.base_url + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            raise AgentError(f"Ollama HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}") from exc
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise AgentError(f"Ollama에 연결할 수 없습니다 ({self.base_url}): {exc}") from exc

    def has_model(self, name=None):
        name = name or self.model
        names = set()
        for m in self.request("/api/tags").get("models", []):
            names |= {m.get("name"), m.get("model")}
        return name in names or f"{name}:latest" in names

    def check(self):
        version = self.request("/api/version").get("version", "")
        if not self.has_model():
            raise AgentError(f"{self.model} 모델이 없습니다. ollama pull {self.model}을 실행하세요.")
        capabilities = self.request("/api/show", {"model": self.model}).get("capabilities", [])
        if capabilities and "tools" not in capabilities:
            raise AgentError(f"{self.model}은 도구 호출을 지원하지 않습니다: {capabilities}")
        return {"version": version, "model": self.model, "capabilities": capabilities}

    def create_model(self, name, base_model, system):
        """기본 모델 가중치를 공유하는 Agent 전용 모델을 만든다 (ollama create와 같음)."""
        payload = {"model": name, "from": base_model, "system": system,
                   "parameters": dict(MODEL_PARAMETERS), "stream": False}
        if self.request("/api/create", payload).get("status") != "success":
            raise AgentError(f"{name} 모델을 만들지 못했습니다.")

    def chat(self, messages, tools):
        """스트리밍으로 응답을 받아 하나의 assistant 메시지로 합친다."""
        payload = {"model": self.model, "messages": messages, "stream": True, "options": dict(MODEL_PARAMETERS)}
        if tools:
            payload["tools"] = tools
        req = Request(self.base_url + "/api/chat", data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"})
        content, tool_calls, done_reason = [], [], None
        started = last = time.monotonic()
        try:
            with urlopen(req, timeout=self.timeout) as response:
                for line in response:
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if chunk.get("error"):
                        raise AgentError(f"Ollama 오류: {chunk['error']}")
                    msg = chunk.get("message") or {}
                    content.append(msg.get("content") or "")
                    tool_calls.extend(msg.get("tool_calls") or [])
                    if chunk.get("done"):
                        done_reason = chunk.get("done_reason")
                    if time.monotonic() - last >= 2:
                        last = time.monotonic()
                        sys.stderr.write(f"\r  {self.model} 응답 중... {last - started:.0f}초 ")
                        sys.stderr.flush()
        except HTTPError as exc:
            raise AgentError(f"Ollama HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}") from exc
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise AgentError(f"Ollama 응답 오류 ({self.base_url}): {exc}") from exc
        finally:
            if last != started:
                sys.stderr.write("\r" + " " * 60 + "\r")
                sys.stderr.flush()
        message = {"role": "assistant", "content": "".join(content),
                   "done_reason": done_reason, "seconds": round(time.monotonic() - started, 1)}
        if tool_calls:
            message["tool_calls"] = tool_calls
        return message


def native_call(name, arguments):
    return {"function": {"name": name, "arguments": arguments}}


class ReplayClient:
    """정해 둔 요청을 재생한다. Ollama 없이 구조만 확인할 때 사용 (모델 판단 없음)."""
    def __init__(self, case, key, use_tools):
        self.case, self.key, self.use_tools, self.turn = case, key, use_tools, 0
        self.model = ROLES[key].model + " (replay)"

    def chat(self, messages, tools):
        self.turn += 1
        chosen = "B" if self.key == "planner" and self.case["vegan_required"] else \
                 "A" if self.key == "planner" else best_set(self.case)["set_id"]
        plan = {"planner": ["간식 목록 확인", "후보 제안"], "budget": ["8명 총액 계산", "조건에 맞는 세트 제안"],
                "reviewer": ["앞선 제안 검사", "최종 선택"]}[self.key]
        if not self.use_tools:
            return {"role": "assistant", "content": json.dumps(
                {"plan": plan, "set_id": "A", "summary": "표를 보고 A를 골랐습니다."}, ensure_ascii=False)}
        if self.turn == 1:
            call = {"planner": native_call("list_snack_sets", {}),
                    "budget": native_call("quote_sets", {"people": self.case["people"]}),
                    "reviewer": native_call("check_constraints", {"case_id": self.case["case_id"], "set_id": chosen})}
            return {"role": "assistant", "content": "",
                    "tool_calls": [native_call("record_plan", {"steps": plan}), call[self.key]]}
        return {"role": "assistant", "content": json.dumps(
            {"set_id": chosen, "summary": f"{chosen} 세트를 제안합니다."}, ensure_ascii=False)}


# ----------------------------------------------------------------------------- Agent 실행 루프
def parse_final(content):
    raw = (content or "").strip()
    if not raw:
        raise AgentError("도구 요청도 최종 답도 없습니다.")
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    match = re.search(r"\{.*\}", raw, re.S)
    try:
        final = json.loads(match.group(0) if match else raw)
    except ValueError as exc:
        raise AgentError("최종 답이 JSON 형식이 아닙니다.") from exc
    if not isinstance(final, dict) or final.get("set_id") not in ("A", "B", "C") or not isinstance(final.get("summary"), str):
        raise AgentError('최종 답은 {"set_id": "A|B|C", "summary": "..."} 형식이어야 합니다.')
    return final


MAX_MODEL_CALLS = 8     # Agent 하나가 모델을 호출하는 최대 횟수
MAX_TOOL_ERRORS = 3     # 잘못된 도구 요청을 모델에게 돌려주는 최대 횟수


def ready_to_answer(role, registry):
    """계획을 기록했고 자기 도구를 모두 불렀으면 최종 답을 쓸 차례다.
    검토자는 optimal: true인 검사 결과가 하나 이상 있어야 한다."""
    if not registry.plan or not set(role.tools) <= set(registry.called):
        return False
    if "check_constraints" in role.tools:
        return any(r["tool"] == "check_constraints" and r["result"].get("optimal") for r in registry.results)
    return True


def run_agent(key, case, board, client, use_tools, emit, max_model_calls=MAX_MODEL_CALLS):
    """Agent 하나를 실행한다: 프롬프트 구성 → 모델 호출 → 도구 실행, 결과 재입력 반복 → 최종 답."""
    role = ROLES[key]
    allowed = ("record_plan",) + role.tools if use_tools else ()
    registry = ToolRegistry(case, allowed, emit)
    model_name = getattr(client, "model", role.model)

    # 역할(Persona)은 Agent 모델의 SYSTEM에 들어 있으므로, 요청에는 작업 지시와 문제, 공유 작업판만 보낸다.
    context = {"problem": case, "shared_board": deepcopy(board)}
    if not use_tools:
        context["note"] = "이번에는 도구가 없습니다. catalog를 보고 판단하고, 최종 JSON에 plan(짧은 작업 계획 1~3개 배열)도 넣으세요."
        context["catalog"] = deepcopy(CATALOG)
    messages = [{"role": "user", "content": json.dumps(context, ensure_ascii=False)}]

    emit("AGENT", {"agent": role.name, "model": model_name, "persona": role.persona})
    emit("MEMORY", {"agent": role.name, "previous_agents": [e["agent"] for e in board]})

    repair_used, tool_errors, server_retries, finalizing = False, 0, 0, False
    for turn in range(1, max_model_calls + 1):
        tools = [TOOL_SCHEMAS[n] for n in allowed]
        if use_tools and ready_to_answer(role, registry):
            # 필요한 도구 결과가 모두 모이면 도구 목록을 빼고 최종 답을 요청한다 (반복 종료는 Harness가 정함)
            tools = []
            if not finalizing:
                finalizing = True
                emit("FINALIZE", {"agent": role.name})
                messages.append({"role": "user", "content": "필요한 도구 결과가 모두 모였습니다. "
                                 "이제 도구를 부르지 말고 최종 JSON 하나로 답하세요."})
        emit("MODEL", {"agent": role.name, "model": model_name, "call": turn})
        try:
            reply = client.chat(messages, tools)
        except AgentError as exc:
            # 모델이 만든 도구 호출 JSON이 깨지면 Ollama가 500을 돌려준다 → 형식 안내를 붙여 다시 요청
            if "HTTP 5" in str(exc) and server_retries < 3:
                server_retries += 1
                emit("RETRY", f"도구 호출 형식 오류, 다시 요청합니다: {exc}")
                messages.append({"role": "user", "content": "방금 도구 호출의 JSON 형식이 깨졌습니다. "
                                 "문자열 안에 큰따옴표를 쓰지 말고, 짧은 문장으로 다시 호출하세요."})
                continue
            raise
        if "seconds" in reply:
            emit("TIME", {"agent": role.name, "seconds": reply["seconds"]})
        message = {"role": "assistant", "content": reply.get("content", "")}
        if reply.get("tool_calls"):
            message["tool_calls"] = deepcopy(reply["tool_calls"])
        messages.append(deepcopy(message))

        calls = message.get("tool_calls") or []
        if calls:                                   # 도구 요청 → 검사 후 실행 → 결과를 tool 메시지로 추가
            if not use_tools or finalizing:
                messages.append({"role": "user", "content": "도구 없이 최종 JSON 하나로만 답하세요."})
                continue
            for call in calls:
                fn = call.get("function", {}) if isinstance(call, dict) else {}
                name, arguments = fn.get("name"), fn.get("arguments")
                if any(r["tool"] == name and r["arguments"] == arguments for r in registry.results):
                    # 같은 도구를 같은 입력으로 다시 부르면 실행하지 않고 최종 답을 쓰도록 안내한다
                    emit("REPEAT", {"tool": name})
                    result = {"note": "이미 받은 결과입니다. 같은 도구를 다시 부르지 말고 최종 JSON 답을 쓰세요."}
                    messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result, ensure_ascii=False)})
                    continue
                try:
                    result = registry.execute(name, arguments)
                except (AgentError, ValueError, TypeError) as exc:
                    tool_errors += 1
                    emit("TOOL ERROR", {"tool": name, "error": str(exc)})
                    if tool_errors > MAX_TOOL_ERRORS:
                        raise AgentError(f"잘못된 도구 요청이 {MAX_TOOL_ERRORS}회를 넘었습니다.") from exc
                    result = {"error": str(exc), "hint": "입력을 고쳐서 다시 호출하세요."}
                messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result, ensure_ascii=False)})
            continue

        try:                                        # 도구 요청 없음 → 최종 답 확인
            if not message["content"].strip() and reply.get("done_reason") == "length":
                raise AgentError("출력 한도에 도달해 답이 비었습니다.")
            final = parse_final(message["content"])
            if use_tools:
                missing = set(role.tools) - set(registry.called)
                if not registry.plan or missing:
                    raise AgentError(f"필수 작업이 빠졌습니다. 계획: {bool(registry.plan)}, 호출 안 한 도구: {sorted(missing)}")
                if "check_constraints" in role.tools:
                    checks = [r for r in registry.results if r["tool"] == "check_constraints"
                              and r["arguments"]["set_id"] == final["set_id"]]
                    if not checks:
                        raise AgentError("최종 선택한 세트를 check_constraints로 검사하지 않았습니다.")
                    if not checks[-1]["result"]["optimal"]:
                        raise AgentError("최종 선택이 검사 결과와 맞지 않습니다 (optimal: false).")
            else:
                plan = final.get("plan")
                if not isinstance(plan, list) or not 1 <= len(plan) <= 3:
                    raise AgentError("도구 없이 답할 때는 plan(1~3개)이 필요합니다.")
                registry.plan = plan
                emit("PLAN", plan)
        except AgentError as exc:
            emit("RAW ANSWER", message["content"])
            if not repair_used and turn < max_model_calls:   # 한 번만 고칠 기회를 준다
                repair_used = True
                emit("RETRY", str(exc))
                messages.append({"role": "user", "content": f"{exc} 필요한 도구를 호출하고, 최종 답은 JSON 하나로만 쓰세요."})
                continue
            raise
        emit("AGENT ANSWER", {"agent": role.name, **final})
        entry = {"agent": role.name, "model": model_name, "plan": registry.plan,
                 "final": final, "tool_results": registry.results}
        board.append(deepcopy(entry))
        return dict(entry, messages=messages, model_calls=turn)
    raise AgentError(f"{role.name}: 모델 호출 {max_model_calls}회 안에 끝나지 않았습니다.")


def run_case(case_id, use_tools, mode, agent_clients, emit):
    """문제 하나를 세 Agent가 순서대로 처리한다. 문제마다 공유 작업판을 새로 시작한다."""
    case = get_case(case_id)
    board, agents = [], []
    outcome = {"case": case, "mode": mode, "data_fingerprint": data_fingerprint(),
               "settings": {"USE_TOOLS": use_tools}, "agents": agents, "shared_board": board, "status": "error"}
    emit("CASE", dict(case, harness=HARNESS_VERSION))
    started = time.monotonic()
    try:
        for i, key in enumerate(TEAM):
            client = ReplayClient(case, key, use_tools) if mode == "replay" else agent_clients[key]
            agents.append(run_agent(key, case, board, client, use_tools, emit))
            if i + 1 < len(TEAM):
                emit("HANDOFF", {"from": agents[-1]["model"], "to": ROLES[TEAM[i + 1]].model,
                                 "set_id": agents[-1]["final"]["set_id"], "board_entries": len(board)})
        final = agents[-1]["final"]
        verification = verify_selection(case, final["set_id"])
        outcome.update(final=final, verification=verification,
                       status="success" if verification["optimal"] else "incorrect")
        emit("FINAL", final)
        emit("VERIFY", verification)
    except (AgentError, ValueError, TypeError, KeyError) as exc:
        outcome["error"] = str(exc)
        emit("ERROR", str(exc))
    outcome["seconds"] = round(time.monotonic() - started, 1)
    return outcome


def new_run_id():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex[:5]


def check_live(client, emit):
    """Ollama 연결과 도구 호출 1회를 점검한다."""
    info = client.check()
    emit("CHECK", info)
    reply = client.chat([{"role": "user", "content": "quote_sets 도구를 people=8로 한 번 호출하세요."}],
                        [TOOL_SCHEMAS["quote_sets"]])
    calls = reply.get("tool_calls") or []
    if not calls or calls[0].get("function", {}).get("name") != "quote_sets":
        raise AgentError("모델이 도구 호출을 하지 않았습니다. 모델 이름을 확인하세요.")
    ToolRegistry(get_case(1), ("quote_sets",), emit).execute("quote_sets", calls[0]["function"].get("arguments"))
    emit("CHECK", "연결 점검 완료")