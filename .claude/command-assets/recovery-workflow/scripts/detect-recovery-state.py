#!/usr/bin/env python3
"""
detect-recovery-state.py — Universal workflow recovery detector.

Auto-detects which interactive workflow or pipeline session was interrupted
by inspecting git branch names, durable planning artifacts, pipeline state,
current-workspace plans, review artifacts, and code changes.

Does NOT run tests — the skill controls test execution so the user can see
real-time output.

Usage:
  python3 detect-recovery-state.py [--project-root .]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def run_git(args, cwd=None):
    """Run a git command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def detect_main_branch(project_root):
    """Detect the default branch name (main or master)."""
    for candidate in ["main", "master"]:
        check = run_git(["rev-parse", "--verify", candidate], cwd=project_root)
        if check:
            return candidate
    return "main"


def relpath(path, project_root):
    return os.path.relpath(path, project_root)


def file_exists(project_root, *parts):
    path = os.path.join(project_root, *parts)
    return path if os.path.isfile(path) else None


def dir_has_content(project_root, *parts):
    path = os.path.join(project_root, *parts)
    return os.path.isdir(path) and bool(os.listdir(path))


def extract_bug_id_from_branch(branch):
    """Extract bug ID from branch name like fix/B-001-login-crash -> B-001."""
    match = re.match(r"fix/(B-\d+)", branch or "")
    return match.group(1) if match else None


def latest_bugfix_artifact_id(project_root):
    bugfix_dir = os.path.join(project_root, ".prizmkit", "bugfix")
    if not os.path.isdir(bugfix_dir):
        return None
    bug_ids = sorted(
        d for d in os.listdir(bugfix_dir)
        if os.path.isdir(os.path.join(bugfix_dir, d))
    )
    return bug_ids[-1] if bug_ids else None


def detect_workflow_type(project_root):
    """Priority-ordered signature matching.

    Returns (workflow_type, context_dict) or (None, None).
    """
    branch = run_git(["branch", "--show-current"], cwd=project_root)

    if branch.startswith("fix/"):
        return ("bug-fix-workflow", {
            "bug_id": extract_bug_id_from_branch(branch),
            "branch": branch,
            "signal": "fix branch",
        })

    if dir_has_content(project_root, ".prizmkit", "state", "bugfix"):
        return ("bug-fix-workflow", {
            "bug_id": extract_bug_id_from_branch(branch) or latest_bugfix_artifact_id(project_root),
            "branch": branch,
            "signal": "bugfix pipeline state",
        })

    if file_exists(project_root, ".prizmkit", "plans", "bug-fix-list.json"):
        return ("bug-fix-workflow", {
            "bug_id": extract_bug_id_from_branch(branch) or latest_bugfix_artifact_id(project_root),
            "branch": branch,
            "signal": "bug-fix-list.json",
        })

    bug_id = latest_bugfix_artifact_id(project_root)
    if bug_id:
        return ("bug-fix-workflow", {
            "bug_id": bug_id,
            "branch": branch,
            "signal": "optional bugfix artifacts",
        })

    if branch.startswith("refactor/"):
        return ("refactor-workflow", {"branch": branch, "signal": "refactor branch"})

    if file_exists(project_root, ".prizmkit", "plans", "refactor-list.json"):
        return ("refactor-workflow", {"branch": branch, "signal": "refactor-list.json"})

    if dir_has_content(project_root, ".prizmkit", "state", "refactor"):
        return ("refactor-workflow", {"branch": branch, "signal": "refactor pipeline state"})

    if branch.startswith("feat/"):
        return ("feature-workflow", {"branch": branch, "signal": "feature branch"})

    if file_exists(project_root, ".prizmkit", "plans", "feature-list.json"):
        return ("feature-workflow", {"branch": branch, "signal": "feature-list.json"})

    if dir_has_content(project_root, ".prizmkit", "state", "features"):
        return ("feature-workflow", {"branch": branch, "signal": "feature pipeline state"})

    if file_exists(project_root, "spec.md") or file_exists(project_root, "plan.md"):
        return ("unknown-fast-path", {"branch": branch, "signal": "spec.md or plan.md"})

    return (None, None)


def detect_other_workflows(project_root, primary_type):
    """Scan for secondary workflow signals beyond the primary match."""
    others = []
    branch = run_git(["branch", "--show-current"], cwd=project_root)

    signals = [
        ("bug-fix-workflow", [
            branch.startswith("fix/"),
            file_exists(project_root, ".prizmkit", "plans", "bug-fix-list.json"),
            dir_has_content(project_root, ".prizmkit", "state", "bugfix"),
            latest_bugfix_artifact_id(project_root),
        ]),
        ("refactor-workflow", [
            branch.startswith("refactor/"),
            file_exists(project_root, ".prizmkit", "plans", "refactor-list.json"),
            dir_has_content(project_root, ".prizmkit", "state", "refactor"),
        ]),
        ("feature-workflow", [
            branch.startswith("feat/"),
            file_exists(project_root, ".prizmkit", "plans", "feature-list.json"),
            dir_has_content(project_root, ".prizmkit", "state", "features"),
        ]),
    ]

    for workflow, checks in signals:
        if workflow != primary_type and any(checks):
            others.append(workflow)
    return others


def find_first_existing(project_root, candidates):
    for parts in candidates:
        path = os.path.join(project_root, *parts)
        if os.path.isfile(path) or os.path.isdir(path):
            return relpath(path, project_root)
    return None


def find_review_artifact(project_root):
    candidates = [
        ("review-report.md",),
        ("code-review-report.md",),
        (".prizmkit", "review-report.md"),
        (".prizmkit", "code-review", "review-report.md"),
        (".prizmkit", "reviews"),
    ]
    return find_first_existing(project_root, candidates)


def find_session_artifact(project_root):
    candidates = [
        ("context-snapshot.md",),
        ("session-summary.md",),
        (".prizmkit", "context-snapshot.md"),
        (".prizmkit", "session-summary.md"),
    ]
    return find_first_existing(project_root, candidates)


def detect_fast_path_artifacts(project_root):
    artifacts = {}
    for name in ["spec.md", "plan.md"]:
        path = file_exists(project_root, name)
        artifacts[f"{name.replace('.', '_')}_exists"] = bool(path)
        if path:
            artifacts[f"{name.replace('.', '_')}_path"] = relpath(path, project_root)

    review = find_review_artifact(project_root)
    artifacts["review_artifact_exists"] = bool(review)
    if review:
        artifacts["review_artifact_path"] = review

    session = find_session_artifact(project_root)
    artifacts["session_artifact_exists"] = bool(session)
    if session:
        artifacts["session_artifact_path"] = session

    return artifacts


def infer_bugfix_phase(project_root, context, code_changes, commits_ahead):
    """Infer bug-fix recovery phase from optional signals and git state."""
    bug_id = context.get("bug_id") if context else None
    bugfix_dir = os.path.join(project_root, ".prizmkit", "bugfix", bug_id) if bug_id else ""
    has_fix_plan = bool(bugfix_dir and os.path.isfile(os.path.join(bugfix_dir, "fix-plan.md")))
    has_fix_report = bool(bugfix_dir and os.path.isfile(os.path.join(bugfix_dir, "fix-report.md")))

    artifacts = detect_fast_path_artifacts(project_root)
    artifacts.update({
        "fix_plan_exists": has_fix_plan,
        "fix_report_exists": has_fix_report,
    })
    if has_fix_plan:
        artifacts["fix_plan_path"] = relpath(os.path.join(bugfix_dir, "fix-plan.md"), project_root)
    if has_fix_report:
        artifacts["fix_report_path"] = relpath(os.path.join(bugfix_dir, "fix-report.md"), project_root)

    has_plan_artifact = artifacts.get("spec_md_exists") or artifacts.get("plan_md_exists") or has_fix_plan
    has_review_artifact = artifacts.get("review_artifact_exists") or has_fix_report

    if commits_ahead > 0:
        return 7, "Merge Decision", artifacts, \
            f"{commits_ahead} commit(s) ahead — fix may already be committed", \
            "merge decision or branch handoff"

    if has_review_artifact and code_changes["has_changes"]:
        return 6, "User Verification", artifacts, \
            "review artifact found with code changes", \
            "user verification -> commit -> merge decision"

    if code_changes["has_changes"]:
        return 5, "Review", artifacts, \
            "code/test changes present without review artifact", \
            "run tests if safe -> code review -> verification -> commit"

    if has_plan_artifact:
        return 4, "Fix", artifacts, \
            "plan artifact found but no implementation changes", \
            "implement fix -> review -> verification -> commit"

    return 1, "Diagnosis / Triage", artifacts, \
        "bug-fix signal found but no durable implementation artifacts", \
        "restore bug context -> diagnose -> choose recovery action"


def infer_pipeline_workflow_phase(project_root, list_filename, state_subdir, workflow_label):
    list_path = file_exists(project_root, ".prizmkit", "plans", list_filename)
    has_state = dir_has_content(project_root, ".prizmkit", "state", state_subdir)
    fast_path = detect_fast_path_artifacts(project_root)

    artifacts = {
        f"{workflow_label}_list_exists": bool(list_path),
        "pipeline_state_exists": bool(has_state),
        **fast_path,
    }
    if list_path:
        artifacts[f"{workflow_label}_list_path"] = relpath(list_path, project_root)

    if list_path and has_state:
        return 4, "Monitor / Recover Pipeline", artifacts, \
            f"{list_filename} and pipeline state both exist", \
            "check launcher status or run recovery script"

    if list_path:
        return 3, "Launch", artifacts, \
            f"{list_filename} exists without pipeline state", \
            "launch pipeline or inspect/update list"

    if fast_path.get("spec_md_exists") or fast_path.get("plan_md_exists"):
        return 2, "Fast Path Continuation", artifacts, \
            "current-workspace spec/plan artifact found", \
            "continue implementation/review/commit based on diff"

    return 1, "Route Selection", artifacts, \
        f"no {list_filename} or pipeline state found", \
        f"clarify {workflow_label} intent and choose path"


def infer_feature_phase(project_root):
    return infer_pipeline_workflow_phase(project_root, "feature-list.json", "features", "feature")


def infer_refactor_phase(project_root):
    return infer_pipeline_workflow_phase(project_root, "refactor-list.json", "refactor", "refactor")


def infer_unknown_fast_path_phase(project_root, code_changes):
    artifacts = detect_fast_path_artifacts(project_root)
    if code_changes["has_changes"]:
        return 5, "Review", artifacts, \
            "spec/plan plus code changes found, but workflow family is unknown", \
            "ask workflow family -> run tests/review -> continue"
    return 2, "Fast Path Continuation", artifacts, \
        "spec/plan found, but workflow family is unknown", \
        "ask whether this is feature, bug fix, or refactor work"


def detect_commits_ahead(project_root, main_branch="main"):
    log_output = run_git(["log", f"{main_branch}..HEAD", "--oneline"], cwd=project_root)
    if log_output:
        return len(log_output.strip().split("\n"))
    return 0


def detect_git_state(project_root, main_branch="main", cached_branch=None):
    current = cached_branch or run_git(["branch", "--show-current"], cwd=project_root)

    uncommitted = run_git(["status", "--porcelain"], cwd=project_root)
    commits_ahead = detect_commits_ahead(project_root, main_branch)

    return {
        "current_branch": current,
        "changed_paths": len([line for line in uncommitted.splitlines() if line.strip()]),
        "commits_ahead_of_main": commits_ahead,
    }


def detect_code_changes(project_root, main_branch="main"):
    """Analyze implementation changes relative to main and working tree."""
    ignored_files = {
        "feature-list.json",
        "bug-fix-list.json",
        "refactor-list.json",
        "spec.md",
        "plan.md",
        "review-report.md",
        "code-review-report.md",
        "session-summary.md",
        "context-snapshot.md",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
    }
    ignored_prefixes = (
        ".prizmkit/",
        ".agents/",
        ".codex/",
        ".claude/",
        ".codebuddy/",
    )

    def is_implementation_file(filepath):
        basename = os.path.basename(filepath)
        if basename in ignored_files:
            return False
        if any(filepath.startswith(prefix) for prefix in ignored_prefixes):
            return False
        return True

    file_statuses = {}

    for command in (["diff", main_branch, "--name-status"], ["diff", "--name-status"]):
        output = run_git(command, cwd=project_root)
        if not output:
            continue
        for line in output.splitlines():
            parts = line.split("\t", 1)
            if len(parts) < 2:
                continue
            status, filepath = parts[0][0], parts[1]
            if is_implementation_file(filepath):
                file_statuses.setdefault(filepath, status)

    untracked = run_git(["ls-files", "--others", "--exclude-standard"], cwd=project_root)
    if untracked:
        for filepath in untracked.splitlines():
            filepath = filepath.strip()
            if filepath and is_implementation_file(filepath):
                file_statuses.setdefault(filepath, "A")

    test_pattern = re.compile(r"(test|spec|__tests__|\.test\.|\.spec\.)", re.IGNORECASE)
    dirs = set()
    result = {
        "files_modified": 0,
        "files_added": 0,
        "files_deleted": 0,
        "test_files_touched": 0,
        "directories_touched": [],
        "has_changes": bool(file_statuses),
    }

    for filepath, status in file_statuses.items():
        if status == "M":
            result["files_modified"] += 1
        elif status == "A":
            result["files_added"] += 1
        elif status == "D":
            result["files_deleted"] += 1
        if test_pattern.search(filepath):
            result["test_files_touched"] += 1
        parent = os.path.dirname(filepath)
        if parent:
            parts = parent.split(os.sep)
            dirs.add(os.sep.join(parts[:2]) + "/")

    result["directories_touched"] = sorted(dirs)
    return result


def main():
    parser = argparse.ArgumentParser(description="Auto-detect interrupted workflow state for recovery")
    parser.add_argument("--project-root", default=None, help="Project root directory (default: auto-detect from git)")
    args = parser.parse_args()

    if args.project_root:
        project_root = os.path.abspath(args.project_root)
    else:
        git_root = run_git(["rev-parse", "--show-toplevel"])
        project_root = git_root if git_root else os.getcwd()

    main_branch = detect_main_branch(project_root)
    workflow_type, context = detect_workflow_type(project_root)

    if workflow_type is None:
        print(json.dumps({
            "detected": False,
            "message": "No interrupted workflow detected. Use /feature-workflow, /bug-fix-workflow, or /refactor-workflow to start.",
        }, indent=2))
        sys.exit(0)

    cached_branch = context.get("branch") if context else None
    git_state = detect_git_state(project_root, main_branch, cached_branch=cached_branch)
    code_changes = detect_code_changes(project_root, main_branch)
    other_workflows = detect_other_workflows(project_root, workflow_type)

    if workflow_type == "bug-fix-workflow":
        phase, phase_name, artifacts, reason, remaining = infer_bugfix_phase(
            project_root, context, code_changes, git_state["commits_ahead_of_main"]
        )
    elif workflow_type == "feature-workflow":
        phase, phase_name, artifacts, reason, remaining = infer_feature_phase(project_root)
    elif workflow_type == "refactor-workflow":
        phase, phase_name, artifacts, reason, remaining = infer_refactor_phase(project_root)
    elif workflow_type == "unknown-fast-path":
        phase, phase_name, artifacts, reason, remaining = infer_unknown_fast_path_phase(project_root, code_changes)
    else:
        print(json.dumps({"detected": False, "message": "Unknown workflow type"}), file=sys.stderr)
        sys.exit(1)

    report = {
        "detected": True,
        "workflow_type": workflow_type,
        "phase": phase,
        "phase_name": phase_name,
        "context": context,
        "artifacts": artifacts,
        "git": git_state,
        "code": code_changes,
        "recovery": {
            "reason": reason,
            "remaining_work": remaining,
        },
    }
    if other_workflows:
        report["other_interrupted_workflows"] = other_workflows

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
