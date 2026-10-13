"""Offline aggregation and blinded review packaging; never calls a provider."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from math import isfinite
from pathlib import Path
import random
from statistics import median


def read_run(root):
    manifest = json.loads((root / "manifest.json").read_text())
    rows = [json.loads(line) for line in (root / "results.jsonl").read_text().splitlines()]
    ids = [r["request_id"] for r in rows]
    keys = [(r["candidate"], r["case"], r["repetition"]) for r in rows]
    if len(set(ids)) != len(ids) or len(set(keys)) != len(keys):
        raise ValueError("Duplicate observations")
    for row in rows:
        if not isfinite(row["duration_ms"]) or row["duration_ms"] < 0:
            raise ValueError("Invalid duration")
    return manifest, rows


def percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def blind(root):
    manifest, rows = read_run(root)
    cases = {c["id"]: c for c in manifest["cases"]}
    qualitative = [r for r in rows if r["case"] in cases and "rubric" in cases[r["case"]]]
    random.Random(918271).shuffle(qualitative)
    prior = {}
    if (root / "blind-review.json").exists():
        prior = {item["id"]: item for item in json.loads((root / "blind-review.json").read_text())}
    mapping, review = {}, []
    for index, row in enumerate(qualitative, 1):
        identifier = "answer-" + hashlib.sha256(row["request_id"].encode()).hexdigest()[:10]
        mapping[identifier] = {k: row[k] for k in ("request_id", "candidate", "case", "repetition")}
        item = {"id": identifier, "task": row["case"], "prompt": cases[row["case"]]["prompt"],
                       "criteria": cases[row["case"]]["rubric"], "text": row["text"],
                       "word_count": len((row["text"] or "").split()), "scores": None, "notes": None}
        if identifier in prior:
            old = prior[identifier]
            if old["text"] != item["text"] or old["task"] != item["task"]:
                raise ValueError("Conflicting blind-review identity")
            item.update(scores=old["scores"], notes=old["notes"])
        review.append(item)
    (root / "blind-map.json").write_text(json.dumps(mapping, indent=2))
    (root / "blind-review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2))
    return review


def aggregate(root):
    manifest, rows = read_run(root)
    cases = {c["id"]: c for c in manifest["cases"]}
    repeat = manifest["repetitions"]
    planned = len(cases) * repeat
    objective_planned = sum("expected" in c for c in cases.values()) * repeat
    critical_planned = sum(c.get("critical", False) for c in cases.values()) * repeat
    qualitative_planned = sum(len(c.get("rubric", [])) for c in cases.values()) * repeat
    mapping = json.loads((root / "blind-map.json").read_text())
    review = json.loads((root / "blind-review.json").read_text())
    qualitative_scores = {}
    for item in review:
        scores = item["scores"]
        if not isinstance(scores, list) or len(scores) != 4 or any(type(n) is not int or n not in (0, 1) for n in scores):
            raise ValueError(f"Unreviewed answer: {item['id']}")
        if not item["notes"]:
            raise ValueError("Review needs a rationale")
        qualitative_scores[mapping[item["id"]]["request_id"]] = sum(scores)
    summaries = []
    for candidate in manifest["candidates"]:
        name = candidate["id"]
        tests = [r for r in rows if r["candidate"] == name and r["case"] in cases]
        probe = next(r for r in rows if r["candidate"] == name and r["case"] == "availability")
        successful = [r for r in tests if r["success"]]
        objective = [r for r in tests if "expected" in cases[r["case"]]]
        critical = [r for r in tests if r["critical"]]
        qualitative = [r for r in tests if "rubric" in cases[r["case"]]]
        seconds = [r["duration_ms"] / 1000 for r in successful]
        active = probe["success"]
        reliability = 100 * len(successful) / planned if active else None
        objective_correct = sum(r["objective_pass"] is True for r in objective)
        critical_correct = sum(r["objective_pass"] is True for r in critical)
        communication_points = sum(qualitative_scores[r["request_id"]] for r in qualitative)
        objective_pct = 100 * objective_correct / objective_planned if active else None
        communication_pct = 100 * communication_points / qualitative_planned if active else None
        quality = 0.75 * objective_pct + 0.25 * communication_pct if active else None
        complete = (len(tests) == planned and len(objective) == objective_planned
                    and len(critical) == critical_planned and len(qualitative) * 4 == qualitative_planned)
        eligible = bool(active and complete and reliability >= 95 and critical_correct == critical_planned
                        and objective_pct >= 85)
        usages = [r["usage"] for r in tests if r["usage"] is not None and "total_tokens" in r["usage"]]
        summary = {"candidate": name, "model_id": candidate["model_id"], "available": active,
                   "availability_error": probe["error"], "planned": planned if active else 0,
                   "completed": len(tests), "successful": len(successful), "complete": complete,
                   "reliability_pct": reliability, "objective_correct": objective_correct if active else None,
                   "objective_planned": objective_planned if active else 0, "objective_pct": objective_pct,
                   "critical_correct": critical_correct if active else None,
                   "critical_planned": critical_planned if active else 0,
                   "communication_points": communication_points if active else None,
                   "communication_possible": qualitative_planned if active else 0,
                   "communication_pct": communication_pct, "quality_pct": quality,
                   "median_seconds": median(seconds) if seconds else None,
                   "p95_seconds": percentile(seconds, .95),
                   "known_tokens": sum(u["total_tokens"] for u in usages) if usages else None,
                   "usage_coverage": len(usages), "eligible": eligible,
                   "errors": dict(Counter(r["error"] for r in tests if not r["success"])),
                   "objective_failures": [{"case": r["case"], "repetition": r["repetition"],
                                           "request_id": r["request_id"]} for r in objective if r["objective_pass"] is not True]}
        summaries.append(summary)
    eligible = [s for s in summaries if s["eligible"]]
    choice = {"fast": None, "primary": None, "provisional": True}
    if eligible:
        best = max(s["quality_pct"] for s in eligible)
        tied = [s for s in eligible if best - s["quality_pct"] < 2]
        primary = min(tied, key=lambda s: (s["median_seconds"], -s["reliability_pct"]))
        fast_pool = [s for s in eligible if s["objective_pct"] >= 90 and best - s["quality_pct"] <= 5]
        choice["primary"] = primary["candidate"]
        if fast_pool:
            choice["fast"] = min(fast_pool, key=lambda s: (s["median_seconds"], -s["reliability_pct"]))["candidate"]
    result = {"summaries": summaries, "choice": choice,
              "source_sha256": hashlib.sha256((root / "results.jsonl").read_bytes()).hexdigest()}
    (root / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    fields = ["candidate", "available", "completed", "successful", "reliability_pct", "objective_correct",
              "objective_planned", "critical_correct", "critical_planned", "communication_points",
              "communication_possible", "quality_pct", "median_seconds", "p95_seconds", "known_tokens", "eligible"]
    with (root / "summary.csv").open("w") as target:
        writer = csv.DictWriter(target, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(summaries)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--blind", action="store_true")
    args = parser.parse_args()
    print(json.dumps(blind(args.run) if args.blind else aggregate(args.run), ensure_ascii=False, indent=2))
