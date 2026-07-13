# Evidence Request Protocol

Load this reference when writing an inventory, execution, differential, resume, or replay request. Validate every authoritative record against `${SKILL_DIR}/assets/authoritative-records.schema.json`; the validator loads the named `$defs` for each file.

## Request Ownership

The model writes project-semantic requests after inspecting manifests, runner configuration, contracts, test conventions, changed files, and module boundaries. The bundled builder owns process execution, raw output, receipts, isolation, tree hashes, and invalidation calculations.

Never hand-author `executions.json` receipt fields. Never copy a command's claimed output into `raw/`. Invoke the builder so provenance is linked to the actual process.

## Inventory Request

Place a request under `requests/` with:

- `request_version: "1.0"`;
- `categories`: project-relative glob arrays for source, tests, contracts, and lockfiles;
- nonempty `changed_files` and declared `module_roots`;
- structured `exclusions`, each with path, rationale, and discovery evidence;
- `discovery_evidence` for manifests, runner configuration, filesystem discovery, contracts, lockfiles, and boundary analysis;
- nonempty `plan_inputs` carrying the semantic planning inputs whose hash controls resume.

An empty inventory is not evidence of an empty module. Ensure every changed file exists and is either inventoried or explicitly excluded with evidence. The builder independently enumerates every actual file under each model-declared module root; every enumerated file must appear in one inventory category or a structured exclusion. This does not decide whether the model selected the right semantic module boundary, but it prevents silent omission after that boundary is declared.

## Execution Request

Use an argv array so the runner does not interpret a shell string. Required fields are:

- `request_version`, `purpose`, `command`, `cwd`;
- environment additions (the runner starts from a minimal runtime environment and the receipt records every effective value);
- model-selected `tool_version_commands`;
- selected `layer` and semantic `test_ids`;
- structured `external_targets`.

Optional `timeout_seconds`, `attempt_policy`, and `concurrency` remain model-chosen. The builder records them through request binding but does not invent values or silently retry.

The request path must be beneath the evidence directory. `cwd` resolves beneath the selected execution root. Missing commands produce an actual exit 127 receipt; missing cwd or escaped paths block before execution.

## Differential Request

Record:

- behavior ID and model-selected `baseline` or `controlled-mutation` method;
- the nested execution request;
- actual baseline commit and the stable source-snapshot hash produced with the builder's runtime exclusions;
- mutation patch path when applicable;
- concrete expected failure signals.

The builder creates isolated copies from the same stable source-snapshot scope, executes the failing and current sides, records receipts, binds the differential request hash, and verifies that behavior-bearing project content is unchanged. Runtime state, evidence output, linked Agent worktrees, Git metadata, and Python bytecode caches do not participate in source identity. A proof is `PROVEN` only when the intended failure signal appears, the failing side exits nonzero, current exits zero, and cleanup/snapshot checks pass.

## Structured N/A

Use the same structure for omitted layers, not-applicable risk cells, stage N/A, and proof N/A:

- `rationale`: behavior-specific reasoning;
- `evidence`: one or more typed discovery records;
- `considered_signals`: signals examined before deciding N/A;
- `conflicts`: every detected contradictory signal plus an explanation.

The model retains semantic judgment. The deterministic validator checks shape and obvious signal conflicts only. For example, auth/tenant/role signals conflict with permission N/A; lock/shared-state/worker signals conflict with concurrency N/A; retry/idempotency/dedup signals conflict with idempotency N/A; timeout/TTL/expiry signals conflict with time N/A; clients/contracts/network signals conflict with dependency N/A; callers/consumers/shared-contract mappings conflict with consumer N/A. A conflict can be accepted only when explicitly recorded and explained.

## Record-to-Schema Map

| Authoritative record | Schema definition |
|---|---|
| `change-classification.json` | `changeClassification` |
| `scope.json` | `scope` |
| `target-inventory.json` | `targetInventory` |
| `test-plan.json` | `testPlan` |
| `requests/*.execution.json` | `executionRequest` |
| receipt entries in `executions.json` | `executionReceipt` / `executionLog` |
| `requests/*differential*.json` | `differentialRequest` |
| `differential-proof.json` | `differentialProof` |
| `infrastructure-changes.json` | `infrastructureChanges` |
| `verdict.json` | `verdict` |
| `validation.json` | `validation` |
| `lightweight-verification.json` | `lightweightVerification` |

`manifest.json` and `behavior-risk-matrix.json` retain their dedicated schemas. All schemas reject unknown fields where the protocol owns the record.
