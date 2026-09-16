"""Write the frozen execution manifest from the active WSL environment."""
from __future__ import annotations
import platform, subprocess, sys
from pathlib import Path
from common import FINAL_PREREGISTRATION, ROOT, now, read_json, write_json

def output(*cmd: str) -> str | None:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, check=False)
        return p.stdout.strip() if p.returncode == 0 else None
    except OSError:
        return None

pre = read_json(FINAL_PREREGISTRATION)
write_json(ROOT / "environment_manifest.json", {
    "timestamp": now(), "execution_environment": "WSL", "python": sys.version,
    "platform": platform.platform(), "benchflow": output(str(Path(sys.executable).parent / "bench"), "--version"),
    "docker": output("docker", "--version"), "docker_info": output("docker", "info", "--format", "{{.ServerVersion}}"),
    "skillsbench_commit": output("git", "-C", str(ROOT / "external" / "skillsbench-lf"), "rev-parse", "HEAD"),
    "project_git_commit": output("git", "-C", str(ROOT), "rev-parse", "HEAD"),
    "final_preregistration": FINAL_PREREGISTRATION.name,
    "tasks": list(pre["tasks"]),
    "network_settings_modified": False
})
