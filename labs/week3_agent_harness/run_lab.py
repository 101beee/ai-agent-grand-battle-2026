"""실행 순서: --check → inspect → models → run → (USE_TOOLS = True) → run → cases → report"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import student_config
from harness import (CASES, CATALOG, ROLES, TEAM, LabError, OllamaClient, check_live,
                     data_fingerprint, modelfile_text, new_run_id, role_prompt, run_case)

ROOT = Path(__file__).resolve().parent


def agent_bases():
    bases = dict(getattr(student_config, "AGENT_BASES", {}))
    return {k: bases.get(k, student_config.MODEL) for k in TEAM}


def create_models(client, emit, mode):
    """Agent마다 Modelfile을 쓰고 Ollama 모델을 만든다."""
    folder = ROOT / "modelfiles"
    folder.mkdir(exist_ok=True)
    for key, base in agent_bases().items():
        (folder / f"{key}.Modelfile").write_text(modelfile_text(key, base), encoding="utf-8")
        emit("MODELFILE", {"model": ROLES[key].model, "from": base, "file": f"modelfiles/{key}.Modelfile"})
    if mode == "replay":
        return
    for key, base in agent_bases().items():
        if not client.has_model(base):
            raise LabError(f"기본 모델 {base}이 없습니다. ollama pull {base}을 실행하세요.")
        client.create_model(ROLES[key].model, base, role_prompt(key))
        emit("MODEL CREATED", {"model": ROLES[key].model, "from": base})


def agent_clients(base_client):
    clients = {}
    for key in TEAM:
        name = ROLES[key].model
        if not base_client.has_model(name):
            raise LabError(f"{name} 모델이 없습니다. 먼저 --step models를 실행하세요.")
        clients[key] = OllamaClient(name, base_client.base_url)
    return clients


def report(runs_root, mode, emit):
    batches = []
    for path in runs_root.glob("*/manifest.json"):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if manifest.get("step") == "cases" and manifest.get("mode") == mode:
            batches.append((manifest.get("created_at", ""), path, manifest))
    if not batches:
        raise LabError("cases 실행 기록이 없습니다. 먼저 --step cases를 실행하세요.")
    _, path, manifest = max(batches, key=lambda b: b[0])
    if manifest.get("data_fingerprint") != data_fingerprint():
        raise LabError("데이터가 바뀌었습니다. --step cases를 다시 실행하세요.")
    emit("REPORT", {"run_id": manifest["run_id"], "settings": manifest["settings"], "created_at": manifest["created_at"]})
    print("문제  선택  총액(원)  정답  판정", flush=True)
    for case_id in (1, 2, 3):
        record_path = path.parent / f"case_{case_id}.json"
        if not record_path.exists():
            print(f"{case_id:<5} 기록 없음", flush=True)
            continue
        record = json.loads(record_path.read_text(encoding="utf-8"))
        final, verify = record.get("final", {}), record.get("verification", {})
        print(f"{case_id:<5} {final.get('set_id', '-'):<5} {str(verify.get('total_krw', '-')):<9} "
              f"{str(verify.get('expected_set_id', '-')):<5} {record['status']}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Agent Harness 실습")
    parser.add_argument("--step", choices=("inspect", "models", "run", "cases", "report"), default="inspect")
    parser.add_argument("--case", dest="case_id", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--mode", choices=("live", "replay"), default="live")
    parser.add_argument("--check", action="store_true", help="Ollama 연결과 도구 호출 점검")
    parser.add_argument("--solution", action="store_true", help="USE_TOOLS = True로 실행 (강의자 점검용)")
    parser.add_argument("--runs-dir", type=Path, default=ROOT / "runs")
    args = parser.parse_args(argv)

    prefix = "[REPLAY]" if args.mode == "replay" else ""
    def emit(event, value):
        print(f"{prefix}[{event}] {json.dumps(value, ensure_ascii=False)}", flush=True)

    use_tools = True if args.solution else student_config.USE_TOOLS
    if not isinstance(use_tools, bool):
        emit("ERROR", "student_config.py의 USE_TOOLS는 True 또는 False여야 합니다.")
        return 1
    try:
        client = OllamaClient(student_config.MODEL, student_config.OLLAMA_URL)
        if args.check:
            check_live(client, emit)
            return 0
        if args.step == "inspect":
            emit("SETTINGS", {"USE_TOOLS": use_tools, "MODEL": student_config.MODEL})
            emit("DATA", {"catalog": CATALOG, "cases": list(CASES.values())})
            emit("ELEMENTS", {"LLM": "OllamaClient.chat()", "Planning": "record_plan",
                              "Memory": "messages, shared_board", "Tools": "ToolRegistry.execute()"})
            for key in TEAM:
                r = ROLES[key]
                emit("AGENT", {"name": r.name, "model": r.model, "from": agent_bases()[key],
                               "persona": r.persona, "tools": r.tools})
            return 0
        if args.step == "report":
            report(args.runs_dir, args.mode, emit)
            return 0
        if args.step == "models":
            create_models(client, emit, args.mode)
            return 0

        clients = None
        if args.mode == "live":
            clients = agent_clients(client)
        run_id = new_run_id()
        run_dir = args.runs_dir / run_id
        run_dir.mkdir(parents=True)
        manifest = {"run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(), "step": args.step,
                    "mode": args.mode, "data_fingerprint": data_fingerprint(),
                    "settings": {"USE_TOOLS": use_tools}, "models": {k: ROLES[k].model for k in TEAM}, "cases": []}
        for case_id in ((1, 2, 3) if args.step == "cases" else (args.case_id,)):
            traces = []
            def record(event, value):
                traces.append({"event": event, "value": value})
                emit(event, value)
            outcome = run_case(case_id, use_tools, args.mode, clients, record)
            outcome.update(run_id=run_id, step=args.step, traces=traces)
            (run_dir / f"case_{case_id}.json").write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest["cases"].append({"case_id": case_id, "status": outcome["status"]})
        (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        emit("SAVED", f"runs/{run_id}")
        return 0 if all(c["status"] == "success" for c in manifest["cases"]) else 1
    except (LabError, OSError, ValueError) as exc:
        emit("ERROR", str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
