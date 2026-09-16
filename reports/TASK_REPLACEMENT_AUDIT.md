# Task Replacement Audit

Date: 2026-09-16  
Benchmark source: SkillsBench v1.1, commit `b63b7b2850226b6aa4fb5929a8c1ac7bc4d9a6af`  
Runner: BenchFlow `0.6.7`, WSL + local Docker

## Retired originals

| Task | Decision | Basis |
|---|---|---|
| `fix-build-agentops` | `TASK_QUALIFICATION_FAILED_SEMANTIC_EXTERNAL_DEPENDENCY` | The unmodified oracle requires the unreachable BugSwarm REST API to retrieve its golden patch. Modal registration was declined. |
| `fix-build-google-auto` | `TASK_QUALIFICATION_FAILED_SEMANTIC_EXTERNAL_DEPENDENCY` | Same mandatory BugSwarm REST API dependency and failure mode. |

## Candidate screening

| Candidate | Structural/package check | External-dependency audit | Local oracle evidence | Status |
|---|---|---|---|---|
| `adaptive-cruise-control` | Pass; task package and five local skills present. | `BOOTSTRAP_DEPENDENCY`: verifier installs fixed Python test packages; no semantic remote input, truth, or oracle dependency. | Three fresh Docker oracle runs each returned `reward=1.0` and 12/12 verifier tests passed; each ran `no-skill` with no injected skill directory. | **QUALIFIED TASK 1**; held pending paired-skill screen. |
| `drone-planning-control` | Pass; task package and six local skills present. | `BOOTSTRAP_DEPENDENCY`: `verifier/test.sh` installs fixed-version `uv` through the Astral installer; no semantic remote truth path was identified. | Not run after the two-task stop condition. | Not selected |
| `exoplanet-detection-period` | Task package present. | `BOOTSTRAP_DEPENDENCY`: verifier has the same fixed-version Astral `uv` bootstrap; no semantic remote truth path was identified. | Not run after the two-task stop condition. | Not selected |
| `grid-dispatch-operator` | Pass; local skills `dc-power-flow`, `economic-dispatch`, and `power-flow-data` present. | `BOOTSTRAP_DEPENDENCY`: verifier installs unpinned `pytest` and `pytest-json-ctrf` from PyPI; no semantic remote truth path was found. | Fresh run 1 returned `reward=1.0` (6/6 tests); fresh run 2 returned `reward=0.0` when PyPI TLS fetch of `pytest` failed. | `TASK_BOOTSTRAP_UNSTABLE`; `HERMETIC_FALLBACK_POOL` |
| `hvac-control` | Pass; task package and five local skills present. | `BOOTSTRAP_DEPENDENCY`: verifier installs pinned `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`, and `numpy==1.26.4`; oracle, inputs, and truth are local. | Three fresh Docker oracle runs each returned `reward=1.0` and 7/7 verifier tests passed; each ran `no-skill` with no injected skill directory. | **QUALIFIED TASK 2**; held pending paired-skill screen. |

## Evidence and scope

- `adaptive-cruise-control` result files: `runs/oracle-067-adaptive-cruise-control-{1,2,3}/.../result.json`; all have `reward: 1.0`, `skill_mode: no-skill`, and `include_task_skills: false`. The verifier output in each run reports 12/12 tests passed.
- The Docker runs use BenchFlow-created temporary containers. BenchFlow removes each task container and image at the end of a run; no Docker daemon, proxy, TUN, WSL, or system networking setting was changed.
- Pinned package installation is recorded as an environment reproducibility constraint; it is not treated as an external oracle/service dependency. Arbitrary runtime bootstrap downloads and remote data/API calls are disqualifying.
- `grid-dispatch-operator` is in the hermetic fallback pool because its unpinned verifier package fetch made the oracle reward non-repeatable. It is not a semantic external-dependency failure. No retry, proxy change, or task modification was used to conceal that failure.
- No model API call or formal experiment run has occurred.

## Current decision

The static sweep was completed before selecting `hvac-control`. Both
`adaptive-cruise-control` and `hvac-control` satisfy the required three fresh
oracle rewards, stable verifiers, no semantic external dependency, and
no-skill isolation. Candidate search stops here. No paid model/API or formal
screening run has started.
