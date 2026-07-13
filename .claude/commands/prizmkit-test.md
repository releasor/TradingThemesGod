---
description: Auditable test-evidence protocol for AI-generated behavior changes. Classifies changes, discovers affected modules and regression rings, models observable behavior and risk, builds project-native tests and contract-driven mocks, proves tests differentially, preserves content-addressed raw evidence, and deterministically returns TEST_PASS, TEST_FAIL, or TEST_BLOCKED. Use after code/config/schema/dependency changes or when users ask to test, verify, add complete module tests, inspect boundaries, or produce auditable evidence. Supports full-project, module, feature, and scope=this-change. (project)
---

# PrizmKit Test

`/prizmkit-test` converts code changes into auditable testing evidence. Completeness means that the affected module's observable behavior, contracts, boundaries, invariants, errors, state transitions, and coupling risks are represented and proven. It does not mean mechanically reaching a line-coverage threshold.

This skill orchestrates each target project's native runners and conventions. It does not install a cross-language test runtime.

## Model Choice vs Fixed Evidence Mechanics

Choose project-semantic parameters from the target project: framework, commands, cwd, timeout, retry/attempt policy, concurrency, Mock tools, test layers, module boundary, inventory patterns, mutation technology, and environment classification. Do not hard-code ecosystem-specific defaults when the project can decide them.

Fix only the protocol mechanisms needed for safe, replayable evidence: project/evidence/request locators, schema-shaped requests, path confinement, real process execution, complete raw capture, runner-generated chained receipts, hash binding, append-only history, differential isolation/cleanup, and resume invalidation. Read `.claude/command-assets/prizmkit-test/references/trusted-evidence-execution.md` before inventory, execution, differential proof, resume, or replay; it defines the trust boundary and builder commands. Read `.claude/command-assets/prizmkit-test/references/evidence-request-protocol.md` when authoring any request or authoritative JSON record; it defines request ownership, structured N/A, and the schema map.

## When to Use

Use for:

- behavior-changing source code;
- runtime configuration, schema, migration, generated-runtime, lockfile, or dependency changes;
- public interfaces and data contracts;
- frontend, backend, library, CLI, adapter, and multi-module changes;
- legacy modules whose observable test coverage is incomplete;
- explicit test, boundary, evidence, confidence, or audit requests.

Documentation, comment, and formatting-only scopes use deterministic lightweight verification. They do not receive an unjustified full behavior-test claim.

## Preconditions and Safety

1. Load `root.prizm`, relevant L1/L2 docs, project manifests, runner configuration, and changed scope once.
2. Never use production credentials, production databases, production APIs, production queues/storage, or destructive operations against real data.
3. Preserve complete command/environment/output values as requested. Mark the package `sensitivity=project-controlled`; the project owns access control, retention, and upload policy.
4. Treat code-level dependencies as mock-first. Real deployed test-environment validation is a separate authorized activity.
5. Never delete existing tests.

If test infrastructure is missing, the infrastructure preparation state establishes only the necessary project-native infrastructure autonomously. Do not ask the user to install routine test dependencies in a headless run; verify dependency versions before editing manifests.

## Input

| Parameter | Required | Description |
|-----------|----------|-------------|
| `scope` | No | `full-project`, `module:<name>`, `feature:<slug>`, or `this-change`. Defaults to `this-change` with a valid artifact directory, otherwise `full-project`. |
| `artifact_dir` | No | Change artifact containing `spec.md` + `plan.md`; used to resolve acceptance conditions and changed scope. |
| `changed_files` | No | Explicit changed files; highest-priority scope input. |
| `diff_base` | No | Git baseline used when `changed_files` is absent. |
| `evidence_target` | No | Existing evidence ID/directory to validate and resume. |
| `execution_budget` | No | Bounded time/attempt budget. Incomplete necessary work is `TEST_BLOCKED`, never truncated to pass. |
| `test_commands` | No | Explicit project-native commands when discovery is ambiguous. |

For `scope=this-change`, determine changed files from `changed_files`, `diff_base`, current diff, artifact plan/context manifest, then spec mapping. Unknown scope is `TEST_BLOCKED`.

Do not infer a current change artifact from a legacy bug/refactor directory name alone; require explicit `artifact_dir` and changed-file evidence.

## Authoritative Resources

Load each resource only on its branch:

- Read `.claude/command-assets/prizmkit-test/references/evidence-protocol.md` before a behavior evidence run or validation/resume decision — it defines state contracts, identity, proof, and verdict semantics.
- Load `.claude/command-assets/prizmkit-test/assets/evidence-manifest.schema.json` when creating or validating `manifest.json`.
- Load `.claude/command-assets/prizmkit-test/assets/behavior-risk-matrix.schema.json` during `CONTRACT_MODEL` or matrix validation.
- Load `.claude/command-assets/prizmkit-test/assets/authoritative-records.schema.json` when creating or validating any other authoritative request/record.
- Load `.claude/command-assets/prizmkit-test/assets/evidence-package-template.json` when initializing or resuming an evidence directory.
- Read `.claude/command-assets/prizmkit-test/references/contract-mock-protocol.md` only when dependency, contract, or external-boundary risks require doubles.
- Read `.claude/command-assets/prizmkit-test/references/test-generation-steps.md` during `INFRA_READY`, `TEST_BUILD`, or `EXECUTE_PROVE`.
- Read `.claude/command-assets/prizmkit-test/references/service-boundary-test-catalog.md` only when domain boundary signals need risk discovery.
- Read `.claude/command-assets/prizmkit-test/references/boundary-coverage-protocol.md` when defining module roots, exclusions, Regression Ring, or behavior-risk completeness.

## Required State Machine

Execute in this exact order: CHANGE_CLASSIFY, SCOPE_DISCOVER, CONTRACT_MODEL, TEST_PLAN, INFRA_READY, TEST_BUILD, EXECUTE_PROVE, EVIDENCE_PACKAGE, EVIDENCE_VALIDATE. Do not claim a later state complete without valid applicable predecessor outputs.

### 1. CHANGE_CLASSIFY

Classify the scope as `behavior` or `lightweight` and write `change-classification.json`.

- `behavior`: code, runtime config, schema, migration, generated runtime, dependency, or mixed/uncertain scope; full protocol required.
- `lightweight`: exclusively docs/comments/formatting with deterministic evidence that runtime behavior cannot change.

Unknown classification follows the full protocol or becomes `TEST_BLOCKED`.

### 2. SCOPE_DISCOVER

Write `scope.json`, `target-inventory.json`, and `source-change.patch`. Use a model-authored inventory request with the bundled builder so actual discovered files are hashed. Record:

- changed files, all declared module roots, and evidence-backed exclusions;
- affected module boundary (`explicit` or `cohesion-derived`);
- Primary Scope containing all observable behavior of that module;
- Regression Ring containing direct callers, consumers, shared contracts, and state dependencies, each mapped to planned tests;
- contract, lockfile, test, and module-boundary discovery evidence;
- Unresolved Edges for dynamic/unprovable coupling.

Require every changed file to appear in inventory or a structured exclusion. Inventory and static discovery constrain obvious omissions but cannot deterministically prove semantic completeness; preserve that residual model judgment. Any verdict-capable unresolved edge blocks `TEST_PASS`.

### 3. CONTRACT_MODEL

Write `behavior-risk-matrix.json`. Resolve test truth in strict precedence:

1. specifications;
2. machine-readable contracts;
3. acceptance conditions;
4. trusted existing tests;
5. callers/consumers;
6. current implementation.

Unresolved conflicting truth is `TEST_BLOCKED`, not a characterization test.

For every observable behavior, record contract source, preconditions, input classes/boundaries, outputs, side effects, transitions, errors, and functional/boundary/permission/concurrency/idempotency/time/dependency/consumer risks. Every applicable cell maps to tests and executions or remains explicitly unresolved.

Coverage metrics are diagnostic signals only and never substitute for this matrix.

### 4. TEST_PLAN

Write `test-plan.json`. Select necessary unit, module/component, contract, integration, and code-level E2E tests by risk. Assess the ordered execution layers:

1. focused;
2. module/component;
3. contract/integration;
4. complete affected-module regression;
5. Regression Ring.

Every omitted layer uses a structured N/A decision containing rationale, typed evidence, considered signals, and explicit explanations for detected conflicts. The model owns semantic judgment; deterministic validation checks shape and obvious conflicts.

### 5. INFRA_READY

Discover and reuse native runners and conventions. Install only required dependencies, configure commands, and create fixtures/fakes/contract mock servers/isolated services as needed. Avoid duplicate frameworks and record every infrastructure change and verification in `infrastructure-changes.json`.

External dependencies use `.claude/command-assets/prizmkit-test/references/contract-mock-protocol.md`. Shared machine-readable contracts are preferred; locally derived contract fixtures must record their source. Independently invented incompatible mocks are rejected.

### 6. TEST_BUILD

Fill gaps across the whole affected module's observable behavior, contracts, boundaries, invariants, failure paths, transitions, and coupling risks. Do not test only the changed happy path or unrelated private implementation lines.

Minimal behavior-preserving production refactoring is allowed only for test seams such as dependency injection, pure-function extraction, adapters, or controllable state. If testing requires changing a public production contract, issue `TEST_BLOCKED`.

If a valid test reveals a business/contract defect, do not fix production behavior in this skill. Preserve the evidence for `TEST_FAIL`.

### 7. EXECUTE_PROVE

Run required layers in plan order through `.claude/command-assets/prizmkit-test/scripts/build_test_evidence.py execute`. The model selects project-native argv, cwd, timeout, attempts, concurrency, layer, environment classification, and tool probes in schema-shaped requests. The runner performs the actual process execution and appends complete environment/tool versions, raw stdout/stderr hashes, request hash, runner hash, unique receipt, and receipt-chain binding to `executions.json`. Do not accept caller-authored execution JSON and do not retry until green.

Differentially prove each added/changed necessary behavior test:

- Prefer baseline failure plus current success in an isolated/uncontaminated environment.
- If baseline is inapplicable, use a minimal controlled mutation tied to the same risk.
- Bind proof to runner receipts, baseline commit, a stable source-snapshot hash, mutation apply/restore hashes, and complete cleanup. The source snapshot excludes runtime-managed `.prizmkit/state/`, evidence output under `.prizmkit/test/evidence/`, `.claude/worktrees/`, Git metadata, and Python bytecode caches because those paths change while the tested code remains identical.
- Keep source identity separate from evidence integrity: the stable snapshot detects behavior-bearing project drift, while `manifest.json` hashes every evidence file and detects report/output tampering.
- Completely remove mutations and verify the stable source snapshot is unchanged. Never rebind completed proof to the mutable live project tree.
- Classify each proof as `PROVEN`, structured `NOT_APPLICABLE`, or `UNPROVEN`.

Necessary `UNPROVEN` behavior, required flakiness, unavailable infrastructure after bounded recovery, failed cleanup, unreliable execution, or budget truncation yields `TEST_BLOCKED`.

### 8. EVIDENCE_PACKAGE

Create `.prizmkit/test/evidence/<evidence-id>/` from the package template with:

- `manifest.json`
- `change-classification.json`
- `scope.json`
- `behavior-risk-matrix.json`
- `test-plan.json`
- `infrastructure-changes.json`
- `differential-proof.json`
- `executions.json`
- `verdict.json`
- `source-change.patch`
- complete `raw/` stdout/stderr
- `generated-tests/` snapshots
- `contracts/` snapshots
- derived `test-report.md`

Hash baseline, diff, the stable source snapshot, inventoried source/tests/contracts/lockfiles, environment, plan, and every evidence file. Runtime state, evidence output, linked Agent worktrees, Git metadata, and bytecode caches are outside source identity; evidence files remain independently content-addressed through `manifest.json`. Set `environment_claim=mocked-code-level-only` and `compatibility=legacy-test-report-interface-not-supported`.

### 9. EVIDENCE_VALIDATE

Run:

```bash
python3 .claude/command-assets/prizmkit-test/scripts/validate_test_evidence.py \
  --evidence-dir .prizmkit/test/evidence/<evidence-id> \
  --project-root <target-project-root> \
  --attest
```

The validator checks every authoritative record against its shipped schema, live target inventories, patch/diff binding, stage dependencies, changed-file/module-root/exclusion/Regression Ring cross-links, generated-test snapshots, planned-test execution links, runner-generated receipts/request/raw-output hashes, successful behavior-risk mappings, proof-linked isolated failures/current successes, production/unknown external-target safety, cleanup, and package integrity. `--attest` writes an integrity/protocol attestation, not proof against a malicious same-permission producer. Use builder replay when feasible to rerun recorded requests and create new linked receipts. Store validation output. Tampering, schema/identity/hash mismatch, source/test/lockfile drift, missing matrix mappings, wrong execution order, invalid differential proof, cleanup failure, unjustified structured N/A, unresolved risk, or a false real-environment claim fails validation. `TEST_PASS` requires validator success and means code-level evidence is replayable and validated under this protocol.

## Resume and Idempotency

When interrupted or re-invoked:

1. validate existing manifest, hashes, and stage outputs;
2. recompute code/test/contract/dependency/environment/plan input hashes;
3. preserve prior executions and raw output immutably;
4. invalidate the first changed stage and every downstream result;
5. resume from the last valid predecessor.

For a large module or bounded budget, persist matrix/checkpoint progress and return `TEST_BLOCKED` until complete evidence exists. Never silently reduce scope.

## Terminal Verdicts

Only these testing-domain outcomes are valid:

- `TEST_PASS`: every required module behavior/risk and Regression Ring check is proven, required executions pass reliably, cleanup succeeds, no verdict-capable unresolved edge remains, and deterministic validation passes.
- `TEST_FAIL`: a valid reliable test reproduces an implementation or resolved-contract failure.
- `TEST_BLOCKED`: unknown scope, conflicting truth, unavailable/unreliable/flaky necessary execution, incomplete evidence, unproven tests, failed cleanup, budget truncation, or deterministic validation failure.

No conditional pass exists.

## Derived Report and Handoff

Generate `test-report.md` from structured evidence using `.claude/command-assets/prizmkit-test/references/test-report-template.md`. It is a replaceable view, not the source of truth. Report only:

- testing-domain verdict;
- evidence directory and ID;
- validator result and key execution pointers;
- sensitivity and mocked-versus-real warning;
- explicit notice that the legacy test-report interface is not supported.

Do not embed an independent AI reviewer, decide overall code quality, claim broad Spec compliance, repair a validly detected business defect, authorize commit/release, or perform deployed test/production validation.

Existing Pipeline and Skill consumers are not migrated by this protocol. Temporary post-install incompatibility with callers expecting the legacy report is accepted and must be stated, not hidden.

## Examples

Read `.claude/command-assets/prizmkit-test/references/examples.md` only when a concrete normal, legacy gap-filling, contract-coupled, failure, blocked, recovery, or tampering example is needed.

**HANDOFF:** Return the strict testing verdict and structured evidence pointers only.
