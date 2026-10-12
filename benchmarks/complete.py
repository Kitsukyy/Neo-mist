"""Complete only unattempted cells after the scheduling deadline; never retry failures."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import random
from time import monotonic
import warnings

from benchmarks.analyze import read_run
from benchmarks.run import HERE, run_one
from mist.nvidia import NvidiaProvider


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    root = args.run
    manifest, rows = read_run(root)
    status = json.loads((root / "status.json").read_text())
    if not status["halted"] or status["completed"] >= status["planned"]:
        parser.error("A execução não tem células pendentes após interrupção.")
    if (root / "continuation.json").exists():
        parser.error("Uma continuação já foi registrada.")
    if any(r["error"] in ("PROVIDER_AUTH", "RATE_LIMIT", "AUDIT_FAILURE") for r in rows):
        parser.error("Não continuar uma execução bloqueada por acesso, cota ou auditoria.")
    if hashlib.sha256((HERE / "PROTOCOL.md").read_bytes()).hexdigest() != manifest["protocol_sha256"]:
        parser.error("O protocolo original mudou.")
    seen = {(r["candidate"], r["case"], r["repetition"]) for r in rows}
    candidates = [c for c in manifest["candidates"] if c["id"] in status["active_candidates"]]
    jobs = [(c, task, rep) for rep in range(1, manifest["repetitions"] + 1)
            for task in manifest["cases"] for c in candidates]
    random.Random(manifest["shuffle_seed"]).shuffle(jobs)
    jobs = [job for job in jobs if (job[0]["id"], job[1]["id"], job[2]) not in seen]
    if status["completed"] + len(jobs) != status["planned"]:
        parser.error("A cobertura registrada é inconsistente.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        key = os.environ.get("NVIDIA_API_KEY") or getpass.getpass("Chave NVIDIA (entrada oculta): ")
    NvidiaProvider(key)
    amendment = {"created_at": datetime.now(timezone.utc).isoformat(),
                 "reason": "Original scheduling deadline; complete unattempted cells only, no retries",
                 "original_status": status, "original_results_sha256": hashlib.sha256((root / "results.jsonl").read_bytes()).hexdigest(),
                 "additional_scheduling_deadline_seconds": 600, "remaining": len(jobs),
                 "unchanged": ["cases", "candidates", "identity", "parameters", "scoring", "selection_thresholds"]}
    (root / "continuation.json").write_text(json.dumps(amendment, indent=2))
    deadline = monotonic() + 600
    completed = status["completed"]
    halted = False
    with (root / "results.jsonl").open("a") as log, ThreadPoolExecutor(max_workers=manifest["workers"]) as pool:
        pending, submitted = {}, 0
        while (submitted < len(jobs) or pending) and not (halted and not pending):
            while not halted and submitted < len(jobs) and len(pending) < manifest["workers"]:
                if monotonic() >= deadline:
                    halted = True
                    break
                c, task, rep = jobs[submitted]
                future = pool.submit(run_one, c, task, rep, key, root / "audit.jsonl",
                                     manifest["max_tokens"], manifest["timeout_seconds"])
                pending[future] = True
                submitted += 1
            if not pending:
                break
            future = next(as_completed(tuple(pending)))
            pending.pop(future)
            record = future.result()
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
            log.flush()
            completed += 1
            print(json.dumps({"done": completed, "planned": status["planned"], "candidate": record["candidate"],
                              "case": record["case"], "success": record["success"], "error": record["error"]}), flush=True)
            if record["error"] in ("PROVIDER_AUTH", "RATE_LIMIT", "AUDIT_FAILURE"):
                halted = True
    final = {**status, "completed": completed, "halted": halted,
             "continued": True, "finished_at": datetime.now(timezone.utc).isoformat()}
    (root / "status.json").write_text(json.dumps(final, indent=2))
    print(json.dumps(final), flush=True)
    return 0 if completed == status["planned"] and not halted else 2


if __name__ == "__main__":
    raise SystemExit(main())
