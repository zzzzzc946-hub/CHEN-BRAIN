import argparse
import json
from pathlib import Path

from scripts.governance.git_ops import load_machine_role, preflight, submit_candidate


def main() -> int:
    parser = argparse.ArgumentParser(description="CHEN-BRAIN MAX rule governance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight")
    submit = subparsers.add_parser("submit-candidate")
    submit.add_argument("--draft", required=True, type=Path)
    submit.add_argument("--dry-run", action="store_true", help="validate only; this is the default")
    submit.add_argument("--push", action="store_true", help="request remote submission after the governance gate exists")
    args = parser.parse_args()
    repo = Path.cwd()
    if args.command == "preflight":
        role = load_machine_role(repo)
        base_sha = preflight(repo, role)
        print(json.dumps({"machine_id": role.machine_id, "role": role.role, "base_sha": base_sha}))
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
