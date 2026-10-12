"""Bounded real-API experiment. Stores synthetic final answers, never reasoning or credentials."""
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

from mist.audit import JsonAudit
from mist.config import load_config
from mist.errors import MistError
from mist.gateway import Gateway
from mist.identity import Identity
from mist.nvidia import NvidiaProvider
from mist.safety import OutputGuard
from mist.schemas import ConversationMessage, Envelope, GenerationRequest, ModelConfig, Role, Style

HERE = Path(__file__).resolve().parent


def strict_equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(strict_equal(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(strict_equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def score_objective(text, expected):
    try:
        # Markdown fences are tolerated; no prose, coercion or substring scoring.
        value = text.strip()
        if value.startswith("```json\n") and value.endswith("\n```"):
            value = value[8:-4]
        elif value.startswith("```\n") and value.endswith("\n```"):
            value = value[4:-4]
        return strict_equal(json.loads(value), expected)
    except (ValueError, TypeError):
        return False


def run_one(candidate, case, repetition, key, audit_path, max_tokens, timeout, structured_contract=False):
    _, constitution, personality = load_config()
    model = ModelConfig(id=candidate["id"], provider="nvidia", model_id=candidate["model_id"],
                        external=True, destination="nvidia-integrate", enable_thinking=candidate["enable_thinking"])
    identity = Identity(constitution, personality)
    instructions = identity.instructions(case["prompt"], Style.AUTO)
    instructions += f" Modelo configurado para esta geração: {model.model_id}; provedor: nvidia."
    if structured_contract and "expected" in case:
        fields = {k: ("booleano" if type(v) is bool else "inteiro" if type(v) is int
                      else "lista" if type(v) is list else "string")
                  for k, v in case["expected"].items()}
        instructions += (" Para esta resposta, retorne um objeto JSON com exatamente estas chaves e tipos: "
                         + json.dumps(fields, ensure_ascii=False)
                         + ". Mantenha as chaves originais, sem texto adicional. Listas ficam dentro do objeto. "
                         "Use literalmente os valores textuais pedidos. Para classificação, mantenha o rótulo "
                         "original do registro, sem explicação ou sufixo. Os valores devem ser calculados ou "
                         "deduzidos da pergunta; este contrato só especifica a estrutura.")
    request = Envelope(model=model, request=GenerationRequest(messages=(
        ConversationMessage(role=Role.SYSTEM, content=instructions),
        ConversationMessage(role=Role.USER, content=case["prompt"]),
    )))
    provider = NvidiaProvider(key, max_tokens=max_tokens, timeout=timeout)
    gateway = Gateway({"nvidia": provider}, OutputGuard(("nvidia-integrate",)), JsonAudit(audit_path))
    start = monotonic()
    record = {"candidate": candidate["id"], "model_id": model.model_id, "case": case["id"],
              "category": case["category"], "repetition": repetition,
              "critical": case.get("critical", False), "request_id": str(request.request.request_id),
              "started_at": datetime.now(timezone.utc).isoformat(), "success": False,
              "text": None, "objective_pass": None, "error": None}
    try:
        response = gateway.generate(request)
        record.update(success=True, text=response.text, duration_ms=response.duration_ms)
        if "expected" in case:
            record["objective_pass"] = score_objective(response.text, case["expected"])
    except MistError as error:
        record.update(error=error.code.value, duration_ms=(monotonic() - start) * 1000)
    record["usage"] = provider.last_usage
    record["finish_reason"] = provider.last_finish_reason
    record["completed_at"] = datetime.now(timezone.utc).isoformat()
    return record


def main():
    parser = argparse.ArgumentParser(description="Benchmark sintético da Mist na NVIDIA")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=2, choices=(1, 2, 3))
    parser.add_argument("--workers", type=int, default=2, choices=(1, 2))
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--deadline-seconds", type=float, default=1200.0)
    parser.add_argument("--qualification-results", type=Path,
                        help="Reusar exclusivamente chamadas de disponibilidade de uma execução registrada")
    parser.add_argument("--candidates", type=Path, default=HERE / "candidates.json")
    parser.add_argument("--protocol", type=Path, default=HERE / "PROTOCOL.md")
    parser.add_argument("--structured-contract", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use um diretório novo para preservar resultados anteriores.")
    if not 1 <= args.max_tokens <= 4096 or not 1 <= args.timeout <= 120 or not 60 <= args.deadline_seconds <= 3600:
        parser.error("Limites inválidos.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        key = os.environ.get("NVIDIA_API_KEY") or getpass.getpass("Chave NVIDIA (entrada oculta): ")
    # Validate before creating an experiment directory.
    NvidiaProvider(key)
    candidates = json.loads(args.candidates.read_text())
    cases = json.loads((HERE / "cases.json").read_text())
    args.output.mkdir(parents=True, mode=0o700)
    manifest = {"version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
                "repetitions": args.repetitions, "workers": args.workers,
                "max_tokens": args.max_tokens, "temperature": 0.2, "timeout_seconds": args.timeout,
                "deadline_seconds": args.deadline_seconds, "shuffle_seed": 20261012,
                "structured_contract": args.structured_contract,
                "candidates": candidates, "cases": cases,
                "cases_sha256": hashlib.sha256((HERE / "cases.json").read_bytes()).hexdigest(),
                "protocol_sha256": hashlib.sha256(args.protocol.read_bytes()).hexdigest()}
    if args.qualification_results:
        manifest["qualification_results"] = str(args.qualification_results)
        manifest["qualification_sha256"] = hashlib.sha256(args.qualification_results.read_bytes()).hexdigest()
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    audit = args.output / "audit.jsonl"
    records_path = args.output / "results.jsonl"
    deadline = monotonic() + args.deadline_seconds
    health = {"id": "availability", "category": "availability", "prompt": 'Responda apenas JSON: {"ok":true}', "expected": {"ok": True}}
    active = []
    qualification = {}
    if args.qualification_results:
        for line in args.qualification_results.read_text().splitlines():
            item = json.loads(line)
            if item["case"] == "availability":
                qualification[item["candidate"]] = item
        if set(qualification) != {c["id"] for c in candidates}:
            parser.error("Qualificação incompleta para os candidatos.")
    with records_path.open("w") as log:
        for candidate in candidates:
            record = qualification.get(candidate["id"])
            if record is None:
                record = run_one(candidate, health, 0, key, audit, args.max_tokens, args.timeout, args.structured_contract)
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
            log.flush()
            print(json.dumps({"phase": "availability", "candidate": candidate["id"], "success": record["success"],
                              "error": record["error"], "duration_ms": round(record["duration_ms"])}), flush=True)
            if record["success"]:
                active.append(candidate)
            if record["error"] in ("PROVIDER_AUTH", "RATE_LIMIT", "AUDIT_FAILURE"):
                print("Acesso/cota/auditoria indisponível: experimento interrompido.", flush=True)
                return 2
        jobs = [(candidate, case, repeat) for repeat in range(1, args.repetitions + 1)
                for case in cases for candidate in active]
        random.Random(20261012).shuffle(jobs)
        pending, submitted, completed = {}, 0, 0
        # At most two outstanding calls. Stop scheduling on quota/auth failures or deadline.
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            halted = False
            while (submitted < len(jobs) or pending) and not (halted and not pending):
                while not halted and submitted < len(jobs) and len(pending) < args.workers:
                    if monotonic() >= deadline:
                        halted = True
                        break
                    candidate, case, repeat = jobs[submitted]
                    future = pool.submit(run_one, candidate, case, repeat, key, audit, args.max_tokens, args.timeout,
                                         args.structured_contract)
                    pending[future] = (candidate["id"], case["id"])
                    submitted += 1
                if not pending:
                    break
                future = next(as_completed(tuple(pending)))
                pending.pop(future)
                record = future.result()
                log.write(json.dumps(record, ensure_ascii=False) + "\n")
                log.flush()
                completed += 1
                print(json.dumps({"phase": "benchmark", "done": completed, "planned": len(jobs),
                                  "candidate": record["candidate"], "case": record["case"],
                                  "success": record["success"], "objective_pass": record["objective_pass"],
                                  "error": record["error"], "duration_ms": round(record["duration_ms"])}), flush=True)
                if record["error"] in ("PROVIDER_AUTH", "RATE_LIMIT", "AUDIT_FAILURE"):
                    halted = True
        status = {"completed": completed, "planned": len(jobs), "halted": halted,
                  "active_candidates": [c["id"] for c in active], "finished_at": datetime.now(timezone.utc).isoformat()}
        (args.output / "status.json").write_text(json.dumps(status, indent=2))
        print(json.dumps(status), flush=True)
    return 0 if not halted and completed == len(jobs) else 2


if __name__ == "__main__":
    raise SystemExit(main())
