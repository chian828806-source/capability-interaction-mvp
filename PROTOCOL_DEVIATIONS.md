# Protocol deviations

No deviations have been approved or executed.

## Preflight observation — 2026-09-15

The public release documentation for SkillsBench v1.1 states compatibility
with BenchFlow `>=0.6.3,<0.7`, whereas the supplied protocol uses the stricter
lower bound `>=0.6.4`.  This is recorded for reconciliation only; no BenchFlow
version has been installed and no model run has occurred.

## Approved preflight environment pin — 2026-09-16

The researcher selected BenchFlow `0.6.7` as the fixed preflight version.
This replaces the earlier range with an exact pin before any valid oracle or
model run. BenchFlow 0.6.4 parsed the task packages but failed to mount the
verifier in the local WSL/Docker audit; no task, skill, verifier, model, or
paid API configuration was modified. All subsequent audit runs must report
the exact 0.6.7 version.

## Preflight runner workaround — 2026-09-16

BenchFlow 0.6.7 on WSL failed to resolve the task when passed a relative path
from the Windows-mounted project directory. Subsequent oracle commands used
the same fixed task directory by its absolute WSL path and set
`BENCHFLOW_AGENTS_SOURCE=off` for the command only, avoiding an unrelated
automatic manifest-cache clone. Neither setting was persisted. The two fresh
oracle results remained verifier-invalid (rc=127) and no paid API call ran.

## LF-only benchmark checkout — 2026-09-16

Git for Windows was already configured system-wide with `core.autocrlf=true`.
That produced CRLF verifier scripts in the original workspace checkout.
BenchFlow 0.6.7 running under WSL only normalizes uploaded scripts when Python
reports Windows, so its direct execution reported `/verifier/test.sh: not
found` even though the file was present (the shebang interpreter was
`/bin/bash\\r`). A separate local clone, `external/skillsbench-lf`, was made
from the fixed checkout at the same `b63b7b2…` commit with a repository-local
`core.autocrlf=false`. The original checkout and all global Git, Docker,
Clash, TUN, proxy, and WSL settings remain unchanged. The LF run confirms the
verifier executes; its oracle is still infrastructure-invalid because the
external BugSwarm API is unreachable.

## Original task retirement — 2026-09-16

Before any paid screening or formal experiment, the researcher declined Modal
registration and directed that `fix-build-agentops` and
`fix-build-google-auto` be retired as
`TASK_QUALIFICATION_FAILED_SEMANTIC_EXTERNAL_DEPENDENCY`. Both original, unmodified
oracles require the BugSwarm REST API to retrieve a golden patch; local Docker,
Windows, WSL, and one-command local-proxy diagnostics all failed at that shared
external service. No task, oracle, verifier, or golden patch was modified.
Replacement is therefore a pre-experiment infrastructure-qualification action,
not an outcome-driven task change.

## Replacement-candidate exclusions — 2026-09-16

`drone-planning-control` and `exoplanet-detection-period` were not selected
after the static sweep: each verifier performs a runtime `curl | sh` download
of Astral's `uv` installer. They are bootstrap-dependent rather than semantic
external-dependency failures. `grid-dispatch-operator` had a failed fresh
repeat (run 1 reward 1.0; run 2 reward 0.0) because its unpinned verifier
dependency `pytest` could not be fetched from PyPI (TLS EOF). It is recorded
as `TASK_BOOTSTRAP_UNSTABLE` in `HERMETIC_FALLBACK_POOL`, preserving the raw
failure evidence. No network, proxy, TUN, Docker daemon, or task source
modification was attempted. The detailed replacement evidence is in
`reports/TASK_REPLACEMENT_AUDIT.md`.
