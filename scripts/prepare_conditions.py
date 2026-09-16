"""Create leakage-free task copies and immutable skill condition folders."""
from __future__ import annotations
import shutil
from pathlib import Path
from common import ROOT, copy_tree, file_manifest, read_json, tree_hash, write_json

def clean_task(source: Path, destination: Path) -> None:
    copy_tree(source, destination)
    skills = destination / "environment" / "skills"
    if skills.exists(): shutil.rmtree(skills)

def condition(task_id: str, source_task: Path, skills: list[str]) -> None:
    sanitized = ROOT / "sanitized_tasks" / task_id
    clean_task(source_task, sanitized)
    available = source_task / "environment" / "skills"
    cases = {"ZERO": [], "A": [skills[0]], "B": [skills[1]], "AB": skills}
    for label, selected in cases.items():
        dest = ROOT / "conditions" / task_id / label
        if dest.exists(): shutil.rmtree(dest)
        dest.mkdir(parents=True)
        for skill in selected:
            origin = available / skill
            if not origin.is_dir(): raise FileNotFoundError(f"Missing source skill: {origin}")
            shutil.copytree(origin, dest / skill)
        manifest = {"task_id": task_id, "condition": label, "selected_skills": selected,
                    "files": file_manifest(dest), "tree_sha256": tree_hash(dest),
                    "source_skill_root": str(available)}
        write_json(dest / "manifest.json", manifest)
    write_json(sanitized / "manifest.json", {"task_id": task_id, "tree_sha256": tree_hash(sanitized),
        "removed_path": "environment/skills", "source_task": str(source_task)})

def main() -> None:
    pre = read_json(ROOT / "preregistration.yaml"); source = ROOT / "external" / "skillsbench-lf" / "tasks"
    if not source.is_dir(): raise SystemExit("Pinned SkillsBench source is absent; clone it before preparing conditions.")
    for task_id, spec in pre["tasks"].items(): condition(task_id, source / task_id, spec["skills"])
    print("Sanitized task copies and condition manifests created.")

if __name__ == "__main__": main()
