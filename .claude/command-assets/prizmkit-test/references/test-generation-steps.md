# Test Generation and Infrastructure Steps

Use this reference during `INFRA_READY`, `TEST_BUILD`, and `EXECUTE_PROVE`. The authoritative scope and completeness inputs are `scope.json`, `behavior-risk-matrix.json`, and `test-plan.json`.

## Scope Guard

For `scope=this-change`, changed files locate the affected module; they do not restrict tests to changed lines. Fill observable behavior/risk gaps across the whole affected module and execute its Regression Ring. Unrelated modules remain out of scope unless they are direct callers, consumers, shared contracts, or state dependencies.

Do not infer current-change scope from a directory name alone. Unknown scope is `TEST_BLOCKED`.

## Native Infrastructure Discovery

Before writing tests:

1. Inspect manifests, lockfiles, existing test files, runner configuration, scripts, fixtures, and CI commands.
2. Select the existing adequate runner and naming/import/mock conventions.
3. Let the target project's semantics determine framework, argv, cwd, timeout, attempts, concurrency, Mock tooling, layers, module roots, inventory patterns, and mutation technology; do not import fixed ecosystem defaults from this skill.
4. If no adequate infrastructure exists, add only the smallest project-native runner/config/dependencies required for the planned layers.
5. Verify dependency versions against the package registry before writing manifests.
6. Record every file/dependency/command change and verification in `infrastructure-changes.json`.
7. Never delete existing tests or add a second framework when the current one is adequate.

Create fixtures, fakes, contract-backed mock servers, browser harnesses, or isolated services only when required by `test-plan.json`. Every disposable resource needs a unique ID, bounded lifetime, and verified cleanup.

## Matrix-First Test Construction

For every behavior row:

1. Read the public interface, contract source, preconditions, inputs/boundaries, outputs, side effects, transitions, and errors.
2. Inspect existing test assertions—not names—to find proven cells.
3. Assess all eight risks: functional, boundary, permission, concurrency, idempotency, time, dependency, and consumer.
4. For every applicable risk, create a distinct test ID and expected execution layer.
5. For every non-applicable risk, record a concrete rationale tied to this behavior.
6. Keep unresolved truth or untestable necessary behavior explicit; it blocks rather than becoming guessed expected behavior.

A module is complete when all observable behaviors and applicable risks have mapped, proven tests and the Regression Ring passes. Line/branch/function coverage may reveal an omission and trigger another matrix review, but a percentage cannot complete a cell.

## Risk-Adaptive Layers

Choose only necessary test types, then assess all ordered layers in `test-plan.json`:

- **Unit/focused:** pure behavior, boundaries, errors, deterministic collaborators, and fast defect localization.
- **Module/component:** public module behavior with internal collaborators composed as production uses them.
- **Contract:** producer/consumer or adapter compatibility against a shared/snapshotted machine-readable contract.
- **Integration:** multiple local modules or isolated infrastructure when mocks cannot establish the relevant property.
- **Code-level E2E:** CLI/UI/API flow through code-level boundaries when user-visible composition is at risk and a native harness is available.
- **Affected-module regression:** every required test for the complete affected module.
- **Regression Ring:** direct callers, consumers, shared contracts, and state dependencies.

Do not require every layer mechanically. An omitted layer needs a specific reason such as “pure library has no UI or process boundary; module tests prove its public composition.” “Not tested” is not a rationale.

## Contract-Driven Doubles

Read `${SKILL_DIR}/references/contract-mock-protocol.md` for external databases, queues, filesystems, SaaS, browser backends, and cross-module endpoints.

Prefer shared OpenAPI/schema/types/generated models. Otherwise snapshot a locally derived contract and record derivation source. Generate success, boundary, malformed, timeout, and failure variants from that contract. Reject independently invented fields or a mock that cannot be traced to a snapshot.

Code-level evidence is mock-first and always reports `environment_claim=mocked-code-level-only`. Do not connect production or a user-linked deployed test database.

## Whole-Module Legacy Gap Filling

When a changed module has incomplete tests:

- enumerate every observable public behavior, not only changed exports;
- cover valid/minimal/complex inputs and contract-defined boundaries;
- cover outputs and response shape;
- assert side effects and absence of partial effects on failure;
- cover state transitions and idempotency where applicable;
- cover permissions, concurrency, clocks, external dependency failures, and consumer assumptions where applicable;
- avoid tests for unrelated private implementation lines.

Use `${SKILL_DIR}/references/service-boundary-test-catalog.md` to discover domain-specific risks, then map only contract-supported expectations.

## Testability Seams

If production code cannot be controlled:

1. Prefer injecting an existing dependency abstraction.
2. Otherwise extract a pure function, add an internal adapter, or make state/clock/randomness controllable.
3. Keep the public contract and observable behavior unchanged.
4. Record the production patch and behavior-preservation evidence.

If a public production contract must change, do not proceed autonomously; return `TEST_BLOCKED`.

## Valid Failures

Distinguish:

- **Test construction defect:** wrong import, syntax, fixture, mock contract, or runner usage. Fix the test/infrastructure within bounded attempts.
- **Reliable implementation/contract failure:** valid test against resolved truth repeatedly fails. Preserve the failure and return `TEST_FAIL`; do not repair business behavior here.
- **Uncertain/flaky/unavailable:** truth unresolved, required test unreliable, infrastructure unavailable, or cleanup fails. Return `TEST_BLOCKED`.

Never retry until green or silently weaken an assertion/scope.

## Execution and Differential Proof

Run selected tests in order through the bundled evidence builder: focused, module/component, contract/integration, affected-module regression, Regression Ring. The model writes schema-shaped requests; the builder performs the process and appends immutable runner-generated receipts to `executions.json`.

For each new/changed necessary behavior test:

1. In an isolated checkout/equivalent, run it against the actual baseline commit and require failure for the intended recorded signal, then current success.
2. If baseline proof is genuinely inapplicable, apply one model-selected minimal controlled mutation tied to the risk, require failure, restore it, and verify request/receipt, mutation apply/restore, isolation tree, and original project tree hashes.
3. Record `PROVEN`, structured `NOT_APPLICABLE`, or `UNPROVEN` with runner receipt IDs.

Necessary `UNPROVEN` evidence blocks. Store complete stdout/stderr in `raw/`; snapshots in `generated-tests/`; do not overwrite previous attempts.

## Completion Check

Before packaging:

- no applicable matrix cell lacks test/execution mapping;
- all required planned layers have reliable selected executions in order;
- affected-module and Regression Ring regressions are complete;
- every new/changed necessary behavior has valid differential proof;
- every isolated resource/mutation is cleaned up;
- no verdict-capable unresolved edge remains for pass;
- budgeted/staged work is complete, otherwise `TEST_BLOCKED`.
