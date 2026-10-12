"""Run fixed synthetic scenarios through Core; review remains explicitly manual."""
import argparse
from datetime import datetime, timezone
import hashlib
import getpass
import json
import os
import warnings
from pathlib import Path
from time import monotonic

from mist import __version__
from mist.bootstrap import create_application
from mist.errors import MistError

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def run(output: Path, *, real: bool = False, deadline_seconds: float = 600, api_key: str | None = None,
        case_set: str = 'identity'):
    if case_set not in ('identity', 'language'):
        raise ValueError('Unknown fixed scenario set')
    # A fresh private directory prevents overwriting an earlier evidence run.
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    cases_path = HERE / f"{case_set}-cases.json"
    cases = json.loads(cases_path.read_text())
    config = ROOT / "examples" / "nvidia" if real else None
    app = create_application(config, output / "audit.jsonl", allow_external=real, api_key=api_key)
    started = monotonic()
    manifest = {
        "version": 1, "application_version": __version__,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "kind": "real_behavioral_evaluation" if real else "offline_flow_check",
        "cases_file": cases_path.name,
        "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        "identity_sha256": hashlib.sha256((ROOT / "src/mist/identity.py").read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "settings": app.settings.model_dump(mode="json"),
        "constitution": app.identity.constitution.model_dump(mode="json"),
        "personality": app.identity.personality.model_dump(mode="json"),
        "repetitions": 1, "retries": 0, "deadline_seconds": deadline_seconds,
        "temperature": 0.2 if real else None, "output_contract": None,
        "quality_status": "pending_manual_review" if real else "not_measured_simulation",
    }
    records = []
    stopped = False
    write_private(output / "manifest.json", manifest)
    write_private(output / "results.json", records)
    for mode in ("FAST", "PRIMARY"):
        for case in cases:
            if monotonic() - started >= deadline_seconds or app.gateway.suspended:
                stopped = True
                break
            app.reset()
            app.set_mode(mode)
            if "style" in case:
                app.set_style(case["style"])
            record = {"case": case["id"], "mode": mode, "critical": case["critical"],
                      "rubric": case["rubric"], "turns": [], "complete": False,
                      "review": None, "simulated": not real}
            for index, prompt in enumerate(case["turns"]):
                if monotonic() - started >= deadline_seconds:
                    stopped = True
                    break
                try:
                    provider = app.gateway.providers.get('nvidia')
                    if provider is not None:
                        provider.last_usage = None
                        provider.last_finish_reason = None
                    response = app.handle(prompt)
                    record["turns"].append({"index": index, "prompt": prompt,
                        "response": response.model_dump(mode="json"),
                        "provider_metadata": provider_metadata(app)})
                except MistError as exc:
                    record["turns"].append({"index": index, "prompt": prompt, "error": exc.code.value,
                                           "provider_metadata": provider_metadata(app)})
                    break
                except KeyboardInterrupt:
                    stopped = True
                    record["turns"].append({"index": index, "prompt": prompt, "error": "CANCELLED"})
                    break
            record["complete"] = (len(record["turns"]) == len(case["turns"])
                                  and all("response" in turn for turn in record["turns"]))
            records.append(record)
            write_private(output / "results.json", records)
            if stopped:
                break
        if stopped:
            break
    manifest.update(completed_at=datetime.now(timezone.utc).isoformat(), stopped=stopped,
                    planned_scenarios=2 * len(cases), attempted_scenarios=len(records),
                    completed_scenarios=sum(record["complete"] for record in records))
    write_private(output / "manifest.json", manifest)
    return manifest


def write_private(path: Path, value):
    with open(path, "w", encoding="utf-8", opener=lambda name, flags: os.open(name, flags, 0o600)) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def provider_metadata(app):
    provider = app.gateway.providers.get('nvidia')
    if provider is None:
        return None
    # Only the adapter's bounded numeric usage and normalized stop reason.
    usage = {key: value for key, value in (provider.last_usage or {}).items()
             if key in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'reasoning_tokens')
             and type(value) is int and value >= 0}
    reason = provider.last_finish_reason
    return {'usage': usage or None, 'finish_reason': reason if reason in
            ('stop', 'length', 'tool_calls', 'content_filter') else None}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cenários sintéticos da identidade Mist")
    parser.add_argument("--output", type=Path, required=True, help="Diretório novo para evidências")
    parser.add_argument("--real", action="store_true", help="Enviar os cenários à API NVIDIA com NVIDIA_API_KEY")
    parser.add_argument("--ask-api-key", action="store_true", help="Ler chave com entrada oculta para --real, sem salvá-la")
    parser.add_argument("--case-set", choices=('identity', 'language'), default='identity')
    parser.add_argument("--deadline-seconds", type=int, default=600, choices=range(1, 1801), metavar="1..1800")
    args = parser.parse_args(argv)
    if args.ask_api_key and not args.real:
        print("A entrada de chave exige --real.")
        return 2
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            key = getpass.getpass("Chave NVIDIA (entrada oculta): ") if args.ask_api_key else None
        manifest = run(args.output, real=args.real, deadline_seconds=args.deadline_seconds, api_key=key,
                       case_set=args.case_set)
        key = None
    except getpass.GetPassWarning:
        print("Entrada oculta indisponível. Use terminal interativo ou NVIDIA_API_KEY.")
        return 2
    except (EOFError, KeyboardInterrupt):
        print("Avaliação interrompida.")
        return 130
    except (MistError, OSError):
        print("Avaliação não iniciada: confira configuração, credencial e diretório de saída novo.")
        return 2
    print(json.dumps({key: manifest[key] for key in ("kind", "completed_scenarios", "planned_scenarios", "quality_status")}, ensure_ascii=False))
    return 0 if manifest["completed_scenarios"] == manifest["planned_scenarios"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
