# Trusted Evidence Execution

Load this reference before `SCOPE_DISCOVER`, `EXECUTE_PROVE`, resume, or replay. It defines which choices remain with the model and which evidence mechanics are fixed.

## Two Parameter Classes

### Model-Chosen Project Parameters

Inspect the target project and choose these semantically:

- native test framework, runner, command, flags, and working directory;
- timeout, attempt/retry policy, concurrency, resource limits, and isolation strategy;
- unit/module/contract/integration/code-level E2E layers;
- fixture, fake, Mock, service-double, browser, database, and mutation technology;
- module roots, public behavior boundary, inventory patterns, exclusions, Regression Ring, and differential method;
- environment classification and endpoint allow/deny evidence.

The protocol does not prescribe Jest, pytest, a timeout number, a retry count, coverage threshold, runner flag, or mutation package. Record the reason for each choice in request and planning records.

### Protocol-Fixed Locators and Mechanisms

The protocol fixes only what trustworthy, replayable packaging needs:

- locator arguments: project root, evidence directory, request/manifest/inventory/receipt path;
- schema-shaped request records;
- project-root and evidence-root path confinement;
- actual child-process execution without a shell;
- complete stdout/stderr capture and output hashes;
- complete effective environment and tool-probe capture;
- runner-generated UUID receipt, request hash, runner hash, and receipt-chain hash;
- append-only execution history;
- differential isolation, cleanup, and tree hashes;
- deterministic resume invalidation calculation;
- strict schema and cross-record validation.

## Trust Boundary

A receipt proves that the bundled runner produced a record with the captured inputs and outputs during this invocation. The runner snapshots its own executable bytes inside the evidence package so later validation does not silently depend on whichever PrizmKit version happens to be installed. Hashes bind bytes together and detect later drift. They do not create cryptographic non-repudiation and cannot prove that a same-OS-user, same-permission producer did not replace the runner, requests, repository, or evidence package before validation.

Treat evidence as auditable project-controlled provenance, not a defense against a malicious same-privilege actor. The validator checks consistency, obvious conflicts, and replayability; it cannot mathematically prove that the model found every business behavior.

## Builder Commands

Write requests beneath the evidence directory, then invoke the bundled script:

```bash
python3 ${SKILL_DIR}/scripts/build_test_evidence.py \
  --project-root <target-project-root> \
  --evidence-dir <evidence-dir> \
  inventory --request requests/inventory.json

python3 ${SKILL_DIR}/scripts/build_test_evidence.py \
  --project-root <target-project-root> \
  --evidence-dir <evidence-dir> \
  execute --request requests/focused.json

python3 ${SKILL_DIR}/scripts/build_test_evidence.py \
  --project-root <target-project-root> \
  --evidence-dir <evidence-dir> \
  differential --request requests/differential.json

python3 ${SKILL_DIR}/scripts/build_test_evidence.py \
  --project-root <target-project-root> \
  --evidence-dir <evidence-dir> \
  resume --manifest manifest.json --inventory target-inventory.json
```

The subcommands cover fixed mechanics only:

- `inventory`: expand model-selected project-relative patterns, independently enumerate all actual files under each declared module root, reject files that are neither categorized nor structurally excluded, hash actual files, and bind discovery inputs;
- `execute`: run the declared argv in the declared safe cwd and append a runner-generated receipt;
- `differential`: execute baseline or controlled-mutation proof in isolated copies and verify cleanup/tree binding;
- `resume`: compare hashes and stage outputs to compute an invalidation decision while retaining `semantic_review_required=true`.

## Replay

Replay a prior receipt through the runner rather than treating attestation as historical proof:

```bash
python3 ${SKILL_DIR}/scripts/build_test_evidence.py \
  --project-root <target-project-root> \
  --evidence-dir <evidence-dir> \
  execute --replay-receipt receipts/<receipt>.json
```

The recorded request hash must still match. Replay emits a new receipt linked with `replay_of`; it never overwrites the historical receipt. A replay can still differ because project state, installed tools, clocks, external test services, or environment values changed. Report those differences instead of claiming historical equivalence.

## External Target Safety

Do not block merely because a string contains `production`; names can be misleading. Classify every external target using endpoint/configuration evidence:

- block `production` and `unknown` external targets;
- permit only model-classified isolated/test/staging targets with explicit allow evidence and no deny evidence;
- preserve the complete evidence used for the decision;
- keep local fakes and in-process contract mocks classified `local` with `external=false`.

The model owns the semantic classification; the runner enforces the declared production/unknown safety invariant and rejects contradictory allow/deny records.
