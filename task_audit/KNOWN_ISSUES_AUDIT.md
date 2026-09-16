# Known-issue audit — 2026-09-15

## Sources searched

- SkillsBench GitHub release v1.1 and task registry, queried for each fixed task
  plus `verifier`, `oracle`, `leak`, `broken`, and `reproduce`.
- BenchFlow issue tracker with the same queries.

## Result requiring resolution

BenchFlow issue [#192](https://github.com/benchflow-ai/benchflow/issues/192),
opened 2026-04-24 and shown as closed/not planned when checked, reports that
`fix-build-google-auto`'s verifier invokes `uv` even though the sandbox did
not install it.  The issue describes this as a false-fail source.  Because this
can affect verifier correctness, Task 2 remains **ineligible unless the exact
fixed v1.1 checkout passes its two-oracle and verifier-repeatability audit in
fresh local Docker sandboxes**. The verifier must not be patched for this MVP.

The same issue also reports an `claude-agent-acp` launch/PATH failure for
`fix-build-agentops` in a Daytona-specific configuration. This does not by
itself establish a Docker/verifier defect in the fixed task, but it is a
material harness-risk note. The required local Docker audit and the common
provider-agnostic harness are therefore mandatory.

The v1.1 release page confirms the pinned revision is `b63b7b2` and describes
the native `task.md` package format and BenchFlow 0.6.x line. This audit is not
a substitute for a checkout-specific test.
