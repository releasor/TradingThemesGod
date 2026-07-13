#!/usr/bin/env python3
"""Deterministically validate a PrizmKit structured test-evidence package.

This validator deliberately checks protocol mechanics and content-addressed evidence;
it does not treat a successful validation as a claim about a deployed environment or
as authorization to commit, release, or repair product behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

STAGES = [
    "CHANGE_CLASSIFY", "SCOPE_DISCOVER", "CONTRACT_MODEL", "TEST_PLAN",
    "INFRA_READY", "TEST_BUILD", "EXECUTE_PROVE", "EVIDENCE_PACKAGE",
    "EVIDENCE_VALIDATE",
]
CORE_BEHAVIOR_STAGES = set(STAGES)
VERDICTS = {"TEST_PASS", "TEST_FAIL", "TEST_BLOCKED"}
RISK_KEYS = {
    "functional", "boundary", "permission", "concurrency",
    "idempotency", "time", "dependency", "consumer",
}
LAYER_ORDER = {
    "focused": 0,
    "module-component": 1,
    "contract-integration": 2,
    "affected-module-regression": 3,
    "regression-ring": 4,
}
FINAL_RECORDS = {"validation.json", "verdict.json", "test-report.md"}
COMMON_RECORDS = {
    "change-classification.json", "scope.json", "target-inventory.json",
    "environment.json", "executions.json", "verdict.json", "validation.json",
    "source-change.patch", "test-report.md",
}
BEHAVIOR_RECORDS = {
    "behavior-risk-matrix.json", "test-plan.json", "infrastructure-changes.json",
    "differential-proof.json",
}
LIGHTWEIGHT_RECORDS = {"lightweight-verification.json"}
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
UUID_RE = re.compile(r"^[a-f0-9-]{36}$")
BLOCKED_EXTERNAL_CLASSES = {"production", "unknown"}
SNAPSHOT_VOLATILE_ROOTS = (
    ".prizmkit/state",
    ".prizmkit/test/evidence",
    ".claude/worktrees",
)
SNAPSHOT_VOLATILE_NAMES = {".git", "__pycache__"}
RISK_CONFLICT_PATTERNS = {
    "permission": re.compile(r"auth|tenant|role|permission|access|acl|rbac", re.I),
    "concurrency": re.compile(r"lock|shared[ _-]?state|worker|queue|concurr|parallel|race", re.I),
    "idempotency": re.compile(r"retry|idempot|dedup|duplicate|replay", re.I),
    "time": re.compile(r"timeout|ttl|expiry|expire|clock|date|time", re.I),
    "dependency": re.compile(r"client|contract|network|https?|api|service|dependenc|external", re.I),
    "consumer": re.compile(r"caller|consumer|shared[ _-]?contract|import", re.I),
}


class EvidenceError(Exception):
    """Raised for malformed or unreadable evidence input."""


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key: {key}")
        result[key] = value
    return result


def _reject_non_json_number(value: str) -> Any:
    raise ValueError(f"non-JSON numeric constant: {value}")


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_json_number,
        )
    except FileNotFoundError as exc:
        raise EvidenceError(f"missing required file: {path.name}") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise EvidenceError(f"invalid JSON in {path.name}: {exc}") from exc


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def is_relative_path(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and not Path(value).is_absolute()


def safe_path(root: Path, relative: Any, errors: list[str], label: str) -> Path | None:
    if not is_relative_path(relative):
        errors.append(f"{label} must be a non-empty relative path")
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label} escapes its root: {relative}")
        return None
    return candidate


def path_under(relative: str, directory: str) -> bool:
    try:
        Path(relative).relative_to(directory)
        return True
    except ValueError:
        return False


def path_below_or_equal(path: str, root: str) -> bool:
    normalized_path = Path(path).as_posix()
    normalized_root = Path(root).as_posix().rstrip("/")
    return normalized_path == normalized_root or normalized_path.startswith(f"{normalized_root}/")


def resolve_ref(schema: dict[str, Any], root_schema: dict[str, Any]) -> dict[str, Any]:
    reference = schema.get("$ref")
    if not reference:
        return schema
    if not isinstance(reference, str) or not reference.startswith("#/"):
        raise EvidenceError(f"unsupported schema reference: {reference}")
    current: Any = root_schema
    for token in reference[2:].split("/"):
        if not isinstance(current, dict):
            raise EvidenceError(f"invalid schema reference: {reference}")
        current = current[token.replace("~1", "/").replace("~0", "~")]
    if not isinstance(current, dict):
        raise EvidenceError(f"schema reference is not an object: {reference}")
    return current


def json_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if expected == "null":
        return value is None
    return False


def json_equals(left: Any, right: Any) -> bool:
    """JSON equality without Python's bool-is-an-int equivalence."""
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return type(left) is type(right) and left == right
    return left == right


def validate_schema(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    location: str,
    errors: list[str],
) -> None:
    """Validate the strict JSON-Schema subset used by skill-owned schemas."""
    schema = resolve_ref(schema, root_schema)

    for child in schema.get("allOf", []):
        if isinstance(child, dict):
            validate_schema(value, child, root_schema, location, errors)
    if "const" in schema:
        require(json_equals(value, schema["const"]), f"{location}: value does not match const", errors)
    if "enum" in schema:
        allowed = schema["enum"]
        require(
            isinstance(allowed, list) and any(json_equals(value, item) for item in allowed),
            f"{location}: value is outside enum",
            errors,
        )

    expected = schema.get("type")
    if expected is not None:
        expected_types = expected if isinstance(expected, list) else [expected]
        valid_types = [item for item in expected_types if isinstance(item, str)]
        if not any(json_type_matches(value, item) for item in valid_types):
            name = " or ".join(valid_types) if valid_types else repr(expected)
            errors.append(f"{location}: expected {name}")
            return

    if isinstance(value, str):
        if "minLength" in schema:
            require(len(value) >= schema["minLength"], f"{location}: string is too short", errors)
        if "maxLength" in schema:
            require(len(value) <= schema["maxLength"], f"{location}: string is too long", errors)
        if "pattern" in schema:
            try:
                matched = re.search(schema["pattern"], value) is not None
            except re.error as exc:
                raise EvidenceError(f"invalid schema pattern at {location}: {exc}") from exc
            require(matched, f"{location}: string does not match pattern", errors)

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema:
            require(value >= schema["minimum"], f"{location}: number is below minimum", errors)
        if "maximum" in schema:
            require(value <= schema["maximum"], f"{location}: number is above maximum", errors)
        if "exclusiveMinimum" in schema:
            require(value > schema["exclusiveMinimum"], f"{location}: number is not above exclusive minimum", errors)
        if "exclusiveMaximum" in schema:
            require(value < schema["exclusiveMaximum"], f"{location}: number is not below exclusive maximum", errors)

    if isinstance(value, list):
        if "minItems" in schema:
            require(len(value) >= schema["minItems"], f"{location}: array has too few items", errors)
        if "maxItems" in schema:
            require(len(value) <= schema["maxItems"], f"{location}: array has too many items", errors)
        if schema.get("uniqueItems") is True:
            require(len({canonical_sha256(item) for item in value}) == len(value), f"{location}: array items are not unique", errors)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_schema(item, item_schema, root_schema, f"{location}[{index}]", errors)

    if isinstance(value, dict):
        if "minProperties" in schema:
            require(len(value) >= schema["minProperties"], f"{location}: object has too few properties", errors)
        if "maxProperties" in schema:
            require(len(value) <= schema["maxProperties"], f"{location}: object has too many properties", errors)
        required = schema.get("required", [])
        for key in required:
            require(key in value, f"{location}: missing required property {key}", errors)
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                continue
            if additional is False:
                errors.append(f"{location}: unexpected property {key}")
            elif isinstance(additional, dict):
                validate_schema(item, additional, root_schema, f"{location}.{key}", errors)
        for key, child_schema in properties.items():
            if key in value and isinstance(child_schema, dict):
                validate_schema(value[key], child_schema, root_schema, f"{location}.{key}", errors)


def assets_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "assets"


def load_schema(name: str) -> dict[str, Any]:
    schema = load_json(assets_dir() / name)
    if not isinstance(schema, dict):
        raise EvidenceError(f"schema is not an object: {name}")
    return schema


def validate_definition(
    value: Any,
    definition: str,
    records_schema: dict[str, Any],
    location: str,
    errors: list[str],
) -> None:
    definitions = records_schema.get("$defs")
    if not isinstance(definitions, dict) or not isinstance(definitions.get(definition), dict):
        raise EvidenceError(f"missing authoritative schema definition: {definition}")
    validate_schema(value, definitions[definition], records_schema, location, errors)


def require_manifest_entry(
    relative: str,
    entry_map: dict[str, dict[str, Any]],
    root: Path,
    errors: list[str],
    label: str,
) -> Path | None:
    entry = entry_map.get(relative)
    require(entry is not None, f"{label} is not manifest-hashed: {relative}", errors)
    path = safe_path(root, relative, errors, label)
    if path is None:
        return None
    if not path.is_file():
        errors.append(f"{label} is missing: {relative}")
        return None
    if entry is not None:
        require(file_sha256(path) == entry.get("sha256"), f"{label} hash mismatch: {relative}", errors)
    return path


def structured_na(
    value: Any,
    records_schema: dict[str, Any],
    location: str,
    errors: list[str],
    risk: str | None = None,
) -> None:
    validate_definition(value, "naDecision", records_schema, location, errors)
    if not isinstance(value, dict):
        return
    signals = value.get("considered_signals")
    require(isinstance(signals, list) and bool(signals), f"{location}: N/A needs considered signals", errors)
    evidence = value.get("evidence")
    require(isinstance(evidence, list) and bool(evidence), f"{location}: N/A needs discovery evidence", errors)
    conflicts = value.get("conflicts")
    require(isinstance(conflicts, list), f"{location}: N/A conflicts must be an array", errors)
    if not isinstance(signals, list) or not isinstance(conflicts, list):
        return

    signal_text = "\n".join(
        item for item in signals if isinstance(item, str)
    )
    if isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, dict):
                source = item.get("source")
                observations = item.get("observations")
                if isinstance(source, str):
                    signal_text += f"\n{source}"
                if isinstance(observations, list):
                    signal_text += "\n" + "\n".join(value for value in observations if isinstance(value, str))
    if risk and risk in RISK_CONFLICT_PATTERNS and RISK_CONFLICT_PATTERNS[risk].search(signal_text):
        pattern = RISK_CONFLICT_PATTERNS[risk]
        matching_signals = [
            item for item in conflicts
            if isinstance(item, dict)
            and isinstance(item.get("signal"), str)
            and pattern.search(item["signal"])
            and isinstance(item.get("explanation"), str)
            and len(item["explanation"].strip()) >= 8
        ]
        require(
            bool(matching_signals),
            f"{location}: {risk} N/A conflicts with discovered signals but has no explained conflict",
            errors,
        )


def validate_external_targets(value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{location}: external targets must be an array")
        return
    for index, target in enumerate(value):
        target_location = f"{location}[{index}]"
        if not isinstance(target, dict):
            errors.append(f"{target_location}: external target must be an object")
            continue
        external = target.get("external")
        require(type(external) is bool, f"{target_location}: external must be a boolean", errors)
        if external is not True:
            continue
        classification = target.get("classification")
        require(classification not in BLOCKED_EXTERNAL_CLASSES, f"{target_location}: external {classification} target is blocked", errors)
        require(classification in {"isolated", "test", "staging"}, f"{target_location}: external target classification is unsafe", errors)
        endpoint_evidence = target.get("endpoint_evidence")
        allow_evidence = target.get("allow_evidence")
        deny_evidence = target.get("deny_evidence")
        require(isinstance(endpoint_evidence, list) and bool(endpoint_evidence), f"{target_location}: external target lacks endpoint evidence", errors)
        require(isinstance(allow_evidence, list) and bool(allow_evidence), f"{target_location}: external target lacks allow evidence", errors)
        require(isinstance(deny_evidence, list) and not deny_evidence, f"{target_location}: external target has deny evidence", errors)


def stage_input_sha(stage_name: str, target_hashes: dict[str, str], predecessor_files: list[dict[str, str]]) -> str:
    return canonical_sha256({
        "stage": stage_name,
        "target_hashes": target_hashes,
        "predecessor_outputs": sorted(predecessor_files, key=lambda item: item["path"]),
    })


def validate_manifest(
    root: Path,
    manifest: dict[str, Any],
    manifest_schema: dict[str, Any],
    records_schema: dict[str, Any],
    errors: list[str],
    ignored_hash_paths: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    validate_schema(manifest, manifest_schema, manifest_schema, "manifest", errors)
    require(manifest.get("sensitivity") == "project-controlled", "sensitivity must be project-controlled", errors)
    require(manifest.get("environment_claim") == "mocked-code-level-only", "environment claim must be mocked-code-level-only", errors)
    require(manifest.get("compatibility") == "legacy-test-report-interface-not-supported", "legacy compatibility boundary missing", errors)

    identity_inputs = manifest.get("evidence_id_inputs")
    if isinstance(identity_inputs, dict):
        require(manifest.get("evidence_id") == canonical_sha256(identity_inputs), "evidence_id does not match canonical identity inputs", errors)
        require(root.name == manifest.get("evidence_id"), "evidence directory name does not match evidence_id", errors)
        require(identity_inputs.get("baseline_commit") == manifest.get("baseline_commit"), "baseline commit identity mismatch", errors)
        require(identity_inputs.get("working_diff_sha256") == manifest.get("working_diff_sha256"), "working diff identity mismatch", errors)

    entries = manifest.get("files")
    entry_map: dict[str, dict[str, Any]] = {}
    if not isinstance(entries, list):
        return entry_map
    for index, entry in enumerate(entries):
        entry_location = f"manifest.files[{index}]"
        if not isinstance(entry, dict):
            continue
        relative = entry.get("path")
        if not is_relative_path(relative):
            continue
        require(relative not in entry_map, f"duplicate manifest file entry: {relative}", errors)
        entry_map[relative] = entry
        candidate = safe_path(root, relative, errors, entry_location)
        if candidate is None:
            continue
        if not candidate.is_file():
            errors.append(f"manifest file missing: {relative}")
            continue
        if relative not in (ignored_hash_paths or set()):
            require(file_sha256(candidate) == entry.get("sha256"), f"content hash mismatch: {relative}", errors)

    actual_paths = {
        candidate.relative_to(root).as_posix()
        for candidate in root.rglob("*")
        if candidate.is_file() and candidate.name != "manifest.json"
    }
    require(set(entry_map) == actual_paths, "manifest must hash every evidence file exactly once", errors)

    stages = manifest.get("stages")
    if not isinstance(stages, list):
        return entry_map
    names = [stage.get("name") for stage in stages if isinstance(stage, dict)]
    require(names == STAGES, "stages are missing or out of order", errors)
    predecessor_files: list[dict[str, str]] = []
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        name = stage.get("name")
        outputs = stage.get("outputs")
        status = stage.get("status")
        na = stage.get("not_applicable")
        if status == "not_applicable":
            structured_na(na, records_schema, f"stage {name} not_applicable", errors)
            require(outputs == [], f"not-applicable stage must not claim outputs: {name}", errors)
        elif status == "complete":
            require(na is None, f"complete stage must have null not_applicable: {name}", errors)
        for output in outputs if isinstance(outputs, list) else []:
            entry = entry_map.get(output)
            require(entry is not None, f"stage output is not a hashed evidence file: {name}/{output}", errors)
            if entry is not None:
                require(entry.get("produced_by") == name, f"stage output producer mismatch: {name}/{output}", errors)
        if isinstance(name, str) and isinstance(manifest.get("target_hashes"), dict):
            expected_input = stage_input_sha(name, manifest["target_hashes"], predecessor_files)
            require(stage.get("input_sha256") == expected_input, f"stage input dependency hash mismatch: {name}", errors)
        predecessor_files.extend(
            {"path": output, "sha256": entry_map[output]["sha256"]}
            for output in outputs if isinstance(outputs, list) and output in entry_map and output not in FINAL_RECORDS
        )
    return entry_map


def validate_inventory(
    root: Path,
    project_root: Path,
    manifest: dict[str, Any],
    inventory: dict[str, Any],
    scope: dict[str, Any],
    plan: dict[str, Any] | None,
    entry_map: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    categories = inventory.get("categories")
    expected_categories = {"source", "tests", "contracts", "lockfiles"}
    inventory_by_category: dict[str, dict[str, str]] = {}
    aggregates: dict[str, str] = {}
    if not isinstance(categories, dict) or set(categories) != expected_categories:
        errors.append("target inventory categories are incomplete")
        return inventory_by_category, aggregates

    all_paths: dict[str, str] = {}
    for category in sorted(expected_categories):
        entries = categories.get(category)
        category_entries: dict[str, str] = {}
        if not isinstance(entries, list):
            errors.append(f"target inventory category is not an array: {category}")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"invalid target inventory entry: {category}")
                continue
            relative = entry.get("path")
            expected_hash = entry.get("sha256")
            if not is_relative_path(relative) or not is_sha256(expected_hash):
                errors.append(f"invalid target inventory entry: {category}")
                continue
            require(relative not in category_entries, f"duplicate target inventory path: {relative}", errors)
            require(relative not in all_paths, f"target inventory path appears in multiple categories: {relative}", errors)
            candidate = safe_path(project_root, relative, errors, "target inventory path")
            if candidate is None or not candidate.is_file():
                errors.append(f"target project file missing: {relative}")
                continue
            actual = file_sha256(candidate)
            require(actual == expected_hash, f"target project file drift: {relative}", errors)
            category_entries[relative] = actual
            all_paths[relative] = category
        inventory_by_category[category] = category_entries
        aggregates[category] = canonical_sha256([
            {"path": path, "sha256": category_entries[path]}
            for path in sorted(category_entries)
        ])

    try:
        environment = load_json(root / "environment.json")
    except EvidenceError as exc:
        errors.append(str(exc))
        environment = None
    aggregates["environment"] = canonical_sha256(environment)
    plan_inputs = inventory.get("plan_inputs")
    require(isinstance(plan_inputs, dict) and bool(plan_inputs), "target inventory plan_inputs missing", errors)
    aggregates["plan"] = canonical_sha256(plan_inputs)
    require(manifest.get("target_hashes") == aggregates, "target hashes do not match live project inventory", errors)
    require(scope.get("target_hashes") == aggregates, "scope target hashes do not match live inventory", errors)
    if plan is not None:
        require(plan.get("target_hashes") == aggregates, "test plan target hashes do not match live inventory", errors)
        require(plan.get("plan_inputs") == plan_inputs, "test plan inputs do not match target inventory", errors)

    patch = require_manifest_entry("source-change.patch", entry_map, root, errors, "source-change patch")
    if patch is not None:
        require(manifest.get("working_diff_sha256") == file_sha256(patch), "working_diff_sha256 does not match source-change.patch", errors)

    request_relative = inventory.get("inventory_request_path")
    request_path = require_manifest_entry(request_relative, entry_map, root, errors, "inventory request") if isinstance(request_relative, str) else None
    if request_path is not None:
        require(file_sha256(request_path) == inventory.get("inventory_request_sha256"), "inventory request hash mismatch", errors)
        request = load_json(request_path)
        if isinstance(request, dict):
            require(request.get("changed_files") == inventory.get("changed_files"), "inventory request changed_files mismatch", errors)
            require(request.get("module_roots") == inventory.get("module_roots"), "inventory request module_roots mismatch", errors)
            require(request.get("exclusions") == scope.get("exclusions"), "inventory request exclusions mismatch", errors)
            require(request.get("plan_inputs") == plan_inputs, "inventory request plan_inputs mismatch", errors)
        else:
            errors.append("inventory request must be an object")

    return inventory_by_category, aggregates


def validate_scope(
    scope: dict[str, Any],
    inventory: dict[str, Any],
    inventory_by_category: dict[str, dict[str, str]],
    project_root: Path,
    evidence_root: Path,
    errors: list[str],
) -> None:
    changed_files = scope.get("changed_files")
    require(isinstance(changed_files, list) and bool(changed_files), "scope changed_files is empty", errors)
    if not isinstance(changed_files, list):
        return
    require(len(set(changed_files)) == len(changed_files), "scope changed_files contains duplicates", errors)
    require(sorted(changed_files) == sorted(inventory.get("changed_files", [])), "scope and inventory changed_files do not agree", errors)

    exclusions = scope.get("exclusions")
    exclusion_paths = {
        item.get("path") for item in exclusions if isinstance(item, dict) and isinstance(item.get("path"), str)
    } if isinstance(exclusions, list) else set()
    require(exclusion_paths == set(inventory.get("exclusions", [])), "scope and inventory exclusions do not agree", errors)
    inventory_paths = {path for entries in inventory_by_category.values() for path in entries}
    for relative in changed_files:
        candidate = safe_path(project_root, relative, errors, "changed file")
        if relative in exclusion_paths:
            require(relative not in inventory_paths, f"excluded changed file is also inventoried: {relative}", errors)
        else:
            require(candidate is not None and candidate.is_file(), f"changed file is not live: {relative}", errors)
            require(relative in inventory_paths, f"changed file is neither inventoried nor excluded: {relative}", errors)

    roots = scope.get("module_roots")
    require(isinstance(roots, list) and bool(roots), "scope module_roots is empty", errors)
    if not isinstance(roots, list):
        return
    scope_root_paths = [item.get("path") for item in roots if isinstance(item, dict)]
    require(len(set(scope_root_paths)) == len(scope_root_paths), "scope module_roots contains duplicates", errors)
    require(sorted(scope_root_paths) == sorted(inventory.get("module_roots", [])), "scope and inventory module_roots do not agree", errors)
    inventory_root_files = inventory.get("module_root_files")
    require(isinstance(inventory_root_files, dict), "inventory module_root_files is missing", errors)
    require(
        isinstance(inventory_root_files, dict) and set(inventory_root_files) == set(scope_root_paths),
        "inventory module_root_files does not match declared module roots",
        errors,
    )
    evidence_resolved = evidence_root.resolve()
    for root_info in roots:
        if not isinstance(root_info, dict):
            continue
        root_relative = root_info.get("path")
        root_path = safe_path(project_root, root_relative, errors, "module root")
        require(root_path is not None and root_path.exists(), f"module root is not live: {root_relative}", errors)
        files = root_info.get("files")
        require(isinstance(files, list) and bool(files), f"module root has no files: {root_relative}", errors)
        live_root_files: list[str] = []
        if root_path is not None and root_path.exists():
            candidates = [root_path] if root_path.is_file() else root_path.rglob("*")
            for candidate in candidates:
                if not candidate.is_file() or ".git" in candidate.parts or "__pycache__" in candidate.parts:
                    continue
                resolved = candidate.resolve()
                if resolved == evidence_resolved or evidence_resolved in resolved.parents:
                    continue
                live_root_files.append(resolved.relative_to(project_root).as_posix())
        recorded_root_files = inventory_root_files.get(root_relative) if isinstance(inventory_root_files, dict) else None
        require(
            isinstance(recorded_root_files, list) and sorted(recorded_root_files) == sorted(live_root_files),
            f"module root live enumeration differs from inventory: {root_relative}",
            errors,
        )
        require(
            isinstance(files, list) and sorted(files) == sorted(live_root_files),
            f"scope module root files are incomplete: {root_relative}",
            errors,
        )
        for relative in files if isinstance(files, list) else []:
            candidate = safe_path(project_root, relative, errors, "module root file")
            require(candidate is not None and candidate.is_file(), f"module root file is not live: {relative}", errors)
            require(path_below_or_equal(relative, root_relative), f"module root file lies outside its root: {relative}", errors)
            require(relative in inventory_paths or relative in exclusion_paths, f"module root file is neither inventoried nor excluded: {relative}", errors)

    require(
        isinstance(scope.get("primary_scope"), list) and bool(scope.get("primary_scope")),
        "Primary Scope must contain observable behavior descriptions",
        errors,
    )


def validate_requests_and_receipts(
    root: Path,
    entry_map: dict[str, dict[str, Any]],
    records_schema: dict[str, Any],
    errors: list[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    execution_requests: dict[str, dict[str, Any]] = {}
    differential_requests: dict[str, dict[str, Any]] = {}
    requests_root = root / "requests"
    if requests_root.exists():
        for path in sorted(requests_root.rglob("*.json")):
            relative = path.relative_to(root).as_posix()
            require_manifest_entry(relative, entry_map, root, errors, "request")
            try:
                request = load_json(path)
            except EvidenceError as exc:
                errors.append(str(exc))
                continue
            if not isinstance(request, dict):
                errors.append(f"request must be an object: {relative}")
                continue
            if "execution_request" in request:
                validate_definition(request, "differentialRequest", records_schema, relative, errors)
                nested = request.get("execution_request")
                if isinstance(nested, dict):
                    validate_definition(nested, "executionRequest", records_schema, f"{relative}.execution_request", errors)
                    validate_external_targets(nested.get("external_targets"), f"{relative}.execution_request.external_targets", errors)
                differential_requests[relative] = request
            elif "command" in request and "layer" in request:
                validate_definition(request, "executionRequest", records_schema, relative, errors)
                validate_execution_request_semantics(request, relative, errors)
                validate_external_targets(request.get("external_targets"), f"{relative}.external_targets", errors)
                execution_requests[relative] = request
            elif set(request) == {
                "request_version", "categories", "changed_files", "module_roots",
                "exclusions", "discovery_evidence", "plan_inputs",
            }:
                require(request.get("request_version") == "1.0", f"unsupported inventory request version: {relative}", errors)
            else:
                errors.append(f"unrecognized request record: {relative}")

    runner = Path(__file__).resolve().with_name("build_test_evidence.py")
    if not runner.is_file():
        errors.append("runner source is missing: build_test_evidence.py")

    executions_path = root / "executions.json"
    try:
        executions = load_json(executions_path)
    except EvidenceError as exc:
        errors.append(str(exc))
        return execution_requests, differential_requests, []
    validate_definition(executions, "executionLog", records_schema, "executions", errors)
    if not isinstance(executions, list):
        return execution_requests, differential_requests, []

    receipt_by_id: dict[str, dict[str, Any]] = {}
    seen_receipt_paths: set[str] = set()
    attempts_by_request: dict[str, int] = {}
    previous_receipt: dict[str, Any] | None = None
    for index, receipt in enumerate(executions):
        location = f"executions[{index}]"
        if not isinstance(receipt, dict):
            continue
        validate_definition(receipt, "executionReceipt", records_schema, location, errors)
        receipt_id = receipt.get("execution_id")
        require(isinstance(receipt_id, str) and bool(UUID_RE.fullmatch(receipt_id)), f"{location}: invalid execution_id", errors)
        require(receipt_id not in receipt_by_id, f"duplicate execution id: {receipt_id}", errors)
        if isinstance(receipt_id, str):
            receipt_by_id[receipt_id] = receipt

        require(receipt.get("receipt_format") == "prizmkit-runner-generated-v1", f"{location}: receipt is not runner-generated", errors)
        runner_relative = receipt.get("runner_path")
        runner_snapshot = require_manifest_entry(
            runner_relative, entry_map, root, errors, "runner snapshot",
        ) if isinstance(runner_relative, str) else None
        require(
            isinstance(runner_relative, str) and path_under(runner_relative, "runner"),
            f"{location}: runner snapshot must be under runner/",
            errors,
        )
        if runner_snapshot is not None:
            require(file_sha256(runner_snapshot) == receipt.get("runner_sha256"), f"{location}: runner snapshot hash mismatch", errors)
        request_relative = receipt.get("request_path")
        request = execution_requests.get(request_relative) if isinstance(request_relative, str) else None
        require(request is not None, f"{location}: receipt references an unknown execution request", errors)
        request_path = require_manifest_entry(request_relative, entry_map, root, errors, "receipt request") if isinstance(request_relative, str) else None
        if request_path is not None:
            require(file_sha256(request_path) == receipt.get("request_sha256"), f"{location}: request hash mismatch", errors)
        if isinstance(request, dict):
            for key in ("purpose", "command", "cwd", "layer", "test_ids", "external_targets"):
                require(receipt.get(key) == request.get(key), f"{location}: receipt {key} does not match request", errors)
            expected_environment = request.get("environment")
            actual_environment = receipt.get("environment")
            require(isinstance(actual_environment, dict) and isinstance(actual_environment.get("PATH"), str), f"{location}: receipt lacks complete PATH environment", errors)
            if isinstance(expected_environment, dict) and isinstance(actual_environment, dict):
                for key, value in expected_environment.items():
                    require(actual_environment.get(key) == value, f"{location}: receipt environment differs for {key}", errors)
            expected_probes = request.get("tool_version_commands")
            actual_probes = receipt.get("tool_versions")
            require(isinstance(actual_probes, dict), f"{location}: receipt tool_versions must be an object", errors)
            if isinstance(expected_probes, dict) and isinstance(actual_probes, dict):
                require(set(actual_probes) == set(expected_probes), f"{location}: receipt tool probe names differ from request", errors)
                for probe_name, command in expected_probes.items():
                    probe = actual_probes.get(probe_name)
                    require(isinstance(probe, dict), f"{location}: tool probe is not an object: {probe_name}", errors)
                    if isinstance(probe, dict):
                        require(probe.get("command") == command, f"{location}: tool probe command mismatch: {probe_name}", errors)
                        require("exit_code" in probe or "error" in probe, f"{location}: tool probe has no result: {probe_name}", errors)

        validate_execution_request_semantics(receipt, location, errors, receipt=True)
        validate_external_targets(receipt.get("external_targets"), f"{location}.external_targets", errors)
        for raw_key, hash_key in (("stdout_path", "stdout_sha256"), ("stderr_path", "stderr_sha256")):
            relative = receipt.get(raw_key)
            raw_path = safe_path(root, relative, errors, f"{location}.{raw_key}")
            require(isinstance(relative, str) and path_under(relative, "raw"), f"{location}: {raw_key} must be under raw/", errors)
            if raw_path is not None:
                require(raw_path.is_file(), f"{location}: raw output is missing: {relative}", errors)
                if raw_path.is_file():
                    require(file_sha256(raw_path) == receipt.get(hash_key), f"{location}: raw output hash mismatch: {relative}", errors)
                    require_manifest_entry(relative, entry_map, root, errors, "raw output")

        recorded_receipt_path = f"receipts/{receipt_id}.json" if isinstance(receipt_id, str) else ""
        receipt_path = require_manifest_entry(recorded_receipt_path, entry_map, root, errors, "receipt") if recorded_receipt_path else None
        if receipt_path is not None:
            try:
                require(load_json(receipt_path) == receipt, f"{location}: receipt file does not match execution log", errors)
            except EvidenceError as exc:
                errors.append(str(exc))
        seen_receipt_paths.add(recorded_receipt_path)

        expected_previous = canonical_sha256(previous_receipt) if previous_receipt is not None else None
        require(receipt.get("previous_receipt_sha256") == expected_previous, f"{location}: receipt chain mismatch", errors)
        request_hash = receipt.get("request_sha256")
        if isinstance(request_hash, str):
            attempts_by_request[request_hash] = attempts_by_request.get(request_hash, 0) + 1
            require(receipt.get("attempt_index") == attempts_by_request[request_hash], f"{location}: attempt_index is not request-local sequence", errors)
        replay_of = receipt.get("replay_of")
        if replay_of is not None:
            previous = receipt_by_id.get(replay_of)
            require(previous is not None, f"{location}: replay source is missing", errors)
            if previous is not None:
                require(previous.get("request_sha256") == request_hash, f"{location}: replay request differs from source", errors)
        previous_receipt = receipt

    receipt_files = {
        path.relative_to(root).as_posix()
        for path in (root / "receipts").rglob("*.json")
    } if (root / "receipts").is_dir() else set()
    require(receipt_files == seen_receipt_paths, "receipt directory does not exactly match executions.json", errors)
    return execution_requests, differential_requests, executions


def validate_execution_request_semantics(
    value: dict[str, Any],
    location: str,
    errors: list[str],
    receipt: bool = False,
) -> None:
    command = value.get("command")
    require(isinstance(command, list) and bool(command) and all(isinstance(item, str) and item for item in command), f"{location}: command must be a non-empty string argv", errors)
    environment = value.get("environment")
    require(isinstance(environment, dict) and all(isinstance(key, str) and isinstance(item, str) for key, item in environment.items()), f"{location}: environment must contain complete string values", errors)
    test_ids = value.get("test_ids")
    require(isinstance(test_ids, list) and all(isinstance(item, str) and item for item in test_ids), f"{location}: test_ids must be string IDs", errors)
    if receipt:
        require(type(value.get("selected_execution")) is bool, f"{location}: selected_execution must be boolean", errors)
        require(type(value.get("reliable")) is bool, f"{location}: reliable must be boolean", errors)
        require(type(value.get("exit_code")) is int and not isinstance(value.get("exit_code"), bool), f"{location}: exit_code must be an integer", errors)


def validate_plan_and_scope_bindings(
    root: Path,
    project_root: Path,
    manifest: dict[str, Any],
    scope: dict[str, Any],
    matrix: dict[str, Any],
    plan: dict[str, Any],
    inventory_by_category: dict[str, dict[str, str]],
    entry_map: dict[str, dict[str, Any]],
    executions: list[dict[str, Any]],
    records_schema: dict[str, Any],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    require(scope.get("affected_module") == matrix.get("affected_module", {}).get("name"), "matrix affected module does not match scope", errors)
    require(scope.get("boundary_source") == matrix.get("affected_module", {}).get("boundary_source"), "matrix boundary source does not match scope", errors)
    require(scope.get("primary_scope") == matrix.get("primary_scope"), "matrix primary scope does not match scope", errors)
    scope_ring = sorted((item.get("name"), item.get("kind")) for item in scope.get("regression_ring", []) if isinstance(item, dict))
    matrix_ring = sorted((item.get("name"), item.get("kind")) for item in matrix.get("regression_ring", []) if isinstance(item, dict))
    require(scope_ring == matrix_ring, "scope and matrix regression rings do not agree", errors)

    unresolved = scope.get("unresolved_edges")
    if manifest.get("final_verdict") == "TEST_PASS" and isinstance(unresolved, list):
        for edge in unresolved:
            if isinstance(edge, dict) and edge.get("verdict_capable") is True and edge.get("resolved") is not True:
                errors.append("TEST_PASS has a verdict-capable unresolved edge")

    layers = plan.get("layers")
    layer_map = {item.get("name"): item for item in layers if isinstance(item, dict)} if isinstance(layers, list) else {}
    require(set(layer_map) == set(LAYER_ORDER), "test plan must assess every risk-adaptive layer exactly once", errors)
    for name, layer in layer_map.items():
        required = layer.get("required")
        na = layer.get("not_applicable")
        require(type(required) is bool, f"layer required flag invalid: {name}", errors)
        if required is True:
            require(na is None, f"required layer cannot be N/A: {name}", errors)
        elif required is False:
            structured_na(na, records_schema, f"layer {name} not_applicable", errors)
    if matrix.get("regression_ring"):
        require(layer_map.get("regression-ring", {}).get("required") is True, "nonempty regression ring must be required", errors)
    if manifest.get("final_verdict") == "TEST_PASS":
        for layer_name, layer in layer_map.items():
            if layer.get("required") is True:
                matches = [
                    item for item in executions
                    if item.get("selected_execution") is True
                    and item.get("layer") == layer_name
                    and item.get("reliable") is True
                    and item.get("exit_code") == 0
                ]
                require(bool(matches), f"required layer lacks a successful reliable receipt: {layer_name}", errors)

    tests = plan.get("tests")
    test_map: dict[str, dict[str, Any]] = {}
    if not isinstance(tests, list):
        return test_map
    selected_by_test: dict[str, list[dict[str, Any]]] = {}
    for receipt in executions:
        if receipt.get("selected_execution") is True:
            for test_id in receipt.get("test_ids", []):
                if isinstance(test_id, str):
                    selected_by_test.setdefault(test_id, []).append(receipt)
    known_behavior_ids = {item.get("id") for item in matrix.get("behaviors", []) if isinstance(item, dict)}
    for test in tests:
        if not isinstance(test, dict):
            continue
        test_id = test.get("id")
        require(isinstance(test_id, str) and bool(test_id), "planned test has no ID", errors)
        require(test_id not in test_map, f"duplicate planned test ID: {test_id}", errors)
        if not isinstance(test_id, str):
            continue
        test_map[test_id] = test
        behavior_ids = test.get("behavior_ids")
        require(isinstance(behavior_ids, list) and bool(behavior_ids), f"planned test has no behavior mapping: {test_id}", errors)
        for behavior_id in behavior_ids if isinstance(behavior_ids, list) else []:
            require(behavior_id in known_behavior_ids, f"planned test maps unknown behavior: {test_id}/{behavior_id}", errors)
        project_relative = test.get("project_path")
        inventory_relative = test.get("inventory_path")
        snapshot_relative = test.get("snapshot_path")
        project_path = safe_path(project_root, project_relative, errors, f"planned test {test_id} project_path")
        require(project_path is not None and project_path.is_file(), f"planned test live path is missing: {test_id}", errors)
        require(inventory_relative == project_relative, f"planned test inventory path differs from live project path: {test_id}", errors)
        require(inventory_relative in inventory_by_category.get("tests", {}), f"planned test is not in the test inventory: {test_id}", errors)
        snapshot_path = require_manifest_entry(snapshot_relative, entry_map, root, errors, f"planned test snapshot {test_id}") if isinstance(snapshot_relative, str) else None
        require(isinstance(snapshot_relative, str) and path_under(snapshot_relative, "generated-tests"), f"planned test snapshot must be under generated-tests/: {test_id}", errors)
        if project_path is not None and project_path.is_file() and snapshot_path is not None and snapshot_path.is_file():
            require(file_sha256(project_path) == file_sha256(snapshot_path), f"generated test snapshot differs from live test: {test_id}", errors)
        test_layers = test.get("layers")
        require(isinstance(test_layers, list) and bool(test_layers), f"planned test has no layers: {test_id}", errors)
        for layer in test_layers if isinstance(test_layers, list) else []:
            require(layer in LAYER_ORDER, f"planned test uses unknown layer: {test_id}/{layer}", errors)
        matching_receipts = selected_by_test.get(test_id, [])
        require(bool(matching_receipts), f"planned test has no selected receipt: {test_id}", errors)
        for receipt in matching_receipts:
            require(receipt.get("layer") in test_layers, f"planned test receipt uses an unplanned layer: {test_id}", errors)

    for ring in scope.get("regression_ring", []):
        if not isinstance(ring, dict):
            continue
        ring_name = ring.get("name")
        ring_files = ring.get("files")
        require(isinstance(ring_files, list) and bool(ring_files), f"regression ring has no files: {ring_name}", errors)
        for relative in ring_files if isinstance(ring_files, list) else []:
            candidate = safe_path(project_root, relative, errors, "regression ring file")
            require(candidate is not None and candidate.is_file(), f"regression ring file is not live: {relative}", errors)
            require(relative in inventory_by_category.get("source", {}) or relative in inventory_by_category.get("tests", {}) or relative in inventory_by_category.get("contracts", {}) or relative in inventory_by_category.get("lockfiles", {}), f"regression ring file is not inventoried: {relative}", errors)
        planned_ids = ring.get("planned_test_ids")
        require(isinstance(planned_ids, list) and bool(planned_ids), f"regression ring has no planned tests: {ring_name}", errors)
        for test_id in planned_ids if isinstance(planned_ids, list) else []:
            test = test_map.get(test_id)
            require(test is not None, f"regression ring maps unknown planned test: {test_id}", errors)
            if test is not None:
                require("regression-ring" in test.get("layers", []), f"regression ring test lacks regression-ring layer: {test_id}", errors)
    return test_map


def validate_matrix_risks(
    manifest: dict[str, Any],
    matrix: dict[str, Any],
    test_map: dict[str, dict[str, Any]],
    executions: list[dict[str, Any]],
    records_schema: dict[str, Any],
    errors: list[str],
) -> None:
    verdict = manifest.get("final_verdict")
    execution_by_id = {item.get("execution_id"): item for item in executions if isinstance(item.get("execution_id"), str)}
    selected_ranks = [
        LAYER_ORDER[item["layer"]]
        for item in executions
        if item.get("selected_execution") is True and item.get("layer") in LAYER_ORDER
    ]
    require(selected_ranks == sorted(selected_ranks), "selected executions are out of layer order", errors)

    reliably_failed = any(
        item.get("reliable") is True
        and item.get("exit_code") != 0
        and item.get("selected_execution") is True
        for item in executions
    )
    if verdict == "TEST_FAIL":
        require(reliably_failed, "TEST_FAIL lacks a reliable reproduced failing execution", errors)

    for behavior in matrix.get("behaviors", []):
        if not isinstance(behavior, dict):
            continue
        behavior_id = behavior.get("id")
        risks = behavior.get("risks")
        if not isinstance(risks, dict):
            continue
        require(risks.get("functional", {}).get("status") != "not_applicable", f"behavior functional risk cannot be N/A: {behavior_id}", errors)
        for risk_name in RISK_KEYS:
            cell = risks.get(risk_name)
            if not isinstance(cell, dict):
                continue
            status = cell.get("status")
            na = cell.get("not_applicable")
            if status == "applicable":
                require(na is None, f"applicable behavior risk cannot be N/A: {behavior_id}/{risk_name}", errors)
                mapped_tests = cell.get("test_ids")
                mapped_executions = cell.get("execution_ids")
                require(isinstance(mapped_tests, list) and bool(mapped_tests), f"behavior risk has no test mapping: {behavior_id}/{risk_name}", errors)
                require(isinstance(mapped_executions, list) and bool(mapped_executions), f"behavior risk has no receipt mapping: {behavior_id}/{risk_name}", errors)
                for test_id in mapped_tests if isinstance(mapped_tests, list) else []:
                    require(test_id in test_map, f"behavior maps unknown planned test: {behavior_id}/{test_id}", errors)
                    if test_id in test_map:
                        require(behavior_id in test_map[test_id].get("behavior_ids", []), f"behavior test mapping is not bidirectional: {behavior_id}/{test_id}", errors)
                for execution_id in mapped_executions if isinstance(mapped_executions, list) else []:
                    receipt = execution_by_id.get(execution_id)
                    require(receipt is not None, f"behavior maps unknown execution: {behavior_id}/{execution_id}", errors)
                    if receipt is not None:
                        require(any(test_id in receipt.get("test_ids", []) for test_id in mapped_tests or []), f"behavior receipt did not run a mapped test: {behavior_id}/{risk_name}", errors)
                        if verdict == "TEST_PASS":
                            require(receipt.get("selected_execution") is True and receipt.get("reliable") is True and receipt.get("exit_code") == 0, f"TEST_PASS behavior maps a non-passing receipt: {behavior_id}/{risk_name}", errors)
            elif status == "not_applicable":
                require(cell.get("test_ids") == [] and cell.get("execution_ids") == [], f"N/A risk must not map tests or receipts: {behavior_id}/{risk_name}", errors)
                structured_na(na, records_schema, f"behavior {behavior_id} {risk_name} not_applicable", errors, risk_name)
            elif status == "unresolved":
                require(na is None, f"unresolved risk cannot also be N/A: {behavior_id}/{risk_name}", errors)
                if verdict == "TEST_PASS":
                    errors.append(f"TEST_PASS has unresolved behavior risk: {behavior_id}/{risk_name}")


def is_volatile_snapshot_path(root: Path, candidate: Path, evidence_root: Path) -> bool:
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return True
    if any(part in SNAPSHOT_VOLATILE_NAMES for part in relative.parts):
        return True
    if any(relative == Path(prefix) or Path(prefix) in relative.parents for prefix in SNAPSHOT_VOLATILE_ROOTS):
        return True
    resolved = candidate.resolve()
    excluded = evidence_root.resolve()
    return resolved == excluded or excluded in resolved.parents


def tree_sha256(root: Path, evidence_root: Path) -> str:
    entries: list[dict[str, str]] = []
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file() or is_volatile_snapshot_path(root, candidate, evidence_root):
            continue
        entries.append({"path": candidate.relative_to(root).as_posix(), "sha256": file_sha256(candidate)})
    return canonical_sha256(entries)


def require_sha_or_null(value: Any, location: str, errors: list[str]) -> None:
    require(value is None or is_sha256(value), f"{location} must be a sha256 or null", errors)


def validate_differential_proofs(
    root: Path,
    project_root: Path,
    manifest: dict[str, Any],
    matrix: dict[str, Any],
    proof: dict[str, Any],
    differential_requests: dict[str, dict[str, Any]],
    executions: list[dict[str, Any]],
    entry_map: dict[str, dict[str, Any]],
    records_schema: dict[str, Any],
    errors: list[str],
) -> None:
    verdict = manifest.get("final_verdict")
    receipts = {item.get("execution_id"): item for item in executions if isinstance(item.get("execution_id"), str)}
    behavior_ids = {item.get("id") for item in matrix.get("behaviors", []) if isinstance(item, dict)}
    proof_by_behavior: dict[str, dict[str, Any]] = {}
    live_tree_hash = tree_sha256(project_root, root)
    proofs = proof.get("proofs")
    if not isinstance(proofs, list):
        return
    for item in proofs:
        if not isinstance(item, dict):
            continue
        behavior_id = item.get("behavior_id")
        require(behavior_id in behavior_ids, f"differential proof maps unknown behavior: {behavior_id}", errors)
        require(behavior_id not in proof_by_behavior, f"duplicate differential proof: {behavior_id}", errors)
        if isinstance(behavior_id, str):
            proof_by_behavior[behavior_id] = item
        classification = item.get("classification")
        if classification == "NOT_APPLICABLE":
            structured_na(item.get("not_applicable"), records_schema, f"differential proof {behavior_id} not_applicable", errors)
            for key in (
                "method", "differential_request_path", "differential_request_sha256", "baseline_commit",
                "current_tree_sha256", "baseline_execution_id", "mutation_execution_id", "current_execution_id",
                "project_tree_before_sha256", "project_tree_after_sha256", "isolation_tree_sha256",
                "mutation_apply_sha256", "mutation_restore_sha256",
            ):
                require(item.get(key) is None, f"N/A differential proof must clear {key}: {behavior_id}", errors)
            require(item.get("failure_reason_matched") is False, f"N/A differential proof cannot claim a failure match: {behavior_id}", errors)
            continue

        request_relative = item.get("differential_request_path")
        request = differential_requests.get(request_relative) if isinstance(request_relative, str) else None
        require(request is not None, f"differential proof has no matching request: {behavior_id}", errors)
        request_path = require_manifest_entry(request_relative, entry_map, root, errors, "differential request") if isinstance(request_relative, str) else None
        if request_path is not None:
            require(file_sha256(request_path) == item.get("differential_request_sha256"), f"differential request hash mismatch: {behavior_id}", errors)
        if not isinstance(request, dict):
            continue
        require(request.get("behavior_id") == behavior_id, f"differential request behavior mismatch: {behavior_id}", errors)
        method = item.get("method")
        require(method == request.get("method") and method in {"baseline", "controlled-mutation"}, f"differential method mismatch: {behavior_id}", errors)
        require(item.get("baseline_commit") == request.get("baseline_commit") == manifest.get("baseline_commit"), f"differential baseline commit mismatch: {behavior_id}", errors)
        require(item.get("current_tree_sha256") == request.get("current_tree_sha256") == live_tree_hash, f"differential current tree hash mismatch: {behavior_id}", errors)
        for key in (
            "differential_request_sha256", "current_tree_sha256", "project_tree_before_sha256",
            "project_tree_after_sha256", "isolation_tree_sha256", "mutation_apply_sha256", "mutation_restore_sha256",
        ):
            require_sha_or_null(item.get(key), f"differential proof {behavior_id}.{key}", errors)
        require(item.get("project_tree_before_sha256") == live_tree_hash, f"differential project tree before mismatch: {behavior_id}", errors)
        require(item.get("project_tree_after_sha256") == live_tree_hash, f"differential project tree after mismatch: {behavior_id}", errors)
        require(item.get("cleanup_succeeded") is True, f"differential cleanup failed: {behavior_id}", errors)

        current = receipts.get(item.get("current_execution_id"))
        require(current is not None, f"differential current receipt is missing: {behavior_id}", errors)
        failing_id = item.get("baseline_execution_id") if method == "baseline" else item.get("mutation_execution_id")
        failing = receipts.get(failing_id)
        require(failing is not None, f"differential failing receipt is missing: {behavior_id}", errors)
        if current is not None and failing is not None:
            require(current.get("request_sha256") == failing.get("request_sha256"), f"differential sides use different execution requests: {behavior_id}", errors)
            nested = request.get("execution_request")
            current_request_path = current.get("request_path")
            current_request = load_json(root / current_request_path) if isinstance(current_request_path, str) and safe_path(root, current_request_path, errors, "differential receipt request") else None
            require(current_request == nested, f"differential current receipt request does not match request: {behavior_id}", errors)
            require(current.get("selected_execution") is True and current.get("reliable") is True and current.get("exit_code") == 0, f"differential current side is not a reliable success: {behavior_id}", errors)
            require(failing.get("selected_execution") is False and failing.get("reliable") is True and failing.get("exit_code") != 0, f"differential failing side is not a reliable failure: {behavior_id}", errors)
            current_isolation = current.get("isolation")
            failing_isolation = failing.get("isolation")
            require(isinstance(current_isolation, dict) and current_isolation.get("kind") == "current", f"differential current receipt lacks current isolation: {behavior_id}", errors)
            require(isinstance(failing_isolation, dict) and failing_isolation.get("kind") == method, f"differential failing receipt isolation mismatch: {behavior_id}", errors)
            if isinstance(current_isolation, dict):
                require(current_isolation.get("tree_sha256") == item.get("isolation_tree_sha256") == live_tree_hash, f"differential current isolation hash mismatch: {behavior_id}", errors)
            if method == "baseline" and isinstance(failing_isolation, dict):
                require(failing_isolation.get("baseline_commit") == request.get("baseline_commit"), f"baseline receipt commit mismatch: {behavior_id}", errors)
            if method == "controlled-mutation" and isinstance(failing_isolation, dict):
                patch_relative = request.get("mutation_patch_path")
                patch_path = require_manifest_entry(patch_relative, entry_map, root, errors, "controlled mutation patch") if isinstance(patch_relative, str) else None
                require(patch_path is not None, f"controlled mutation patch is missing: {behavior_id}", errors)
                if patch_path is not None:
                    patch_hash = file_sha256(patch_path)
                    require(failing_isolation.get("patch_sha256") == patch_hash, f"controlled mutation receipt patch hash mismatch: {behavior_id}", errors)
                require(item.get("mutation_apply_sha256") == failing_isolation.get("tree_sha256"), f"controlled mutation apply hash mismatch: {behavior_id}", errors)
                require(item.get("mutation_restore_sha256") == item.get("isolation_tree_sha256"), f"controlled mutation restore hash mismatch: {behavior_id}", errors)
        if method == "baseline":
            require(item.get("mutation_execution_id") is None, f"baseline proof has mutation receipt: {behavior_id}", errors)
            require(request.get("mutation_patch_path") is None, f"baseline request has mutation patch: {behavior_id}", errors)
            require(item.get("mutation_apply_sha256") is None and item.get("mutation_restore_sha256") is None, f"baseline proof has mutation hashes: {behavior_id}", errors)
        elif method == "controlled-mutation":
            require(item.get("baseline_execution_id") is None, f"mutation proof has baseline receipt: {behavior_id}", errors)
            require(isinstance(request.get("mutation_patch_path"), str) and bool(request.get("mutation_patch_path")), f"mutation request lacks patch: {behavior_id}", errors)
        if classification == "PROVEN":
            require(item.get("failure_reason_matched") is True, f"differential failure reason was not matched: {behavior_id}", errors)
            if failing is not None:
                output = b""
                for key in ("stdout_path", "stderr_path"):
                    relative = failing.get(key)
                    path = safe_path(root, relative, errors, "differential raw output") if isinstance(relative, str) else None
                    if path is not None and path.is_file():
                        output += path.read_bytes()
                signals = request.get("expected_failure_signals")
                require(isinstance(signals, list) and any(isinstance(signal, str) and signal.encode() in output for signal in signals), f"differential expected failure signal is absent: {behavior_id}", errors)
        elif classification == "UNPROVEN" and verdict == "TEST_PASS":
            errors.append(f"TEST_PASS has unproven necessary behavior: {behavior_id}")

    if verdict == "TEST_PASS":
        for behavior_id in behavior_ids:
            require(behavior_id in proof_by_behavior, f"behavior lacks differential proof: {behavior_id}", errors)


def validate_infrastructure(
    manifest: dict[str, Any],
    infrastructure: dict[str, Any],
    executions: list[dict[str, Any]],
    entry_map: dict[str, dict[str, Any]],
    root: Path,
    errors: list[str],
) -> None:
    verdict = manifest.get("final_verdict")
    require(infrastructure.get("cleanup_succeeded") is True or verdict == "TEST_BLOCKED", "infrastructure cleanup did not succeed", errors)
    external_targets = infrastructure.get("external_targets")
    validate_external_targets(external_targets, "infrastructure external_targets", errors)
    declared = {canonical_sha256(item) for item in external_targets if isinstance(item, dict)} if isinstance(external_targets, list) else set()
    for receipt in executions:
        for target in receipt.get("external_targets", []):
            if isinstance(target, dict):
                require(canonical_sha256(target) in declared, f"receipt external target is absent from infrastructure: {target.get('name')}", errors)
    snapshots = infrastructure.get("contract_snapshots")
    require(isinstance(snapshots, list), "contract snapshot provenance is missing", errors)
    for record in snapshots if isinstance(snapshots, list) else []:
        if not isinstance(record, dict):
            continue
        relative = record.get("path")
        require(isinstance(relative, str) and path_under(relative, "contracts"), "contract snapshot must be under contracts/", errors)
        path = require_manifest_entry(relative, entry_map, root, errors, "contract snapshot") if isinstance(relative, str) else None
        if path is not None:
            require(file_sha256(path) == record.get("sha256"), f"contract snapshot hash/provenance mismatch: {relative}", errors)


def validate_lightweight(
    manifest: dict[str, Any],
    record: dict[str, Any],
    executions: list[dict[str, Any]],
    errors: list[str],
) -> None:
    execution_by_id = {item.get("execution_id"): item for item in executions if isinstance(item.get("execution_id"), str)}
    checks = record.get("checks")
    require(isinstance(checks, list) and bool(checks), "lightweight deterministic checks are missing", errors)
    for check in checks if isinstance(checks, list) else []:
        if not isinstance(check, dict):
            continue
        receipt = execution_by_id.get(check.get("execution_id"))
        require(receipt is not None and receipt.get("selected_execution") is True and receipt.get("reliable") is True and receipt.get("exit_code") == 0, "lightweight check lacks a successful deterministic receipt", errors)
    if manifest.get("final_verdict") == "TEST_PASS":
        require(record.get("runtime_behavior_claimed") is False, "lightweight TEST_PASS must not claim runtime behavior", errors)


def validate_verdict_and_attestation(
    root: Path,
    manifest: dict[str, Any],
    verdict_record: dict[str, Any],
    validation: dict[str, Any],
    report: str,
    entry_map: dict[str, dict[str, Any]],
    executions: list[dict[str, Any]],
    records_schema: dict[str, Any],
    errors: list[str],
    verify_attestation: bool,
) -> None:
    validate_definition(verdict_record, "verdict", records_schema, "verdict", errors)
    verdict = manifest.get("final_verdict")
    require(verdict in VERDICTS and verdict_record.get("verdict") == verdict, "verdict record does not match manifest", errors)
    require(verdict_record.get("testing_domain_only") is True, "verdict exceeds testing-domain responsibility", errors)
    require(verdict_record.get("authorizes_commit_or_release") is False, "test verdict must not authorize commit or release", errors)
    require(verdict_record.get("real_environment_validated") is False, "code evidence must not claim real-environment validation", errors)
    require(verdict_record.get("repairs_business_defects") is False, "test skill must not repair business defects", errors)
    if verdict == "TEST_PASS":
        require(verdict_record.get("code_evidence_replayable") is True, "TEST_PASS must declare replayable code evidence", errors)
        require(not verdict_record.get("blockers"), "TEST_PASS contains blockers", errors)
        require(not verdict_record.get("reproduced_failures"), "TEST_PASS contains reproduced failures", errors)
    elif verdict == "TEST_BLOCKED":
        require(bool(verdict_record.get("blockers")), "TEST_BLOCKED lacks blocker reasons", errors)
    elif verdict == "TEST_FAIL":
        require(bool(verdict_record.get("reproduced_failures")), "TEST_FAIL lacks reproduced failures", errors)

    if verify_attestation:
        validate_definition(validation, "validation", records_schema, "validation", errors)
        payload = sorted(
            ({"path": path, "sha256": entry["sha256"]} for path, entry in entry_map.items() if path not in FINAL_RECORDS),
            key=lambda item: item["path"],
        )
        replayed_ids = [
            item.get("execution_id") for item in executions
            if isinstance(item.get("execution_id"), str) and isinstance(item.get("replay_of"), str)
        ]
        require(validation.get("validator") == "validate_test_evidence.py", "validation attestation names wrong validator", errors)
        require(validation.get("validator_sha256") == file_sha256(Path(__file__).resolve()), "validation attestation validator hash mismatch", errors)
        require(validation.get("payload_sha256") == canonical_sha256(payload), "validation attestation payload hash mismatch", errors)
        require(validation.get("result") == "passed", "validation attestation is not passed", errors)
        require(validation.get("verdict") == verdict, "validation attestation verdict mismatch", errors)
        require(validation.get("semantics") == "integrity-and-protocol-validation-not-hostile-producer-proof", "validation attestation semantics exceed integrity/protocol validation", errors)
        require(validation.get("replay_receipt_ids") == replayed_ids, "validation replay receipt IDs do not match actual replay executions", errors)

    fragments = [
        f"Verdict: {verdict}", f"Evidence ID: {manifest.get('evidence_id')}",
        "Derived from structured evidence", "sensitivity=project-controlled",
        "project owns access control, retention, and upload policy",
        "Mocked code-level evidence does not verify a real deployed environment",
        "legacy test-report interface is not supported",
    ]
    for fragment in fragments:
        require(fragment in report, f"derived report missing authoritative evidence fragment: {fragment}", errors)


def validate_evidence(
    root: Path,
    project_root: Path,
    ignored_hash_paths: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    try:
        manifest = load_json(root / "manifest.json")
        classification = load_json(root / "change-classification.json")
        scope = load_json(root / "scope.json")
        inventory = load_json(root / "target-inventory.json")
        verdict_record = load_json(root / "verdict.json")
        validation = load_json(root / "validation.json")
        report = (root / "test-report.md").read_text(encoding="utf-8")
        manifest_schema = load_schema("evidence-manifest.schema.json")
        records_schema = load_schema("authoritative-records.schema.json")
        matrix_schema = load_schema("behavior-risk-matrix.schema.json")
    except (EvidenceError, FileNotFoundError) as exc:
        return [str(exc)]
    if not all(isinstance(item, dict) for item in (manifest, classification, scope, inventory, verdict_record, validation)):
        return ["structured evidence records must be JSON objects"]

    entry_map = validate_manifest(root, manifest, manifest_schema, records_schema, errors, ignored_hash_paths)
    change_class = manifest.get("change_class")
    required = COMMON_RECORDS | (BEHAVIOR_RECORDS if change_class == "behavior" else LIGHTWEIGHT_RECORDS)
    for relative in required:
        require(relative in entry_map, f"required evidence record not hashed: {relative}", errors)
    validate_definition(classification, "changeClassification", records_schema, "change-classification", errors)
    validate_definition(scope, "scope", records_schema, "scope", errors)
    validate_definition(inventory, "targetInventory", records_schema, "target-inventory", errors)
    require(classification.get("classification") == change_class, "change classification does not match manifest", errors)
    require(classification.get("full_protocol_required") is (change_class == "behavior"), "change classification protocol decision is inconsistent", errors)

    plan: dict[str, Any] | None = None
    if change_class == "behavior":
        try:
            plan = load_json(root / "test-plan.json")
        except EvidenceError as exc:
            errors.append(str(exc))
        if isinstance(plan, dict):
            validate_definition(plan, "testPlan", records_schema, "test-plan", errors)
        else:
            errors.append("test-plan.json must be an object")
            plan = None

    inventory_by_category, _ = validate_inventory(root, project_root, manifest, inventory, scope, plan, entry_map, errors)
    require(manifest.get("evidence_id_inputs", {}).get("scope_sha256") == canonical_sha256(scope), "scope identity hash mismatch", errors)
    validate_scope(scope, inventory, inventory_by_category, project_root, root, errors)
    execution_requests, differential_requests, executions = validate_requests_and_receipts(root, entry_map, records_schema, errors)

    if change_class == "behavior":
        try:
            matrix = load_json(root / "behavior-risk-matrix.json")
            infrastructure = load_json(root / "infrastructure-changes.json")
            proof = load_json(root / "differential-proof.json")
        except EvidenceError as exc:
            errors.append(str(exc))
            matrix = infrastructure = proof = None
        if all(isinstance(item, dict) for item in (matrix, infrastructure, proof, plan)):
            validate_schema(matrix, matrix_schema, matrix_schema, "behavior-risk-matrix", errors)
            validate_definition(infrastructure, "infrastructureChanges", records_schema, "infrastructure-changes", errors)
            validate_definition(proof, "differentialProof", records_schema, "differential-proof", errors)
            stages = {item.get("name"): item for item in manifest.get("stages", []) if isinstance(item, dict)}
            for stage_name in CORE_BEHAVIOR_STAGES:
                require(stages.get(stage_name, {}).get("status") == "complete", f"behavior protocol stage cannot be N/A: {stage_name}", errors)
            test_map = validate_plan_and_scope_bindings(
                root, project_root, manifest, scope, matrix, plan, inventory_by_category, entry_map,
                executions, records_schema, errors,
            )
            validate_matrix_risks(manifest, matrix, test_map, executions, records_schema, errors)
            validate_differential_proofs(
                root, project_root, manifest, matrix, proof, differential_requests, executions,
                entry_map, records_schema, errors,
            )
            validate_infrastructure(manifest, infrastructure, executions, entry_map, root, errors)
        else:
            errors.append("behavior evidence records must be JSON objects")
    elif change_class == "lightweight":
        try:
            lightweight = load_json(root / "lightweight-verification.json")
        except EvidenceError as exc:
            errors.append(str(exc))
            lightweight = None
        if isinstance(lightweight, dict):
            validate_definition(lightweight, "lightweightVerification", records_schema, "lightweight-verification", errors)
            validate_lightweight(manifest, lightweight, executions, errors)
        else:
            errors.append("lightweight-verification.json must be an object")
    else:
        errors.append("invalid change_class")

    validate_verdict_and_attestation(
        root, manifest, verdict_record, validation, report, entry_map, executions, records_schema,
        errors, verify_attestation=not bool(ignored_hash_paths),
    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a PrizmKit test evidence package")
    parser.add_argument("--evidence-dir", required=True, help="Path to .prizmkit/test/evidence/<evidence-id>")
    parser.add_argument("--project-root", help="Target project root; defaults to four parents above evidence directory")
    parser.add_argument("--attest", action="store_true", help="Validate payload, then atomically refresh the validator-owned attestation and final hashes")
    args = parser.parse_args()
    root = Path(args.evidence_dir).resolve()
    if not root.is_dir():
        print(f"Test evidence validation: FAIL\n- evidence directory not found: {root}")
        return 1
    try:
        project_root = Path(args.project_root).resolve() if args.project_root else root.parents[3]
    except IndexError:
        print("Test evidence validation: FAIL\n- cannot infer project root from evidence directory")
        return 1
    errors = validate_evidence(root, project_root, FINAL_RECORDS if args.attest else None)
    if errors:
        print("Test evidence validation: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    manifest = load_json(root / "manifest.json")
    if args.attest:
        executions = load_json(root / "executions.json")
        replayed_ids = [
            item.get("execution_id") for item in executions
            if isinstance(item, dict)
            and isinstance(item.get("execution_id"), str)
            and isinstance(item.get("replay_of"), str)
        ] if isinstance(executions, list) else []
        payload = sorted(
            (
                {"path": entry["path"], "sha256": entry["sha256"]}
                for entry in manifest["files"] if entry["path"] not in FINAL_RECORDS
            ),
            key=lambda item: item["path"],
        )
        validation = {
            "validator": "validate_test_evidence.py",
            "validator_sha256": file_sha256(Path(__file__).resolve()),
            "payload_sha256": canonical_sha256(payload),
            "result": "passed",
            "verdict": manifest["final_verdict"],
            "semantics": "integrity-and-protocol-validation-not-hostile-producer-proof",
            "replay_receipt_ids": replayed_ids,
        }
        atomic_write_json(root / "validation.json", validation)
        for entry in manifest["files"]:
            if entry["path"] in FINAL_RECORDS:
                entry["sha256"] = file_sha256(root / entry["path"])
        atomic_write_json(root / "manifest.json", manifest)
        errors = validate_evidence(root, project_root)
        if errors:
            print("Test evidence validation: FAIL")
            for error in errors:
                print(f"- {error}")
            return 1

    print("Test evidence validation: PASS")
    print(f"Evidence ID: {manifest['evidence_id']}")
    print(f"Verdict: {manifest['final_verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
