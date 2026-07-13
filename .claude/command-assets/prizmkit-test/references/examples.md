# Test Evidence Examples

## 1. Normally Tested Module Change — TEST_PASS

Input:

```text
/prizmkit-test scope=this-change artifact_dir=<change-artifact>
```

A library parser changes one accepted input form. Scope discovery selects the complete parser module and two direct consumers. Existing module tests already cover most behaviors.

The run:

1. Classifies `behavior`.
2. Adds the changed parser behavior plus existing observable parser behavior to the matrix.
3. Selects focused, affected-module regression, and Regression Ring layers; module-component and contract-integration are N/A with concrete pure-library rationale.
4. Adds missing malformed-input and consumer-shape tests.
5. Proves changed tests fail on baseline and pass currently.
6. Packages all command/environment/output history.
7. Deterministically validates.

Handoff:

```text
TEST_PASS
Evidence: .prizmkit/test/evidence/<evidence-id>/
Validator: passed
Mocked code-level evidence does not verify a real deployed environment.
```

## 2. Incompletely Tested Legacy Module — Whole-Module Gap Filling

A queue worker retry change touches a legacy worker with one happy-path test. Changed lines identify the module, but Primary Scope includes parsing, claim, processing, retry, dead-letter, acknowledgment, idempotency, and dependency-failure behavior.

`TEST_BUILD` fills observable gaps across the module, not unrelated private utility lines. It adds deterministic fake-clock and contract-backed queue tests for retry just below/at/above maximum, duplicate delivery, malformed payload, lock failure, no partial side effect, ack/nack calls, and dead-letter transition. Regression Ring runs the scheduler and producer contract checks. Coverage percentage is recorded only as a diagnostic signal.

The run cannot pass until every applicable behavior-risk cell and Regression Ring execution is mapped and proven.

## 3. Contract-Coupled Modules — Contract-Driven Mocks

An API client and consumer share OpenAPI. The run snapshots the OpenAPI document into `contracts/`, records its source/hash, and generates mock responses for success, schema error, 429, timeout, malformed body, and pagination token boundaries.

The mock is rejected if it invents an incompatible field or cannot trace behavior to the contract. Contract and consumer executions pass, and the report states `environment_claim=mocked-code-level-only`; it makes no claim about a deployed SaaS environment.

## 4. Reliable Business Defect — TEST_FAIL

Resolved specification and OpenAPI require a negative amount to return a validation error without a write. A generated contract test reliably observes success plus a database-adapter call.

The test is valid, current and affected-module executions reproduce the failure, and raw output is preserved. `/prizmkit-test` does not change production business behavior. It packages:

```text
TEST_FAIL
Reproduced failure: amount-boundary-negative
Evidence: .prizmkit/test/evidence/<evidence-id>/
```

## 5. Unknown Coupling or Conflicting Truth — TEST_BLOCKED

A dynamically loaded plugin may consume the changed result shape, but its registry is generated remotely and unavailable. The edge can change the verdict, so it remains verdict-capable and unresolved.

Alternatively, specification and shared schema disagree on nullability with no authoritative resolution. The skill does not freeze current behavior into a characterization test.

Both produce:

```text
TEST_BLOCKED
Blocker: verdict-capable unresolved edge or conflicting truth
Evidence: .prizmkit/test/evidence/<evidence-id>/
```

## 6. Baseline Inapplicable — Controlled Mutation

A newly added CLI command has no pre-change interface, so baseline execution is justified `NOT_APPLICABLE` as a direct proof method. In an uncontaminated checkout, the run applies a minimal mutation that removes the command registration, observes the command test fail for that risk, restores the patch, verifies source hashes and cleanup, then observes current success. The behavior is `PROVEN` by `controlled-mutation`.

If restoration cannot be proven, the verdict is `TEST_BLOCKED`.

## 7. Interrupted or Budgeted Run

On recovery, the skill validates stage outputs and target hashes. A changed lockfile invalidates `INFRA_READY` and every downstream stage but preserves earlier execution history immutably. The run resumes there.

If the budget ends after half a large module's required matrix is tested, progress persists and the result is `TEST_BLOCKED`; no scope is silently truncated.

## 8. Tampering

After packaging, changing `raw/execution-003.stdout`, a contract snapshot, generated test, source patch, or derived report produces a content-hash mismatch. Changing identity inputs without recomputing the canonical evidence ID also fails.

```bash
python3 ${SKILL_DIR}/scripts/validate_test_evidence.py \
  --evidence-dir .prizmkit/test/evidence/<evidence-id> \
  --project-root <target-project-root>
```

Result: non-zero with `Test evidence validation: FAIL`. A tampered package cannot retain `TEST_PASS`.

## 9. Lightweight Change

A comments-only diff is deterministically classified and parser/format/generated-output checks pass. Behavior-only stages are marked not applicable with reasons. `TEST_PASS` means the lightweight claim is proven; the report explicitly does not claim full runtime test evidence.

## Compatibility Notice

The legacy `PASS | NEEDS_FIXES | BLOCKED` Markdown report interface is intentionally not preserved. Existing Pipeline and Skill consumers are not migrated here and may be temporarily incompatible after installation.
