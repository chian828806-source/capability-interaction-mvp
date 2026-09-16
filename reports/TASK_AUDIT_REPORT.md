# Task Audit Report — BugSwarm oracle API blocked

The protocol requires a fixed local checkout of SkillsBench `v1.1` at
`b63b7b2`, two successful fresh Docker oracle runs per task, verifier
repeatability, an initial-state failure check, skill-leakage isolation, and a
dated known-issue review. None of these conditions is inferred from a web page
or fabricated by this repository.

The fixed public source is now checked out at commit `b63b7b285…`. Both fixed
tasks pass the BenchFlow 0.6.7 structural check. The original checkout had
CRLF verifier scripts because the pre-existing Git for Windows system setting
is `core.autocrlf=true`; in WSL, BenchFlow skipped its Windows-only upload
normalization and direct execution failed at the CRLF shebang. A separate,
project-local LF checkout at the same commit fixes that environment-only
problem without changing the original source or global Git configuration.

Task 1 then executed its oracle and verifier normally, but the oracle's
required BugSwarm REST API call was disconnected before it could retrieve the
golden patch. A host reachability check likewise received HTTP 000 and an HTTPS
timeout from `www.bugswarm.org`; a one-command local-proxy check returned HTTP
502 and an HTTPS handshake failure. Docker Hub authentication subsequently
recovered (HTTP 200), and Task 2's LF retry successfully built and started its
container, then failed at the identical BugSwarm golden-patch request. These
are infrastructure-invalid runs, no model API was called, and neither
benchmark task has been modified.

The dated issue review is in `task_audit/KNOWN_ISSUES_AUDIT.md`.  In
particular, a public report describes a missing-`uv` verifier dependency for
`fix-build-google-auto`.  This confirms why Task 2 may not be repaired and
used without passing the exact fixed-checkout audit.

## Retirement decision

At the researcher's direction, both original BugSwarm tasks are classified
`TASK_QUALIFICATION_FAILED_EXTERNAL_DEPENDENCY`. Modal diagnosis was not run
because the researcher declined Modal registration. Candidate replacement
audits start with `adaptive-cruise-control` and `drone-planning-control`; no
formal LLM run may begin until two replacements qualify.
