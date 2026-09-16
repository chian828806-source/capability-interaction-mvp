# Task Candidate Sweep

Date: 2026-09-16  
Source: SkillsBench v1.1 commit `b63b7b2850226b6aa4fb5929a8c1ac7bc4d9a6af`  
Method: read-only static scan of all 87 `tasks/*` packages by
`scripts/scan_task_candidates.py`.

## Classification rule

- `SEMANTIC_EXTERNAL_DEPENDENCY`: a remote oracle/ground-truth/input or
  verifier-truth dependency. Excluded.
- `BOOTSTRAP_DEPENDENCY`: package/test-runner installation only. It remains
  eligible for fresh-oracle repeatability testing.
- `SELF_CONTAINED`: neither of the above.

The score is a deterministic pre-oracle ordering: medium difficulty, skill
count, dependency class, local/no-network metadata, and clear modularity. It
does not use observed skill uplift, model outcomes, or expected interaction.

## Top 10 static candidates

| Rank | Task | Why in the static top tier | Skills | Dependency class | Oracle status | Decision |
|---:|---|---|---|---|---|---|
| 1 | `adaptive-cruise-control` | Medium; 5 skills; local simulator workflow. | csv-processing; pid-controller; simulation-metrics; vehicle-dynamics; yaml-config | BOOTSTRAP_DEPENDENCY, pinned | 3× `1.0`, verifier 12/12 each | QUALIFIED TASK 1 |
| 2 | `drone-planning-control` | Medium; 6 skills; modular controller/planning workflow. | attitude-controller-planner; flight-plan-parser; motor-model-dynamics; plot-quadrotor; position-controller-trajectory-planner; stepinfo-3d | BOOTSTRAP_DEPENDENCY, pinned | Not run after two tasks qualified | Not selected |
| 3 | `exoplanet-detection-period` | Medium; 5 skills; local analysis-oriented workflow. | box-least-squares; exoplanet-workflows; light-curve-preprocessing; lomb-scargle-periodogram; transit-least-squares | BOOTSTRAP_DEPENDENCY, pinned | Not run after two tasks qualified | Not selected |
| 4 | `hvac-control` | Medium; 5 skills; local thermal simulator with clear identification→tuning workflow. | excitation-signal-design; first-order-model-fitting; imc-tuning-rules; safety-interlocks; scipy-curve-fit | BOOTSTRAP_DEPENDENCY, pinned | 3× `1.0`, verifier 7/7 each | QUALIFIED TASK 2 |
| 5 | `organize-messy-files` | Medium; 5 file-processing skills. | docx; file-organizer; pdf; planning-with-files; pptx | BOOTSTRAP_DEPENDENCY, pinned | Not run after stop condition | Not selected |
| 6 | `python-scala-translation` | Medium; 6 language-translation modules. | python-scala-collections; python-scala-functional; python-scala-idioms; python-scala-libraries; python-scala-oop; python-scala-syntax-mapping | BOOTSTRAP_DEPENDENCY, pinned | Not run after stop condition | Not selected |
| 7 | `bike-rebalance` | Medium; 4 optimization/routing skills; no-network metadata. | geospatial-routing-data; logistics-rules-to-optimization; routing-subtour-elimination; scip-opt | BOOTSTRAP_DEPENDENCY, pinned | Not run after stop condition | Not selected |
| 8 | `gravitational-wave-detection` | Medium; self-contained static class. | conditioning; matched-filtering | SELF_CONTAINED | Not run after stop condition | Not selected |
| 9 | `lake-warming-attribution` | Medium; 4 analysis modules. | contribution-analysis; meteorology-driver-classification; pca-decomposition; trend-analysis | BOOTSTRAP_DEPENDENCY, pinned | Not run after stop condition | Not selected |
| 10 | `r2r-mpc-control` | Medium; 4 control-design modules. | finite-horizon-lqr; integral-action-design; mpc-horizon-tuning; state-space-linearization | BOOTSTRAP_DEPENDENCY, pinned | Not run after stop condition | Not selected |

The complete machine-readable inventory, including every requested detection
field and all skill names, is at `task_audit/task_candidate_inventory.csv`.

## Frozen task set and skill-pair recommendation

| Task | Suggested A | Suggested B | Rationale |
|---|---|---|---|
| `adaptive-cruise-control` | `vehicle-dynamics` | `pid-controller` | A supplies kinematic/safety dynamics; B supplies the feedback-control law. Their combination maps directly to safe adaptive cruise control. |
| `hvac-control` | `first-order-model-fitting` | `imc-tuning-rules` | A estimates the thermal model from calibration data; B converts that model into controller gains. The combined workflow has a genuine identify→tune dependency. |

For HVAC, A-only is a useful system-identification aid, B-only is a useful
rule-based tuning aid when parameters are already known, and A+B is the
end-to-end task workflow. This is a qualitative pair qualification only; no
model API or paid pilot has been run.

## Final state

`READY_FOR_SKILL_PAIR_FREEZE`

Candidate search stopped immediately after the second qualified task. The
hermetic fallback pool was not started. The frozen selection is recorded in
`preregistration_v2.yaml` with SHA-256 in `PREREGISTRATION_HASH_V2.txt`; the
original preregistration was not modified.
