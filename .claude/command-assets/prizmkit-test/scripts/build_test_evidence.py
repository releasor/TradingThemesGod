#!/usr/bin/env python3
"""Build runner-generated PrizmKit test evidence from schema-shaped requests.

Usage:
  python3 build_test_evidence.py --project-root ROOT --evidence-dir DIR inventory --request REQUEST
  python3 build_test_evidence.py --project-root ROOT --evidence-dir DIR execute --request REQUEST
  python3 build_test_evidence.py --project-root ROOT --evidence-dir DIR execute --replay-receipt RECEIPT
  python3 build_test_evidence.py --project-root ROOT --evidence-dir DIR differential --request REQUEST
  python3 build_test_evidence.py --project-root ROOT --evidence-dir DIR resume --manifest MANIFEST --inventory INVENTORY

Only locator arguments and evidence mechanics are fixed. Test commands, working directories,
timeouts, attempts, concurrency, tool probes, test layers, and framework-specific options come
from model-authored requests after project inspection.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

STAGES = [
    "CHANGE_CLASSIFY", "SCOPE_DISCOVER", "CONTRACT_MODEL", "TEST_PLAN",
    "INFRA_READY", "TEST_BUILD", "EXECUTE_PROVE", "EVIDENCE_PACKAGE",
    "EVIDENCE_VALIDATE",
]
CATEGORIES = ("source", "tests", "contracts", "lockfiles")
BLOCKED_EXTERNAL_CLASSES = {"production", "unknown"}
SNAPSHOT_VOLATILE_ROOTS = (
    ".prizmkit/state",
    ".prizmkit/test/evidence",
    ".claude/worktrees",
)
SNAPSHOT_VOLATILE_NAMES = {".git", "__pycache__"}


class RequestError(Exception):
    """Raised when a request would produce unsafe or ambiguous evidence."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RequestError(f"file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RequestError(f"invalid JSON: {path}: {exc}") from exc


def confined(root: Path, value: str, *, must_exist: bool = False, directory: bool = False) -> Path:
    if not isinstance(value, str) or not value:
        raise RequestError("path must be a non-empty string")
    candidate = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise RequestError(f"path escapes root: {value}") from exc
    if must_exist and not candidate.exists():
        raise RequestError(f"path does not exist: {value}")
    if directory and candidate.exists() and not candidate.is_dir():
        raise RequestError(f"path is not a directory: {value}")
    return candidate


def evidence_relative(evidence_dir: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(evidence_dir.resolve()).as_posix()
    except ValueError as exc:
        raise RequestError(f"evidence output escapes evidence directory: {path}") from exc


def request_file(evidence_dir: Path, value: str) -> Path:
    return confined(evidence_dir, value, must_exist=True)


def receipt_file(evidence_dir: Path, value: str) -> Path:
    direct = confined(evidence_dir, value)
    if direct.is_file():
        return direct
    return confined(evidence_dir, f"receipts/{value}", must_exist=True)


def ensure_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RequestError(f"{label} must be an object")
    return value


def ensure_string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise RequestError(f"{label} must be a{' non-empty' if not allow_empty else ''} string array")
    if any(not isinstance(item, str) or not item for item in value):
        raise RequestError(f"{label} contains a non-string or empty value")
    return value


def validate_external_targets(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RequestError("external_targets must be an array")
    for target in value:
        if not isinstance(target, dict):
            raise RequestError("external target must be an object")
        required = {"name", "external", "classification", "endpoint_evidence", "allow_evidence", "deny_evidence"}
        if set(target) != required:
            raise RequestError(f"external target fields must be exactly {sorted(required)}")
        if not isinstance(target["external"], bool):
            raise RequestError("external target external flag must be boolean")
        for key in ("endpoint_evidence", "allow_evidence", "deny_evidence"):
            ensure_string_list(target[key], f"external target {key}", allow_empty=(key != "endpoint_evidence"))
        if target["external"] and target["classification"] in BLOCKED_EXTERNAL_CLASSES:
            raise RequestError(f"execution blocked for external target classified {target['classification']}: {target['name']}")
        if target["external"] and target["classification"] not in {"isolated", "test", "staging"}:
            raise RequestError(f"invalid external target classification: {target['classification']}")
        if target["external"] and not target["allow_evidence"]:
            raise RequestError(f"external target lacks explicit allow evidence: {target['name']}")
        if target["external"] and target["deny_evidence"]:
            raise RequestError(f"external target matched deny evidence: {target['name']}")
    return value


def validate_execution_request(request: Any) -> dict[str, Any]:
    request = ensure_object(request, "execution request")
    required = {
        "request_version", "purpose", "command", "cwd", "environment",
        "tool_version_commands", "layer", "test_ids", "external_targets",
    }
    optional = {"timeout_seconds", "attempt_policy", "concurrency"}
    if not required <= set(request) or set(request) - required - optional:
        raise RequestError(f"execution request fields must contain {sorted(required)} and only supported optional fields")
    if request["request_version"] != "1.0":
        raise RequestError("unsupported execution request version")
    command = ensure_string_list(request["command"], "command", allow_empty=False)
    if not command[0]:
        raise RequestError("command executable is empty")
    if not isinstance(request["cwd"], str):
        raise RequestError("cwd must be a string")
    environment = ensure_object(request["environment"], "environment")
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in environment.items()):
        raise RequestError("environment must contain string keys and complete string values")
    probes = ensure_object(request["tool_version_commands"], "tool_version_commands")
    for name, probe in probes.items():
        if not isinstance(name, str):
            raise RequestError("tool probe names must be strings")
        ensure_string_list(probe, f"tool probe {name}", allow_empty=False)
    ensure_string_list(request["test_ids"], "test_ids")
    validate_external_targets(request["external_targets"])
    if "timeout_seconds" in request and (isinstance(request["timeout_seconds"], bool) or not isinstance(request["timeout_seconds"], (int, float)) or request["timeout_seconds"] <= 0):
        raise RequestError("timeout_seconds must be a positive number")
    return request


def is_volatile_snapshot_path(root: Path, candidate: Path, excluded: list[Path] | None = None) -> bool:
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return True
    if any(part in SNAPSHOT_VOLATILE_NAMES for part in relative.parts):
        return True
    if any(relative == Path(prefix) or Path(prefix) in relative.parents for prefix in SNAPSHOT_VOLATILE_ROOTS):
        return True
    resolved = candidate.resolve()
    return any(resolved == item.resolve() or item.resolve() in resolved.parents for item in (excluded or []))


def tree_sha256(root: Path, excluded: list[Path] | None = None) -> str:
    entries: list[dict[str, str]] = []
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file() or is_volatile_snapshot_path(root, candidate, excluded):
            continue
        entries.append({"path": candidate.relative_to(root).as_posix(), "sha256": file_sha256(candidate)})
    return canonical_sha256(entries)


def collect_matches(project_root: Path, patterns: list[str], exclusions: set[str]) -> list[dict[str, str]]:
    paths: set[Path] = set()
    for pattern in patterns:
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise RequestError(f"inventory pattern is not project-relative: {pattern}")
        for candidate in project_root.glob(pattern):
            if candidate.is_file():
                paths.add(candidate.resolve())
    entries = []
    for candidate in sorted(paths):
        relative = candidate.relative_to(project_root).as_posix()
        if relative not in exclusions:
            entries.append({"path": relative, "sha256": file_sha256(candidate)})
    return entries


def enumerate_module_root_files(
    project_root: Path,
    evidence_dir: Path,
    module_roots: list[str],
) -> dict[str, list[str]]:
    evidence_resolved = evidence_dir.resolve()
    result: dict[str, list[str]] = {}
    for relative in module_roots:
        root = confined(project_root, relative, must_exist=True)
        candidates = [root] if root.is_file() else root.rglob("*")
        files: list[str] = []
        for candidate in candidates:
            if not candidate.is_file() or ".git" in candidate.parts or "__pycache__" in candidate.parts:
                continue
            resolved = candidate.resolve()
            if resolved == evidence_resolved or evidence_resolved in resolved.parents:
                continue
            files.append(resolved.relative_to(project_root).as_posix())
        result[relative] = sorted(files)
    return result


def run_inventory(project_root: Path, evidence_dir: Path, request_path: Path, output_name: str) -> Path:
    request = ensure_object(load_json(request_path), "inventory request")
    required = {"request_version", "categories", "changed_files", "module_roots", "exclusions", "discovery_evidence", "plan_inputs"}
    if set(request) != required or request["request_version"] != "1.0":
        raise RequestError(f"inventory request fields must be exactly {sorted(required)} with version 1.0")
    categories = ensure_object(request["categories"], "inventory categories")
    if set(categories) != set(CATEGORIES):
        raise RequestError(f"inventory categories must be exactly {list(CATEGORIES)}")
    exclusions = request["exclusions"]
    if not isinstance(exclusions, list):
        raise RequestError("inventory exclusions must be an array")
    exclusion_paths: set[str] = set()
    for exclusion in exclusions:
        if not isinstance(exclusion, dict) or set(exclusion) != {"path", "reason", "evidence"}:
            raise RequestError("each inventory exclusion requires path, reason, and evidence")
        confined(project_root, exclusion["path"])
        if not isinstance(exclusion["reason"], str) or len(exclusion["reason"].strip()) < 8:
            raise RequestError("inventory exclusion reason is too short")
        if not isinstance(exclusion["evidence"], list) or not exclusion["evidence"]:
            raise RequestError("inventory exclusion lacks evidence")
        exclusion_paths.add(Path(exclusion["path"]).as_posix())
    changed_files = ensure_string_list(request["changed_files"], "changed_files", allow_empty=False)
    module_roots = ensure_string_list(request["module_roots"], "module_roots", allow_empty=False)
    for relative in changed_files:
        confined(project_root, relative, must_exist=relative not in exclusion_paths)
    for relative in module_roots:
        confined(project_root, relative, must_exist=True)
    output_categories = {
        name: collect_matches(project_root, ensure_string_list(categories[name], f"category {name}"), exclusion_paths)
        for name in CATEGORIES
    }
    inventoried_paths = {
        entry["path"]
        for entries in output_categories.values()
        for entry in entries
    }
    module_root_files = enumerate_module_root_files(project_root, evidence_dir, module_roots)
    missing_from_inventory = sorted({
        relative
        for files in module_root_files.values()
        for relative in files
        if relative not in inventoried_paths and relative not in exclusion_paths
    })
    if missing_from_inventory:
        raise RequestError(
            "module root contains files that are neither inventoried nor excluded: "
            + ", ".join(missing_from_inventory[:20])
        )
    output = {
        "inventory_request_path": evidence_relative(evidence_dir, request_path),
        "inventory_request_sha256": file_sha256(request_path),
        "categories": output_categories,
        "changed_files": changed_files,
        "module_roots": module_roots,
        "module_root_files": module_root_files,
        "exclusions": sorted(exclusion_paths),
        "discovery_evidence": request["discovery_evidence"],
        "plan_inputs": ensure_object(request["plan_inputs"], "plan_inputs"),
    }
    output_path = confined(evidence_dir, output_name)
    write_json_atomic(output_path, output)
    return output_path


def run_process(argv: list[str], cwd: Path, environment: dict[str, str], timeout: float | None) -> tuple[int, bytes, bytes]:
    creationflags = 0
    process_kwargs: dict[str, Any] = {}
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        process_kwargs["start_new_session"] = True
    process = subprocess.Popen(
        argv, cwd=cwd, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=creationflags, **process_kwargs,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=1)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        stdout, stderr = process.communicate()
        return 124, stdout, stderr + f"\nPrizmKit runner timeout after {timeout} seconds\n".encode()


def run_probe(argv: list[str], cwd: Path, environment: dict[str, str], timeout: float | None) -> dict[str, Any]:
    try:
        exit_code, stdout, stderr = run_process(argv, cwd, environment, timeout)
        return {
            "command": argv, "exit_code": exit_code,
            "stdout": stdout.decode(errors="replace"), "stderr": stderr.decode(errors="replace"),
        }
    except OSError as exc:
        return {"command": argv, "error": str(exc)}


def append_receipt(evidence_dir: Path, receipt: dict[str, Any]) -> None:
    receipt_path = evidence_dir / "receipts" / f"{receipt['execution_id']}.json"
    if receipt_path.exists():
        raise RequestError(f"receipt already exists: {receipt_path.name}")
    write_json_atomic(receipt_path, receipt)
    path = evidence_dir / "executions.json"
    existing: Any = load_json(path) if path.exists() else []
    if not isinstance(existing, list):
        raise RequestError("executions.json must remain an array")
    previous = canonical_sha256(existing[-1]) if existing else None
    if receipt["previous_receipt_sha256"] != previous:
        raise RequestError("receipt chain mismatch")
    existing.append(receipt)
    write_json_atomic(path, existing)


def ensure_runner_snapshot(evidence_dir: Path) -> tuple[str, str]:
    source = Path(__file__).resolve()
    digest = file_sha256(source)
    relative = f"runner/build_test_evidence-{digest}.py"
    destination = evidence_dir / relative
    if destination.exists():
        if file_sha256(destination) != digest:
            raise RequestError("archived runner snapshot hash mismatch")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return relative, digest


def execute_request(
    project_root: Path,
    evidence_dir: Path,
    request_path: Path,
    *,
    execution_root: Path | None = None,
    replay_of: str | None = None,
    isolation: dict[str, Any] | None = None,
    selected_execution: bool = True,
) -> dict[str, Any]:
    request = validate_execution_request(load_json(request_path))
    root = execution_root or project_root
    cwd = confined(root, request["cwd"] or ".", must_exist=True, directory=True)
    complete_environment = {"PATH": os.environ.get("PATH", os.defpath)}
    if os.name == "nt" and os.environ.get("SYSTEMROOT"):
        complete_environment["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    complete_environment.update(request["environment"])
    timeout = request.get("timeout_seconds")
    tools = {
        name: run_probe(argv, cwd, complete_environment, timeout)
        for name, argv in request["tool_version_commands"].items()
    }
    probes_reliable = all(
        isinstance(result, dict)
        and result.get("exit_code") == 0
        and "error" not in result
        for result in tools.values()
    )
    execution_id = str(uuid.uuid4())
    runner_path, runner_hash = ensure_runner_snapshot(evidence_dir)
    raw_dir = evidence_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = raw_dir / f"{execution_id}.stdout"
    stderr_path = raw_dir / f"{execution_id}.stderr"
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    timed_out = False
    execution_error = False
    try:
        exit_code, stdout, stderr = run_process(
            request["command"], cwd, complete_environment, timeout,
        )
        timed_out = exit_code == 124 and b"PrizmKit runner timeout" in stderr
    except OSError as exc:
        exit_code = 127
        stdout = b""
        stderr = f"PrizmKit runner execution error: {exc}\n".encode()
        execution_error = True
    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(stderr)
    finished = dt.datetime.now(dt.timezone.utc).isoformat()
    existing = load_json(evidence_dir / "executions.json") if (evidence_dir / "executions.json").exists() else []
    if not isinstance(existing, list):
        raise RequestError("executions.json must remain an array")
    previous = canonical_sha256(existing[-1]) if existing else None
    same_request_attempts = sum(1 for item in existing if isinstance(item, dict) and item.get("request_sha256") == file_sha256(request_path))
    receipt = {
        "receipt_format": "prizmkit-runner-generated-v1",
        "runner_path": runner_path,
        "runner_sha256": runner_hash,
        "execution_id": execution_id,
        "attempt_index": same_request_attempts + 1,
        "request_path": evidence_relative(evidence_dir, request_path),
        "request_sha256": file_sha256(request_path),
        "purpose": request["purpose"],
        "command": request["command"],
        "cwd": request["cwd"],
        "environment": complete_environment,
        "tool_versions": tools,
        "layer": request["layer"],
        "test_ids": request["test_ids"],
        "external_targets": request["external_targets"],
        "exit_code": exit_code,
        "stdout_path": evidence_relative(evidence_dir, stdout_path),
        "stderr_path": evidence_relative(evidence_dir, stderr_path),
        "stdout_sha256": file_sha256(stdout_path),
        "stderr_sha256": file_sha256(stderr_path),
        "selected_execution": selected_execution,
        "reliable": probes_reliable and not timed_out and not execution_error,
        "started_at": started,
        "finished_at": finished,
        "previous_receipt_sha256": previous,
        "replay_of": replay_of,
        "isolation": isolation,
    }
    append_receipt(evidence_dir, receipt)
    return receipt


def copy_project_tree(project_root: Path, destination: Path, evidence_dir: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        directory_relative = Path(directory).resolve().relative_to(project_root.resolve())
        ignored: set[str] = set()
        for name in names:
            relative = directory_relative / name
            candidate = project_root / relative
            if is_volatile_snapshot_path(project_root, candidate, [evidence_dir]):
                ignored.add(name)
        return ignored

    shutil.copytree(project_root, destination, ignore=ignore)


def git_archive_baseline(project_root: Path, baseline_commit: str, destination: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(project_root), "archive", "--format=tar", baseline_commit],
        capture_output=True, check=False,
    )
    if result.returncode != 0:
        raise RequestError(f"cannot archive baseline commit {baseline_commit}: {result.stderr.decode(errors='replace')}")
    destination.mkdir(parents=True)
    extracted = subprocess.run(["tar", "-xf", "-", "-C", str(destination)], input=result.stdout, capture_output=True, check=False)
    if extracted.returncode != 0:
        raise RequestError(f"cannot extract baseline archive: {extracted.stderr.decode(errors='replace')}")


def materialize_request(evidence_dir: Path, name: str, request: dict[str, Any]) -> Path:
    path = evidence_dir / "requests" / name
    write_json_atomic(path, request)
    return path


def run_differential(project_root: Path, evidence_dir: Path, request_path: Path) -> dict[str, Any]:
    request = ensure_object(load_json(request_path), "differential request")
    required = {"request_version", "behavior_id", "method", "execution_request", "baseline_commit", "current_tree_sha256", "mutation_patch_path", "test_overlay_paths", "expected_failure_signals"}
    if set(request) != required or request["request_version"] != "1.0":
        raise RequestError(f"differential request fields must be exactly {sorted(required)} with version 1.0")
    execution_request = validate_execution_request(request["execution_request"])
    expected_failure_signals = ensure_string_list(request["expected_failure_signals"], "expected_failure_signals", allow_empty=False)
    overlay_paths = ensure_string_list(request["test_overlay_paths"], "test_overlay_paths")
    for relative in overlay_paths:
        confined(project_root, relative, must_exist=True)
    project_before = tree_sha256(project_root, [evidence_dir])
    if project_before != request["current_tree_sha256"]:
        raise RequestError("current project tree does not match differential request")
    current_request_path = materialize_request(evidence_dir, f"differential-{uuid.uuid4().hex}.execution.json", execution_request)
    baseline_receipt = None
    mutation_receipt = None
    current_receipt = None
    isolation_tree = None
    mutation_apply_sha = None
    mutation_restore_sha = None
    cleanup_succeeded = False
    try:
        with tempfile.TemporaryDirectory(prefix="prizmkit-differential-") as temporary:
            temporary_root = Path(temporary)
            current_root = temporary_root / "current"
            copy_project_tree(project_root, current_root, evidence_dir)
            isolation_tree = tree_sha256(current_root)
            if request["method"] == "baseline":
                failing_root = temporary_root / "baseline"
                git_archive_baseline(project_root, request["baseline_commit"], failing_root)
                for relative in overlay_paths:
                    source = confined(project_root, relative, must_exist=True)
                    destination = confined(failing_root, relative)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
                baseline_receipt = execute_request(
                    project_root, evidence_dir, current_request_path, execution_root=failing_root,
                    isolation={"kind": "baseline", "tree_sha256": tree_sha256(failing_root), "baseline_commit": request["baseline_commit"]},
                    selected_execution=False,
                )
            elif request["method"] == "controlled-mutation":
                failing_root = temporary_root / "mutation"
                shutil.copytree(current_root, failing_root)
                patch_value = request["mutation_patch_path"]
                if not isinstance(patch_value, str) or not patch_value:
                    raise RequestError("controlled mutation requires mutation_patch_path")
                patch_path = request_file(evidence_dir, patch_value)
                applied = subprocess.run(["git", "apply", "--whitespace=nowarn", str(patch_path)], cwd=failing_root, capture_output=True, check=False)
                if applied.returncode != 0:
                    raise RequestError(f"controlled mutation could not be applied: {applied.stderr.decode(errors='replace')}")
                mutation_apply_sha = tree_sha256(failing_root)
                mutation_receipt = execute_request(
                    project_root, evidence_dir, current_request_path, execution_root=failing_root,
                    isolation={"kind": "controlled-mutation", "tree_sha256": tree_sha256(failing_root), "patch_sha256": file_sha256(patch_path)},
                    selected_execution=False,
                )
                mutation_restore_sha = tree_sha256(current_root)
            else:
                raise RequestError("differential method must be baseline or controlled-mutation")
            current_receipt = execute_request(
                project_root, evidence_dir, current_request_path, execution_root=current_root,
                isolation={"kind": "current", "tree_sha256": tree_sha256(current_root)},
            )
        cleanup_succeeded = True
    finally:
        project_after = tree_sha256(project_root, [evidence_dir])
    failing_receipt = baseline_receipt or mutation_receipt
    failing_output = b""
    if failing_receipt:
        failing_output = (evidence_dir / failing_receipt["stdout_path"]).read_bytes() + (evidence_dir / failing_receipt["stderr_path"]).read_bytes()
    failure_reason_matched = any(signal.encode() in failing_output for signal in expected_failure_signals)
    proven = bool(
        failing_receipt and current_receipt and failing_receipt["exit_code"] != 0
        and current_receipt["exit_code"] == 0 and failure_reason_matched
        and cleanup_succeeded and project_before == project_after
    )
    proof = {
        "behavior_id": request["behavior_id"],
        "classification": "PROVEN" if proven else "UNPROVEN",
        "method": request["method"],
        "differential_request_path": evidence_relative(evidence_dir, request_path),
        "differential_request_sha256": file_sha256(request_path),
        "baseline_commit": request["baseline_commit"],
        "current_tree_sha256": request["current_tree_sha256"],
        "baseline_execution_id": baseline_receipt["execution_id"] if baseline_receipt else None,
        "mutation_execution_id": mutation_receipt["execution_id"] if mutation_receipt else None,
        "current_execution_id": current_receipt["execution_id"] if current_receipt else None,
        "failure_reason_matched": failure_reason_matched,
        "cleanup_succeeded": cleanup_succeeded,
        "project_tree_before_sha256": project_before,
        "project_tree_after_sha256": project_after,
        "isolation_tree_sha256": isolation_tree,
        "mutation_apply_sha256": mutation_apply_sha,
        "mutation_restore_sha256": mutation_restore_sha,
        "not_applicable": None,
    }
    proof_path = evidence_dir / "differential-proof.json"
    proof_record = load_json(proof_path) if proof_path.exists() else {"proofs": []}
    if not isinstance(proof_record, dict) or not isinstance(proof_record.get("proofs"), list):
        raise RequestError("differential-proof.json has invalid append target")
    proof_record["proofs"].append(proof)
    write_json_atomic(proof_path, proof_record)
    return proof


def run_resume(
    project_root: Path,
    evidence_dir: Path,
    manifest_path: Path,
    inventory_path: Path,
    output_name: str,
) -> Path:
    manifest = ensure_object(load_json(manifest_path), "manifest")
    inventory = ensure_object(load_json(inventory_path), "inventory")
    categories = ensure_object(inventory.get("categories"), "inventory categories")
    environment_path = evidence_dir / "environment.json"
    environment = load_json(environment_path) if environment_path.exists() else {}
    aggregate = lambda entries: canonical_sha256(sorted(entries, key=lambda item: item["path"]))
    live_categories: dict[str, list[dict[str, str]]] = {}
    for category in CATEGORIES:
        live_entries: list[dict[str, str]] = []
        for entry in categories.get(category, []):
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                raise RequestError(f"invalid resume inventory entry: {category}")
            candidate = confined(project_root, entry["path"], must_exist=True)
            live_entries.append({"path": entry["path"], "sha256": file_sha256(candidate)})
        live_categories[category] = live_entries
    current = {
        "source": aggregate(live_categories["source"]),
        "tests": aggregate(live_categories["tests"]),
        "contracts": aggregate(live_categories["contracts"]),
        "lockfiles": aggregate(live_categories["lockfiles"]),
        "environment": canonical_sha256(environment),
        "plan": canonical_sha256(inventory.get("plan_inputs", {})),
    }
    changed = sorted(key for key, value in current.items() if manifest.get("target_hashes", {}).get(key) != value)
    first_invalid: str | None = None
    reasons: list[str] = []
    dependency_stage = {
        "source": "SCOPE_DISCOVER", "tests": "TEST_PLAN", "contracts": "CONTRACT_MODEL",
        "lockfiles": "INFRA_READY", "environment": "INFRA_READY", "plan": "TEST_PLAN",
    }
    if changed:
        first_invalid = min((dependency_stage[key] for key in changed), key=STAGES.index)
        reasons.append(f"target hashes changed: {', '.join(changed)}")
    files = {entry.get("path"): entry for entry in manifest.get("files", []) if isinstance(entry, dict)}
    for stage in manifest.get("stages", []):
        if not isinstance(stage, dict):
            continue
        for relative in stage.get("outputs", []):
            candidate = confined(evidence_dir, relative)
            entry = files.get(relative)
            if not candidate.is_file() or not entry or file_sha256(candidate) != entry.get("sha256"):
                stage_name = stage.get("name")
                if stage_name in STAGES and (first_invalid is None or STAGES.index(stage_name) < STAGES.index(first_invalid)):
                    first_invalid = stage_name
                reasons.append(f"missing or drifted stage output: {relative}")
    invalidated = STAGES[STAGES.index(first_invalid):] if first_invalid else []
    decision = {
        "decision_format": "prizmkit-resume-invalidation-v1",
        "manifest_path": evidence_relative(evidence_dir, manifest_path),
        "manifest_sha256": file_sha256(manifest_path),
        "inventory_path": evidence_relative(evidence_dir, inventory_path),
        "inventory_sha256": file_sha256(inventory_path),
        "current_target_hashes": current,
        "changed_hashes": changed,
        "first_invalid_stage": first_invalid,
        "invalidated_stages": invalidated,
        "preserve_prior_executions": True,
        "reasons": reasons,
        "semantic_review_required": True,
    }
    output = confined(evidence_dir, output_name)
    write_json_atomic(output, decision)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build trusted, request-driven test evidence")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--evidence-dir", required=True)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("--request", required=True)
    inventory.add_argument("--output", default="target-inventory.json")
    execute = subparsers.add_parser("execute")
    group = execute.add_mutually_exclusive_group(required=True)
    group.add_argument("--request")
    group.add_argument("--replay-receipt")
    differential = subparsers.add_parser("differential")
    differential.add_argument("--request", required=True)
    resume = subparsers.add_parser("resume")
    resume.add_argument("--manifest", required=True)
    resume.add_argument("--inventory", required=True)
    resume.add_argument("--output", default="resume-decision.json")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    evidence_dir = Path(args.evidence_dir).resolve()
    try:
        if not project_root.is_dir():
            raise RequestError(f"project root does not exist: {project_root}")
        evidence_dir.relative_to(project_root)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        if args.subcommand == "inventory":
            output = run_inventory(project_root, evidence_dir, request_file(evidence_dir, args.request), args.output)
            print(f"Inventory written: {output}")
        elif args.subcommand == "execute":
            if args.request:
                receipt = execute_request(project_root, evidence_dir, request_file(evidence_dir, args.request))
            else:
                prior_path = receipt_file(evidence_dir, args.replay_receipt)
                prior = ensure_object(load_json(prior_path), "replay receipt")
                if prior.get("receipt_format") != "prizmkit-runner-generated-v1":
                    raise RequestError("replay source is not a runner-generated receipt")
                original_request = request_file(evidence_dir, prior.get("request_path", ""))
                if file_sha256(original_request) != prior.get("request_sha256"):
                    raise RequestError("recorded request hash no longer matches replay source")
                receipt = execute_request(project_root, evidence_dir, original_request, replay_of=prior.get("execution_id"))
            print(json.dumps(receipt, ensure_ascii=False))
        elif args.subcommand == "differential":
            proof = run_differential(project_root, evidence_dir, request_file(evidence_dir, args.request))
            print(json.dumps(proof, ensure_ascii=False))
        else:
            output = run_resume(
                project_root, evidence_dir, request_file(evidence_dir, args.manifest),
                request_file(evidence_dir, args.inventory), args.output,
            )
            print(f"Resume decision written: {output}")
        return 0
    except (RequestError, OSError, ValueError) as exc:
        print(f"Test evidence builder: BLOCKED\n- {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
