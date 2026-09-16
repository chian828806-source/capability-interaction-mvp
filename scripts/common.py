"""Shared, dependency-free helpers for the MVP experiment."""
from __future__ import annotations

import csv, hashlib, json, os, platform, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def file_manifest(directory: Path) -> list[dict]:
    records = []
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        records.append({"path": path.relative_to(directory).as_posix(), "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                        "line_count": path.read_bytes().count(b"\n")})
    return records

def tree_hash(directory: Path) -> str:
    payload = json.dumps(file_manifest(directory), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()

def command(command: list[str], cwd: Path | None = None, timeout: int = 3600) -> dict:
    try:
        p = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
        return {"command": command, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "returncode": None, "stdout": "", "stderr": str(exc)}

def version(command_: list[str]) -> str | None:
    result = command(command_, timeout=30)
    return result["stdout"].strip() if result["returncode"] == 0 else None

def environment_manifest() -> dict:
    return {"timestamp": now(), "python": sys.version, "platform": platform.platform(),
            "cpu_count": os.cpu_count(), "bench_version": version(["bench", "--version"]),
            "docker_version": version(["docker", "--version"]), "docker_info": version(["docker", "info"])}

def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)

def atomic_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
