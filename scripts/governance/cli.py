import argparse
import json
from pathlib import Path

from scripts.governance.diff_gate import changes_between, changes_in_index, classify_changes, validate_pr_changes
from scripts.governance.git_ops import load_machine_role, preflight, submit_candidate


def main() -> int:
    parser = argparse.ArgumentParser(description="CHEN-BRAIN MAX rule governance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight")
    submit = subparsers.add_parser("submit-candidate")
    submit.add_argument("--draft", required=True, type=Path)
    submit.add_argument("--dry-run", action="store_true", help="validate only; this is the default")
    submit.add_argument("--push", action="store_true", help="request remote submission after the governance gate exists")
    validate = subparsers.add_parser("validate-pr")
    validate.add_argument("--base", required=True)
    validate.add_argument("--head", required=True)
    subparsers.add_parser("validate-index")
    subparsers.add_parser("install-hooks")
    args = parser.parse_args()
    repo = Path.cwd()
    if args.command == "preflight":
        role = load_machine_role(repo)
        base_sha = preflight(repo, role)
        print(json.dumps({"machine_id": role.machine_id, "role": role.role, "base_sha": base_sha}))
        return 0
    if args.command == "validate-pr":
        changes = changes_between(repo, args.base, args.head)
        classification = classify_changes(changes)
        errors = validate_pr_changes(repo, changes)
        print(json.dumps({"kind": classification.kind, "errors": errors, "changes": [change.__dict__ for change in changes]}))
        return 0 if not errors else 1
    if args.command == "validate-index":
        changes = changes_in_index(repo)
        classification = classify_changes(changes)
        errors = validate_pr_changes(repo, changes)
        print(json.dumps({"kind": classification.kind, "errors": errors, "changes": [change.__dict__ for change in changes]}))
        return 0 if not errors else 1
    if args.command == "install-hooks":
        hooks_path = repo / ".githooks" / "pre-commit"
        if not hooks_path.is_file():
            raise ValueError("missing .githooks/pre-commit")
        import subprocess

        subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo, check=True)
        configured = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if configured != ".githooks":
            raise ValueError("could not configure .githooks")
        print(json.dumps({"hooks_path": configured}))
        return 0
    result = submit_candidate(repo, args.draft, dry_run=not args.push, push=args.push)
    print(json.dumps({
        "candidate_id": result.candidate_id,
        "branch": result.branch,
        "base_sha": result.base_sha,
        "changed_paths": result.changed_paths,
        "dry_run": not args.push,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
