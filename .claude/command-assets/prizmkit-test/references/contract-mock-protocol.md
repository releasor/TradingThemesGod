# Contract-Driven Mock Protocol

Use this protocol for external databases, queues, filesystems, SaaS APIs, browser-facing backends, generated clients, and cross-module endpoints. Code-level evidence is mock-first; linking a real test database or deployed environment is outside `/prizmkit-test`.

## Contract Source Precedence

Use the highest available source:

1. Shared machine-readable contract used by producer and consumer: OpenAPI, JSON Schema, Protocol Buffers, GraphQL schema, database schema, AsyncAPI, shared language types, or generated client model.
2. Versioned contract fixture already stored by the target project.
3. Locally derived contract fixture built from a named source such as public adapter types, caller expectations, migration schema, provider documentation snapshot, or captured non-production example already authorized for the project.

Never invent request/response fields independently when a shared source exists. Never derive expected behavior only from the changed implementation when a higher-precedence source disagrees.

## Required Contract Snapshot

Copy the exact contract input into `contracts/` and record:

- contract ID and version when available;
- source path or derivation source;
- SHA-256;
- producer and consumer/module names;
- derivation command or steps;
- unsupported or ambiguous fields;
- whether it represents an external provider, local module, or persistence boundary.

If derivation is not reproducible or sources conflict, add an Unresolved Edge and issue `TEST_BLOCKED` when it can affect the verdict.

## Building Doubles

Generate or configure fakes, mocks, fixtures, and mock servers from the contract snapshot. Verify both request and response directions where applicable:

- required/optional fields and nullability;
- field names, types, enums, formats, and bounds;
- status/error variants;
- stateful sequence or transition rules;
- pagination/cursor semantics;
- idempotency, time, and concurrency behavior;
- malformed, timeout, and dependency-failure variants.

A mock-success-only double is insufficient. Record the matrix behavior/risk cells each double supports and the tests/executions that exercised them.

## Databases and Stateful Services

Prefer an in-memory fake or isolated disposable service only when it preserves the contract being tested. Do not point code-level tests at production or a user-linked deployed test database. For database adapters, derive the fixture from schema/migrations/shared models and test transaction, constraint, rollback, and error behavior relevant to the affected module.

Any isolated resource must have a unique identifier, bounded lifetime, and verified cleanup. Cleanup failure produces `TEST_BLOCKED`.

## Real-Environment Separation

Every package and report must state:

- `environment_claim=mocked-code-level-only`
- Mocked code-level evidence does not verify a real deployed environment.
- Real test-environment, production, credential, network policy, data migration, and operational validation require a separate authorized process.

Reject a package that claims deployment/environment verification from contract mocks, local fakes, containers, or isolated services.

## Prohibitions

- No production credentials, databases, queues, APIs, object storage, or real user data.
- No destructive operation against external data.
- No independently invented incompatible mock contract.
- No silent contract drift.
- No automatic upload of complete raw evidence; the project owns access, retention, and upload policy.
