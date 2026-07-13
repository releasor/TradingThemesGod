# Service Behavior-Risk Catalog

Use this catalog during `CONTRACT_MODEL` and `TEST_BUILD` to discover domain-specific observable risks. It supplies questions, not truth: every expected value must come from the recorded truth precedence and every external dependency double must follow `references/contract-mock-protocol.md`.

## How to Use This Catalog

1. Classify the affected module by its public behavior, dependencies, state changes, and resolved contracts.
2. Select every service type that applies; one behavior can combine several types.
3. Add applicable cases to `behavior-risk-matrix.json` and map them to test/execution IDs.
4. Derive mock requests/responses from shared machine-readable or locally snapshotted contracts. Never independently invent provider/database/queue behavior.
5. Record a concrete rationale for every non-applicable risk.
6. Treat coverage metrics as diagnostic only; complete observable behavior and risk rather than private lines.

Code-level tests are mock-first and must state that they do not verify a real deployed environment. Production credentials, services, and data are prohibited.

## Service Type Detection

| Signal | Likely Service Type |
|--------|---------------------|
| login, logout, signup, password, session, token, jwt, oauth, refresh | Auth / Session / Token |
| role, permission, policy, access, entitlement, plan, quota, ownership | Authorization / Permission / Entitlement |
| payment, wallet, billing, subscription, invoice, refund, balance, currency | Payment / Wallet / Billing / Refund |
| repository, model, dao, create, read, update, delete, insert, save, remove | CRUD / Repository / Database |
| search, list, page, cursor, filter, sort, query, limit, offset | Search / List / Pagination |
| validate, parse, normalize, transform, schema, sanitize, format | Validation / Parser / Normalizer |
| upload, download, storage, file, blob, s3, image, mime, path | File Upload / Storage |
| notify, email, sms, webhook, template, recipient, provider | Notification / Email / Webhook |
| job, queue, worker, scheduler, cron, retry, backoff, task | Job / Queue / Scheduler |
| cache, ttl, rate limit, throttle, idempotency, dedupe, lock | Cache / Rate Limit / Idempotency |
| client, sdk, request, fetch, provider, api key, endpoint, response | API Client / Third-Party Integration |
| date, time, expiry, expiration, ttl, schedule, window, timezone | Date / Time / Expiration |

When names and behavior disagree, trust behavior and dependencies over names. For example, `createCheckoutSession()` is payment-related even if it lives in a controller module.

## Universal Boundary Matrix

Apply these categories to every public function/class method before adding service-specific cases:

- **Valid input**: typical valid input, minimal valid input, and complex valid input when supported.
- **Empty input**: `null` / `undefined` / `None`, empty string, empty array/object, whitespace-only string.
- **Numeric boundaries**: zero, one, minimum allowed value, maximum allowed value, just below/above limits.
- **Collection boundaries**: zero items, one item, many items, duplicate items, first/last element behavior.
- **Type and format errors**: wrong type, malformed string, unsupported enum, missing required parameter.
- **Branch paths**: each `if/else`, `switch/case/default`, ternary side, and loop path with zero/one/many iterations.
- **State and side effects**: before/after state, writes, emitted events, dependency method calls, call count/order/arguments.
- **Dependency failures**: mocked database errors, network timeouts, storage failures, provider errors, clock/randomness behavior.

## Service-Specific Boundary Cases

### Auth / Session / Token Services

Generate applicable cases for:

- Missing identifier, missing password, empty credentials, malformed email/username.
- Identifier normalization: uppercase/lowercase email, leading/trailing whitespace, Unicode usernames when supported.
- User not found, wrong password, unverified account, disabled account, locked account.
- Failed login count just below/at/above lock threshold.
- Successful login creates exactly one session/token with expected expiry and persisted state.
- Token missing, malformed, invalid signature, wrong algorithm, expired, not-yet-valid, revoked.
- Refresh token rotation: old refresh token reuse, missing refresh token, expired refresh token, revoked refresh token.
- Logout idempotency: logout with valid token, already logged-out token, missing token.
- OAuth/callback flows: missing code, missing state, state mismatch, provider error, provider returns incomplete profile.
- Dependency failures: user store error, password hasher error, token signer/verifier error, clock skew.

### Authorization / Permission / Entitlement Services

Generate applicable cases for:

- Missing principal, anonymous principal, principal without roles/permissions.
- Default-deny behavior when no policy matches.
- Role hierarchy: basic role, elevated role, admin override, deny rule precedence.
- Resource ownership: owner, non-owner, tenant mismatch, organization mismatch.
- Entitlement states: active, expired, canceled, trial, disabled feature, missing plan.
- Quota boundaries: usage below limit, exactly at limit, one over limit, reset window boundary.
- Duplicate or conflicting permissions.
- Policy conditions with missing attributes, malformed attributes, unknown action/resource.
- Dependency failures: policy store error, entitlement lookup error, quota service timeout.

### Payment / Wallet / Billing / Refund Services

Generate applicable cases for:

- Amount zero, negative amount, minimum billable unit, maximum allowed amount, just above maximum.
- Currency precision: too many decimal places, integer minor units, rounding at half-unit boundaries.
- Balance boundaries: balance exactly equals debit amount, balance one minor unit below amount, zero balance.
- Currency mismatch between wallet, invoice, and payment request.
- Idempotency: missing key, duplicate key with same payload, duplicate key with different payload.
- Transaction states: pending, succeeded, failed, canceled, already paid, already refunded.
- Refund boundaries: zero refund, partial refund, full refund, cumulative refunds equal original amount, cumulative refunds exceed original amount.
- Concurrent debit/refund attempts against the same account or transaction.
- Subscription/billing cycles: trial start/end, expired subscription, canceled subscription, renewal at boundary time.
- Provider failures: timeout, 4xx/5xx, malformed response, duplicate provider event, out-of-order webhook.
- Side effects: ledger entry count, balance mutation, webhook/event emission, provider call arguments.

### CRUD / Repository / Database Services

Generate applicable cases for:

- Create with missing required fields, nullable fields set to `null`, optional fields omitted.
- Duplicate unique key, generated ID collision, invalid foreign key, unknown enum value.
- Read/update/delete with nonexistent ID, malformed ID, deleted/soft-deleted ID.
- Partial update semantics: omitted field vs `undefined` vs `null`, empty patch object.
- Optimistic locking: expected version, stale version, missing version.
- Soft delete behavior: excluded by default, included only when requested, double delete idempotency.
- Transaction behavior: rollback when one write fails, no partial side effects after failure.
- Database dependency errors: connection failure, constraint violation, timeout.
- Repository side effects: correct query arguments, write count, returned entity shape.

### Search / List / Pagination / Sorting Services

Generate applicable cases for:

- Empty query, whitespace query, special characters, Unicode query, injection-like strings treated as data.
- No results, one result, many results, duplicate ranking/sort values.
- Page/offset pagination: page 0, page 1, last page, beyond last page, negative page/offset.
- Cursor pagination: missing cursor, malformed cursor, expired cursor, cursor at final item.
- Limit boundaries: omitted limit, limit 0, limit 1, maximum limit, maximum + 1.
- Sorting: default sort, invalid sort field, invalid direction, stable ordering with ties.
- Filters: empty filter set, unknown filter, conflicting filters, inclusive/exclusive date ranges.
- Total count and hasNext/hasPrevious flags at page boundaries.
- Dependency failures: search index unavailable, database query error, stale index response.

### Validation / Parser / Normalizer Services

Generate applicable cases for:

- Missing input, `null` / `undefined` / `None`, empty string, whitespace-only string.
- Minimum and maximum length; just below/above configured length boundaries.
- Special characters, Unicode, emoji, newline/control characters, normalization-sensitive characters.
- Wrong type, mixed-type arrays, numeric strings vs numbers, booleans represented as strings.
- Unknown fields in strict mode, extra fields in permissive mode, duplicate keys/items.
- Invalid formats: email, URL, date, UUID, JSON, CSV, phone number, currency.
- Normalization idempotency: applying the normalizer twice yields the same result.
- Error shape: path/field name, code, message, and aggregation of multiple errors.
- Parser failures: malformed payload, truncated payload, unsupported version/schema.

### File Upload / Storage Services

Generate applicable cases for:

- Zero-byte file, one-byte file, just below max size, exactly max size, just above max size.
- MIME/type mismatch between content, extension, and declared header.
- Unsupported file type, missing extension, uppercase extension, compound extension.
- Filename boundaries: empty name, very long name, Unicode name, duplicate name, path traversal characters.
- Storage key collisions and deterministic key generation.
- Checksum/hash mismatch, corrupted stream, interrupted upload, storage write failure.
- Image/media metadata boundaries: dimensions too small/large, unsupported codec, malformed metadata.
- Delete/read behavior for missing object, already-deleted object, permission-denied object.
- Side effects: storage provider call arguments, metadata record creation, cleanup on failure.

### Notification / Email / Webhook Services

Generate applicable cases for:

- Missing recipient, invalid email/phone/URL, empty recipient list, duplicate recipients.
- Recipient preferences: unsubscribed, disabled channel, quiet hours, blocked user.
- Template variables: missing required variable, extra variable, `null` variable, special characters/HTML escaping.
- Provider selection: unsupported channel, fallback provider, disabled provider.
- Deduplication: duplicate notification key, repeated webhook event, retry with same id.
- Provider responses: success, rate limit, timeout, 4xx/5xx, malformed response, partial multi-recipient failure.
- Webhook security: missing signature, invalid signature, timestamp outside tolerance, replayed event.
- Side effects: event status persisted, retry scheduled or suppressed, provider called with expected payload.

### Job / Queue / Scheduler Services

Generate applicable cases for:

- Missing payload, empty payload, malformed payload, unsupported job type/version.
- Duplicate job ID, idempotent processing of already-completed job, requeue behavior.
- Retry boundaries: first failure, retry count just below max, at max, over max, poison/dead-letter path.
- Backoff calculation: zero delay, minimum delay, maximum delay, jitter bounds when deterministic/mocked.
- Schedule boundaries: run in past, run now, run in future, invalid cron, daylight-saving transition.
- Concurrency: two workers claim same job, lock acquisition failure, stale lock recovery.
- Cancellation: before start, during processing, after completion.
- Side effects: ack/nack calls, status transitions, retry scheduling, emitted events.

### Cache / Rate Limit / Idempotency Services

Generate applicable cases for:

- Cache miss, hit, stale hit, expired entry, invalidation, key collision.
- TTL boundaries: zero TTL, negative TTL, one unit TTL, exact expiry instant, just before/after expiry.
- Serialization/deserialization failure, corrupted cached value, unsupported value type.
- Cache stampede: concurrent misses for the same key should not duplicate expensive work when guarded.
- Rate limit boundaries: count below limit, exactly at limit, one above limit, window rollover.
- Missing actor key: anonymous user, missing IP, shared tenant/global scope.
- Idempotency key: missing, malformed, reused with same payload, reused with different payload, expired record.
- Lock behavior: lock unavailable, lock timeout, release on success, release on failure.
- Backing store failures: Redis/cache down, slow response, partial write.

### API Client / Third-Party Integration Services

Generate applicable cases for:

- Missing base URL, missing API key, malformed configuration, unsupported region/environment.
- Request building: query encoding, header inclusion, body serialization, path parameter escaping.
- Response handling: 200 with valid body, 204/no body, malformed JSON, missing required field, unknown extra field.
- Error responses: 400, 401/403, 404, 409, 429, 500/503; retryable vs non-retryable classification.
- Timeout, network error, DNS/connect failure, aborted request.
- Retry boundaries: zero retries, one retry then success, max retries exhausted, backoff capped.
- Pagination: empty page, last page, next token missing/malformed, duplicate page token.
- Auth refresh/signing: expired access token, refresh failure, invalid signature, clock skew.
- Circuit breaker or fallback behavior when present.

### Date / Time / Expiration Services

Generate applicable cases for:

- Exact boundary: `now == startsAt`, `now == expiresAt`, one millisecond/second before and after.
- Inclusive vs exclusive interval ends according to the contract.
- Start after end, zero-length interval, negative duration, missing timezone.
- Time zones: UTC vs local time, DST jump forward/back, leap day, month end, year end.
- Clock skew tolerance for tokens, webhooks, scheduled jobs, and signed requests.
- Recurring schedules: first occurrence, last occurrence, skipped occurrence, invalid cron/expression.
- TTL/window calculations: zero TTL, negative TTL, max TTL, rollover between windows.

## When Multiple Service Types Apply

Combine the relevant sections and remove duplicate cases. Prioritize tests that exercise business invariants over tests that only repeat generic invalid input handling. For example, a wallet debit function should cover payment amount boundaries, idempotency replay, and date/expiration behavior if it also accepts an expiring authorization.

## N/A Rules

Mark a category `N/A` when the unit has no corresponding input, state, or dependency. Include a short reason:

- `N/A — no external provider dependency`
- `N/A — function is pure and has no stateful side effects`
- `N/A — pagination is handled by caller, not this unit`
- `N/A — concurrency safety belongs to integration test because unit has no shared mutable state`
