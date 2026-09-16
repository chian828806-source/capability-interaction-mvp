"""Static, read-only candidate inventory for the fixed SkillsBench checkout.

This script intentionally never writes below the benchmark source.  It only
classifies text found in task metadata, skills, oracle, verifier and Dockerfile.
Remote bootstrap tooling is kept distinct from remote task semantics.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "external" / "skillsbench-lf"
OUT = ROOT / "task_audit" / "task_candidate_inventory.csv"

REMOTE_RE = re.compile(r"https?://[^\s'\"`|)]+", re.I)
PATTERNS = {
    "curl": re.compile(r"\bcurl\b", re.I),
    "wget": re.compile(r"\bwget\b", re.I),
    "http": re.compile(r"https?://", re.I),
    "requests": re.compile(r"\brequests\s*\.", re.I),
    "urllib": re.compile(r"\burllib\b", re.I),
    "git_clone": re.compile(r"\bgit\s+clone\b", re.I),
    "pip_install": re.compile(r"\bpip(?:3)?\s+install\b", re.I),
    "uv": re.compile(r"\buv(?:x)?\b", re.I),
    "apt": re.compile(r"\bapt(?:-get)?\b", re.I),
    "conda": re.compile(r"\bconda\b", re.I),
    "npm_install": re.compile(r"\bnpm\s+install\b|\bnpx\b", re.I),
}
BOOTSTRAP_HOSTS = {"pypi.org", "files.pythonhosted.org", "astral.sh", "github.com", "raw.githubusercontent.com", "deb.debian.org", "archive.ubuntu.com"}


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def files_under(task: Path, relative: str, suffixes: tuple[str, ...] = ()) -> list[Path]:
    base = task / relative
    if not base.exists():
        return []
    if base.is_file():
        return [base]
    return sorted(p for p in base.rglob("*") if p.is_file() and (not suffixes or p.suffix in suffixes))


def hosts(text: str) -> list[str]:
    result = []
    for url in REMOTE_RE.findall(text):
        host = urlparse(url).netloc.lower()
        if host and host not in result:
            result.append(host)
    return result


def has(text: str, name: str) -> bool:
    return bool(PATTERNS[name].search(text))


def packages_and_pins(text: str) -> tuple[str, bool]:
    lines = [line.strip() for line in text.splitlines() if PATTERNS["pip_install"].search(line)]
    packages = []
    pinned = bool(lines)
    for line in lines:
        cleaned = re.sub(r"\s+-[^\s]+(?:\s+[^\s]+)?", " ", line)
        tokens = cleaned.split()
        try:
            start = next(i for i, value in enumerate(tokens) if value in {"install", "install\r"}) + 1
        except StopIteration:
            continue
        for token in tokens[start:]:
            if token.startswith(("$", "#", "\\")) or token in {"&&", "|"}:
                continue
            packages.append(token)
            if "==" not in token:
                pinned = False
    return ";".join(dict.fromkeys(packages)), pinned


def metadata(task_md: str, key: str) -> str:
    match = re.search(rf"^\s*{re.escape(key)}:\s*([^\n#]+)", task_md, re.M)
    return match.group(1).strip(" '\"") if match else ""


def classify(task: Path) -> dict[str, str]:
    task_md = read(task / "task.md")
    docker = read(task / "environment" / "Dockerfile")
    oracle = "\n".join(read(p) for p in files_under(task, "oracle"))
    verifier = "\n".join(read(p) for p in files_under(task, "verifier"))
    skills = sorted(p.name for p in (task / "environment" / "skills").iterdir()) if (task / "environment" / "skills").is_dir() else []
    oracle_hosts, verifier_hosts = hosts(oracle), hosts(verifier)
    oracle_remote = any(has(oracle, name) for name in ("curl", "wget", "http", "requests", "urllib", "git_clone"))
    verifier_remote = any(has(verifier, name) for name in ("curl", "wget", "http", "requests", "urllib", "git_clone"))
    verifier_bootstrap = any(has(verifier, name) for name in ("pip_install", "uv", "apt", "conda", "npm_install"))
    oracle_bootstrap = any(has(oracle, name) for name in ("pip_install", "uv", "apt", "conda", "npm_install"))
    packages, pinned = packages_and_pins("\n".join((oracle, verifier, docker)))

    # Any remote action by the oracle is conservatively semantic: it can affect
    # the produced answer.  Verifier remote hosts are bootstrap only when they
    # are recognizable package/tool sources and the verifier has no HTTP client
    # code beyond installer commands.
    semantic = oracle_remote
    if verifier_remote:
        unknown_hosts = [host for host in verifier_hosts if host not in BOOTSTRAP_HOSTS]
        verifier_code_remote = has(verifier, "requests") or has(verifier, "urllib")
        semantic = semantic or bool(unknown_hosts) or verifier_code_remote
    bootstrap = (verifier_bootstrap or oracle_bootstrap or (verifier_remote and not semantic))
    self_contained = not semantic and not bootstrap

    difficulty = metadata(task_md, "difficulty")
    category = metadata(task_md, "category")
    network_mode = metadata(task_md, "network_mode")
    score = 0
    score += 40 if difficulty == "medium" else 20 if difficulty else 0
    score += min(len(skills), 5) * 6
    # Semantic dependencies are excluded irrespective of any bootstrap tooling
    # also present in the same task.
    score += -100 if semantic else 35 if self_contained else 18 if bootstrap and pinned else 8 if bootstrap else 0
    score += 10 if network_mode in {"", "none", "disabled"} else 0
    score += 5 if len(skills) >= 3 else 0
    reason = ""
    if semantic:
        reason = "semantic remote access in oracle or verifier truth path"
    elif bootstrap:
        reason = "bootstrap dependency" + (" (packages pinned)" if pinned else " (one or more packages unpinned)")
    else:
        reason = ""
    return {
        "task_id": task.name, "difficulty": difficulty, "category": category,
        "network_mode": network_mode, "skill_count": str(len(skills)), "skill_names": ";".join(skills),
        "oracle_has_curl": str(has(oracle, "curl")).lower(), "oracle_has_wget": str(has(oracle, "wget")).lower(),
        "oracle_has_http": str(has(oracle, "http")).lower(), "oracle_has_requests": str(has(oracle, "requests")).lower(),
        "oracle_has_git_clone": str(has(oracle, "git_clone")).lower(), "oracle_remote_hosts": ";".join(oracle_hosts),
        "verifier_has_curl": str(has(verifier, "curl")).lower(), "verifier_has_wget": str(has(verifier, "wget")).lower(),
        "verifier_has_http": str(has(verifier, "http")).lower(), "verifier_has_pip_install": str(has(verifier, "pip_install")).lower(),
        "verifier_has_uv": str(has(verifier, "uv")).lower(), "verifier_has_apt": str(has(verifier, "apt")).lower(),
        "verifier_remote_hosts": ";".join(verifier_hosts), "bootstrap_packages": packages,
        "bootstrap_versions_pinned": str(pinned).lower(), "semantic_external_dependency": str(semantic).lower(),
        "bootstrap_dependency": str(bootstrap).lower(), "self_contained": str(self_contained).lower(),
        "candidate_score": str(score), "rejection_reason": reason,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    rows = [classify(task) for task in sorted((args.source / "tasks").iterdir()) if task.is_dir()]
    rows.sort(key=lambda row: (-int(row["candidate_score"]), row["task_id"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print(f"Wrote {len(rows)} static task records to {OUT}")


if __name__ == "__main__":
    main()
