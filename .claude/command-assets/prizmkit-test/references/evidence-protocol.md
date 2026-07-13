# Test Evidence Protocol

This reference is normative for behavior-changing `/prizmkit-test` runs. Structured JSON is authoritative; `test-report.md` is a derived view.

## Evidence Target and Identity

Write packages under `.prizmkit/test/evidence/<evidence-id>/`. Compute `evidence-id` as lowercase SHA-256 of canonical, key-sorted, compact JSON containing exactly:

- `baseline_commit`
- `working_diff_sha256`
- `scope_sha256`

Store those values as `evidence_id_inputs` in `manifest.json`. Record separate aggregate hashes for inventoried source, tests, contracts, lockfiles, full environment values, and plan inputs. Hash every evidence file except `manifest.json` in the manifest; do not create a self-referential manifest hash.

Use two separate integrity domains:

- **Stable source snapshot:** hash behavior-bearing project files while excluding runtime-managed `.prizmkit/state/`, evidence output under `.prizmkit/test/evidence/`, linked `.claude/worktrees/`, Git metadata, and Python bytecode caches. Builder and validator use the same deterministic exclusion policy, and isolated current execution is copied from that same snapshot scope.
- **Evidence package:** hash each evidence record through `manifest.json`; any report, receipt, raw output, request, or proof mutation remains detectable even though evidence output is outside source identity.

Runtime-only churn must not invalidate a source proof. Drift in an inventoried source, test, contract, or lockfile must still fail live inventory validation. Never replace a completed proof's stable snapshot identity with a later hash of the mutable parent workspace.

Hashes and validator receipts provide byte-level binding and drift detection, not cryptographic non-repudiation. A caller with the same OS permissions can replace the runner, requests, project tree, or package before validation. Preserve runner/request hashes and use replay to improve auditability without claiming resistance to a malicious same-privilege producer.

`source-change.patch` preserves the complete target diff. Snapshot generated/changed tests under `generated-tests/`, contracts under `contracts/`, and raw stdout/stderr under `raw/`. Never replace old execution/output records.

## Ordered State Machine

Run exactly these states in order:

1. `CHANGE_CLASSIFY`
2. `SCOPE_DISCOVER`
3. `CONTRACT_MODEL`
4. `TEST_PLAN`
5. `INFRA_READY`
6. `TEST_BUILD`
7. `EXECUTE_PROVE`
8. `EVIDENCE_PACKAGE`
9. `EVIDENCE_VALIDATE`

Each manifest stage records `name`, `status`, `input_sha256`, and output paths. A stage may be `not_applicable` only with a concrete rationale. A later state cannot complete until every applicable predecessor output exists, validates, and matches its recorded input hash.

### CHANGE_CLASSIFY

Classify `behavior` when executable behavior can change through code, runtime configuration, schemas, migrations, generated runtime assets, lockfiles, or dependency changes. Classify `lightweight` only when the scope is exclusively documentation, comments, or formatting with no generated/runtime behavior effect.

For lightweight changes, record deterministic checks such as patch classification, parser/format validation, and generated-output consistency. Mark behavior-only stages not applicable with rationale. `TEST_PASS` then means only that the lightweight claim was proven; never describe it as complete runtime behavior evidence.

Unknown or mixed classification enters the full protocol; unresolved classification becomes `TEST_BLOCKED`.

### SCOPE_DISCOVER

Record:

- Affected module: explicit module boundary or cohesion-derived files that jointly express one observable responsibility.
- Primary Scope: every public behavior of the affected module, not only changed lines.
- Regression Ring: directly affected callers, consumers, shared contracts, and state dependencies.
- Unresolved Edges: dynamic loading, reflection, generated clients, runtime registration, remote contracts, or coupling that cannot be proven statically.

Record changed files, declared module roots, contract/lockfile/test discovery, evidence-backed exclusions, and Regression Ring mappings in both scope and inventory records. Every changed file must be inventoried or explicitly excluded. The deterministic validator checks these declared relationships and obvious omissions, but inventory cannot prove that the model discovered every semantic behavior or dynamic edge.

Every edge records whether it can change the verdict. A verdict-capable unresolved edge prevents `TEST_PASS`.

### CONTRACT_MODEL

Resolve expected truth in this order:

1. specifications;
2. machine-readable contracts;
3. acceptance conditions;
4. existing trusted tests;
5. callers/consumers;
6. current implementation.

Record conflicts rather than silently characterizing current behavior. If higher-precedence sources conflict and cannot be resolved, issue `TEST_BLOCKED`.

Populate `behavior-risk-matrix.json` using `assets/behavior-risk-matrix.schema.json`. Enumerate observable behavior, preconditions, input classes and boundary values, outputs, side effects, state transitions, errors, and every functional, boundary, permission, concurrency, idempotency, time, dependency, and consumer risk. Every risk is applicable, not applicable with concrete rationale, or unresolved.

Coverage percentages are diagnostic omission signals. They can prompt another matrix review but cannot prove or replace behavior-risk completeness.

### TEST_PLAN

Assess all test layers:

1. `focused`
2. `module-component`
3. `contract-integration`
4. `affected-module-regression`
5. `regression-ring`

Choose unit, module/component, contract, integration, and code-level E2E tests from actual risk. Do not require every test type mechanically. Every omitted layer needs a concrete not-applicable rationale. If a necessary layer cannot be executed within the configured budget, persist progress and issue `TEST_BLOCKED` until complete.

### INFRA_READY

Discover manifests, existing tests, commands, runner configuration, fixtures, and conventions before changing infrastructure. Reuse an adequate native runner. Install only necessary dependencies after registry/version verification. Create only required configuration, fixtures, fakes, contract-backed mock servers, or isolated services. Never delete existing tests.

Record every infrastructure change, command, verification, and cleanup responsibility in `infrastructure-changes.json`. Production credentials, production databases, production APIs, and destructive real-data operations are prohibited.

### TEST_BUILD

Fill the whole affected module's observable gaps: public behavior, contracts, boundaries, invariants, failure paths, state transitions, and coupling risks. Do not stop after the changed happy path and do not mechanically exercise unrelated private lines.

When code has no controllable seam, the test work may make the minimum behavior-preserving production refactor needed for dependency injection, pure-function extraction, adapters, or controllable state. Record the patch and behavior-preservation check. If a public production contract would need to change, stop with `TEST_BLOCKED`.

A valid test that exposes a business/contract defect is evidence for `TEST_FAIL`. Do not repair the business defect inside this skill.

### EXECUTE_PROVE

Run progressively:

1. focused tests;
2. module/component tests;
3. contract/integration tests;
4. complete affected-module regression;
5. Regression Ring verification.

Only omit plan-marked non-required layers. Every N/A is structured with rationale, typed evidence, considered signals, and explanations for detected conflicts. The model retains semantic judgment; validation checks structure and obvious signal conflicts, not hidden intent. Append only runner-generated execution receipts containing:

- runner-generated receipt format, runner hash, request path/hash, and receipt-chain predecessor hash;
- unique selected execution identifier;
- layer and exact argv;
- confined working directory;
- complete effective environment key/value map used by the command;
- tool/runtime probe results;
- integer exit code (booleans are invalid);
- paths and hashes for complete stdout and stderr;
- reliability/flakiness classification.

Do not overwrite failed or superseded attempts. Do not retry until green. Use a bounded documented recovery attempt; required flakiness, unavailable infrastructure, unreliable execution, or cleanup failure is `TEST_BLOCKED`.

For each added or changed necessary behavior test, prove the test:

1. Prefer an isolated checkout or equivalent uncontaminated environment where the test fails against the pre-change baseline and passes against current code.
2. If baseline execution is inapplicable (for example, the public behavior did not exist), apply a minimal controlled mutation tied to the same matrix risk, observe failure, restore it completely, and observe current success.
3. Record `PROVEN`, justified `NOT_APPLICABLE`, or `UNPROVEN`.

Record baseline/current/mutation runner receipt IDs, request hash, baseline commit, stable source-snapshot and isolation hashes, mutation apply/restore hashes, expected failure signal match, and source-snapshot cleanup result. Necessary `UNPROVEN` behavior prevents `TEST_PASS`.

### EVIDENCE_PACKAGE

Create the complete package from `assets/evidence-package-template.json`, then hash its records. Set:

- `sensitivity=project-controlled`
- `environment_claim=mocked-code-level-only`
- `compatibility=legacy-test-report-interface-not-supported`

Preserve complete commands, environment values, stdout, stderr, patches, hashes, and history without automatic redaction. The project owns access control, retention, and upload policy. This does not permit production secrets or services.

Generate `test-report.md` solely from structured records. Regeneration must produce the same evidence pointers and verdict. The report is not independently editable authority.

Prepare `verdict.json` and the derived report, then let the validator finalize the non-circular attestation. Callers must not predeclare validator success as evidence.

### EVIDENCE_VALIDATE

Run:

```bash
python3 ${SKILL_DIR}/scripts/validate_test_evidence.py \
  --evidence-dir .prizmkit/test/evidence/<evidence-id> \
  --project-root <target-project-root> \
  --attest
```

`--attest` first validates the immutable payload while excluding only the final attestation/view records, atomically writes `validation.json`, refreshes final file hashes, then immediately performs a complete second validation. Subsequent checks omit `--attest` and verify the stored attestation. This avoids trusting a caller-authored `passed` marker or creating a self-referential manifest. The attestation proves package integrity and protocol consistency only; it is not proof against a same-permission producer.

When feasible, replay recorded requests through `build_test_evidence.py execute --replay-receipt ...`. Replay performs a new real execution and emits a new linked receipt; it does not pretend the attestation establishes what historically ran.

The validator checks all shipped JSON schemas, evidence-directory identity, live target-project inventories and aggregate hashes, stable source-snapshot identity with runtime paths excluded, changed-file/module-root/exclusion/Regression Ring cross-links, patch/diff binding, stage output ownership and predecessor hashes, generated-test snapshot existence, planned test/inventory/execution linkage, module/matrix completeness, successful selected runner receipts with request/raw-output binding, proof-linked isolated failures/current successes, controlled-mutation apply/restoration hashes, cleanup, structured N/A and obvious signal conflicts, production/unknown external-target safety, strict verdict semantics, and honest mocked-versus-real claims. `TEST_PASS` requires deterministic validator success.

## Resume and Invalidation

On invocation for an existing evidence target:

1. Validate manifest identity and every recorded file hash.
2. Recompute source, tests, contracts, lockfiles, environment, and plan target hashes.
3. Find the first stage whose input hash or output is invalid.
4. Preserve all prior executions and raw outputs immutably.
5. Invalidate that stage and every downstream stage; do not reuse their verdict claims.
6. Resume from the first invalid stage and write new execution identifiers.

Stages are idempotent with respect to the same canonical inputs. Never silently truncate a large module. Persist matrix progress and return `TEST_BLOCKED` until every necessary behavior and Regression Ring cell is complete.

## Terminal Semantics

- `TEST_PASS`: all required behavior/risk cells and Regression Ring checks are proven, all required executions are reliable and successful, no verdict-capable unresolved edge remains, cleanup succeeds, code-level requests remain replayable, and deterministic validation passes. This is protocol-validated code-level evidence, not a mathematical proof that no business behavior was omitted.
- `TEST_FAIL`: valid reliable evidence reproduces an implementation or resolved-contract failure. The package must remain complete enough to prove the failure.
- `TEST_BLOCKED`: scope/truth uncertainty, unavailable execution, necessary flakiness, incomplete evidence, failed cleanup, budget truncation, unproven behavior, conflicting truth, or deterministic validation failure.

No conditional pass exists.

## Responsibility Boundary

Return only the testing-domain verdict and evidence pointers. Do not:

- embed an independent AI reviewer or adversarial PASS judge;
- decide overall code quality;
- claim broad Spec compliance beyond tested contracts;
- repair a business defect exposed by a valid test;
- authorize commit, release, or deployment;
- claim mocked code-level evidence validates a deployed test or production environment.

The legacy report/verdict interface is intentionally unsupported. Do not migrate Pipeline or other Skill consumers and do not add a compatibility layer in this change.
