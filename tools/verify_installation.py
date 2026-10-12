"""Verify the installed distribution, not an editable source checkout."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INSPECT = '''
import importlib.metadata as metadata, json, platform
from pathlib import Path
import mist
from mist.config import load_config
settings, constitution, personality = load_config()
print(json.dumps({
    "python": platform.python_version(), "platform": platform.platform(),
    "module_path": str(Path(mist.__file__).resolve()),
    "dependencies": {name: metadata.version(name) for name in
        ("neo-mist", "pydantic", "pydantic-core", "annotated-types", "typing-extensions", "typing-inspection")},
    "defaults_loaded": True,
    "offline_default": all(not model.external for model in settings.models),
    "autonomy_level": settings.autonomy_level, "tools_enabled": settings.tools_enabled,
}))
'''
SMOKE = '''
from mist.cli import main
from unittest.mock import patch
import socket
with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
    raise SystemExit(main(["--audit-path", "audit.jsonl", "--message", "teste sintetico da instalacao"]))
'''


def verify():
    with tempfile.TemporaryDirectory(prefix="mist-installed-check-") as directory:
        commands = [
            ("package", [sys.executable, "-I", "-c", INSPECT]),
            ("tests", [sys.executable, "-I", "-m", "unittest", "discover", "-s", str(ROOT / "tests")]),
            ("offline_smoke", [sys.executable, "-I", "-c", SMOKE]),
            ("console_entrypoint", [str(Path(sys.executable).with_name("mist")),
                "--audit-path", "console-audit.jsonl", "--message", "teste sintetico do comando instalado"]),
        ]
        evidence = {"verified_at": datetime.now(timezone.utc).isoformat(), "checks": {},
                    "source_revision": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
                    "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                        for folder in (ROOT / "src", ROOT / "tests") for path in sorted(folder.rglob("*.py"))}}
        for label, command in commands:
            result = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=120)
            evidence["checks"][label] = {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
        package = evidence["checks"]["package"]
        info = json.loads(package["stdout"]) if package["returncode"] == 0 else {}
        evidence["package"] = info
        audit = Path(directory) / "audit.jsonl"
        records = [json.loads(line) for line in audit.read_text().splitlines()] if audit.exists() else []
        evidence["audit_phases"] = [record["phase"] for record in records]
        evidence["passed"] = (
            all(check["returncode"] == 0 for check in evidence["checks"].values())
            and "site-packages" in Path(info.get("module_path", "")).parts
            and info.get("offline_default") is True and info.get("tools_enabled") is False
            and info.get("autonomy_level") == 0
            and evidence["audit_phases"] == ["approved", "completed"]
            and "Simulação" in evidence["checks"]["offline_smoke"]["stdout"]
            and "Simulação" in evidence["checks"]["console_entrypoint"]["stdout"]
        )
        return evidence


def main():
    parser = argparse.ArgumentParser(description="Verificar distribuição instalada da Mist em ambiente isolado")
    parser.add_argument("--output", type=Path, required=True, help="Arquivo novo de evidências JSON")
    args = parser.parse_args()
    evidence = verify()
    # Preserve previous evidence instead of silently overwriting it.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"python": evidence["package"].get("python"), "passed": evidence["passed"]}))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
