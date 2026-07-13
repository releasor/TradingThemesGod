# Derived Test Evidence Report Template

Generate this report solely from the structured, hashed evidence package. It is not independently editable authority. Any change to this file or another linked artifact without manifest regeneration causes deterministic validation failure.

```markdown
# Test Evidence Report

Derived from structured evidence. Authoritative package: `{evidence_dir}`

## Evidence
- Evidence ID: {64-character evidence_id}
- Protocol Version: {protocol_version}
- Classification: {behavior / lightweight}
- Baseline Commit: {baseline_commit}
- Working Diff SHA-256: {working_diff_sha256}
- Sensitivity: sensitivity=project-controlled
- Environment Claim: mocked-code-level-only

The evidence package preserves complete command, environment, stdout, stderr, patch, hash, and execution-history values without automatic redaction. The project owns access control, retention, and upload policy. Production credentials, production services, and destructive real-data operations are prohibited.

Mocked code-level evidence does not verify a real deployed environment.

## Scope
- Affected Module: {name} ({explicit / cohesion-derived})
- Primary Scope: {count and pointers}
- Regression Ring: {count and pointers}
- Verdict-capable Unresolved Edges: {count}

## Behavior-Risk Completeness
- Observable Behaviors: {count}
- Applicable Risk Cells: {count}
- Proven/Mapped Risk Cells: {count}
- Unresolved Risk Cells: {count}
- Diagnostic Coverage Signals: {values or not collected; never the completion basis}
- Matrix: `behavior-risk-matrix.json`

## Risk-Adaptive Test Plan
| Layer | Required | Rationale | Tests | Selected Execution IDs |
|-------|----------|-----------|-------|------------------------|
| focused | {yes/no} | {...} | {...} | {...} |
| module-component | {yes/no} | {...} | {...} | {...} |
| contract-integration | {yes/no} | {...} | {...} | {...} |
| affected-module-regression | {yes/no} | {...} | {...} | {...} |
| regression-ring | {yes/no} | {...} | {...} | {...} |

## Infrastructure and Contracts
- Native Runner/Conventions: {...}
- Infrastructure Changes: `infrastructure-changes.json`
- Contract Snapshots: `contracts/`
- Production Resources Used: no
- Cleanup Succeeded: {yes/no}

## Differential Proof
- PROVEN: {count}
- NOT_APPLICABLE: {count with rationale pointers}
- UNPROVEN: {count}
- Proof Record: `differential-proof.json`

## Executions
- Attempts Preserved: {count}
- Selected Required Executions: {IDs in order}
- Complete History: `executions.json`
- Raw Outputs: `raw/`

## Deterministic Validation
- Command: `python3 ${SKILL_DIR}/scripts/validate_test_evidence.py --evidence-dir {evidence_dir} --project-root {target_project_root}`
- Result: {passed / failed}
- Validation Record: `validation.json`

## Verdict
Verdict: TEST_PASS | TEST_FAIL | TEST_BLOCKED

## Responsibility Boundary
- Testing-domain verdict only: yes
- Overall code-quality or broad Spec verdict: no
- Business defects repaired by this skill: no
- Commit/release authorized: no
- Real deployed environment validated: no

## Compatibility
The legacy test-report interface is not supported. Existing Pipeline or other Skill consumers were not migrated and may be temporarily incompatible after installation.
```

## Verdict Rendering Rules

- Render `TEST_PASS` only after deterministic validation passes and all required evidence is proven.
- Render `TEST_FAIL` only with reliable reproduced failure execution pointers.
- Render `TEST_BLOCKED` with explicit blocker pointers.
- Never render `PASS`, `NEEDS_FIXES`, conditional pass, “ready for commit,” or release authorization.
- A lightweight `TEST_PASS` must say it proves only the deterministic lightweight claim, not runtime behavior.
