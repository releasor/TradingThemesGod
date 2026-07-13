# Behavior-Risk Completeness Protocol

This protocol replaces interface-count and line-coverage completion with observable behavior/risk evidence. The authoritative matrix is `behavior-risk-matrix.json`, validated against `${SKILL_DIR}/assets/behavior-risk-matrix.schema.json`.

## Affected Module Boundary

Use an explicit project module when available. Otherwise derive a cohesive boundary from files that jointly implement one observable responsibility. Record the boundary decision, every declared module root, and every discovered file. Every changed file must appear in inventory or an evidence-backed exclusion.

Inventory discovery is a guard against obvious omissions, not a deterministic proof of semantic completeness. Static patterns cannot fully resolve reflection, registration, generated code, runtime configuration, or business concepts spread across unexpected files; preserve those as model judgment or unresolved edges.

- **Primary Scope:** all observable behavior of the affected module.
- **Regression Ring:** direct callers, consumers, shared contracts, and state dependencies.
- **Unresolved Edges:** dynamic or unprovable coupling, each marked verdict-capable or informational.

Changed lines locate the module but do not define completeness. A verdict-capable unresolved edge prevents `TEST_PASS`.

## Behavior-Risk Matrix

For each public observable behavior, record:

| Dimension | Required Content |
|-----------|------------------|
| Public behavior | User/caller-observable capability or guarantee |
| Contract source | Specification, machine-readable contract, acceptance condition, trusted test, caller, or implementation |
| Preconditions | Required identity, state, configuration, or dependency state |
| Inputs | Valid classes, empty/null/type/format variants |
| Boundaries | Contract-defined min/max/exact transition values |
| Outputs | Values, errors, response shape, generated identifiers |
| Side effects | Writes, calls, events, files, messages, or absence of partial effects |
| State transitions | Before/after state and idempotent/retry semantics |
| Error behavior | Validation, authorization, dependency, timeout, and malformed-response outcomes |
| Risks | Functional, boundary, permission, concurrency, idempotency, time, dependency, consumer |

Every risk cell is:

- `applicable`: mapped to one or more actual test IDs and execution IDs;
- `not_applicable`: a structured decision containing behavior-specific rationale, typed evidence, considered signals, and explanations for every detected conflict;
- `unresolved`: missing truth, testability, execution, or proof.

The model decides applicability from project semantics. The validator checks the structure and obvious signal conflicts only: identity/role/tenant suggests permission risk; locks/shared mutable state/workers suggest concurrency; retry/dedup/idempotency keys suggest idempotency; timeout/TTL/expiry suggests time; clients/contracts/network/storage suggest dependency; callers/consumers/shared contracts suggest consumer risk. A detected signal does not force applicability when the structured conflict explanation and evidence establish why it is irrelevant.

“Covered by happy path,” “probably fine,” or bare “N/A” is invalid rationale.

## Truth Resolution

Use this precedence and record the consulted sources:

1. specification;
2. machine-readable contract;
3. acceptance condition;
4. trusted existing test;
5. caller/consumer;
6. current implementation.

Do not freeze a possible current implementation bug into a characterization test. Conflicting higher-precedence sources that cannot be resolved produce `TEST_BLOCKED`.

## Applicable Risk Guidance

### Functional and Boundary

Cover typical/minimal/complex valid inputs; null/empty/wrong type; numeric/string/collection limits; malformed formats; output/error shape; every contract-relevant branch. Do not mechanically test private branches with no observable effect.

### Permission

Apply for identity, role, tenant, ownership, policy, entitlement, secret, or protected-resource behavior. Include missing/invalid identity, wrong owner/tenant, insufficient grant, and default-deny behavior.

### Concurrency

Apply when shared mutable state, locks, optimistic versions, duplicate workers/calls, race-prone caches, or transaction ordering can change observable results. Use deterministic coordination rather than timing sleeps.

### Idempotency

Apply to retries, deduplication keys, create/update/delete repetition, webhook/job replay, token rotation, and state transitions. Assert both result and side-effect count.

### Time

Apply to expiry, schedules, windows, date ranges, TTL, time zones, and clock-sensitive signatures. Control the clock and test exact boundary plus before/after.

### Dependency

Apply to databases, filesystems, queues, providers, clocks/randomness, cross-module adapters, and network clients. Use contract-driven doubles and assert failure mapping, no partial side effects, retry bounds, and cleanup.

### Consumer

Apply when callers depend on return shape, errors, side effects, ordering, generated assets, shared types/contracts, state, or invocation conventions. Regression Ring executions prove these assumptions.

## Completion Rule

The affected module is complete only when:

1. every observable behavior is represented;
2. every applicable risk has tests and reliable execution evidence;
3. every N/A cell has a concrete rationale;
4. every necessary new/changed test has differential proof;
5. complete affected-module regression passes;
6. Regression Ring verification passes;
7. no verdict-capable unresolved edge remains;
8. cleanup and deterministic package validation succeed.

Line, branch, and function coverage are diagnostic signals for possible omitted behavior. They never substitute for matrix evidence and no mechanical threshold is required.

## Derived Markdown

`test-report.md` may render a compact matrix summary, but it is not authoritative. The JSON matrix and hashed test/execution records control the verdict. Editing the report or any linked artifact without regenerating hashes must fail deterministic validation.
