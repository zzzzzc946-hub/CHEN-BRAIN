from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Sequence

from scripts.governance.candidate import Candidate, validate_candidate


OPEN_PREFIX = "03｜CHEN操盘手系统/03｜MAX剪辑系统/08｜规则候选收件箱/open/"
MAX_RULES_PREFIX = "03｜CHEN操盘手系统/03｜MAX剪辑系统/"
FORMAL_PREFIXES = (
    MAX_RULES_PREFIX,
    ".github/",
    ".githooks/",
    "scripts/governance/",
    "tests/governance/",
    "config/machine-role.example.json",
    "requirements-governance.txt",
    ".gitignore",
)


@dataclass(frozen=True)
class GitChange:
    status: str
    path: str


@dataclass(frozen=True)
class ChangeClassification:
    kind: str
    errors: list[str]


def changes_between(repo: Path, base: str, head: str) -> list[GitChange]:
    output = subprocess.run(
        ["git", "diff", "--name-status", "-z", base, head],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return _parse_name_status(output)


def changes_in_index(repo: Path) -> list[GitChange]:
    output = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "-z"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return _parse_name_status(output)


def _parse_name_status(output: str) -> list[GitChange]:
    fields = output.split("\0")
    changes: list[GitChange] = []
    index = 0
    while index < len(fields) - 1:
        status = fields[index]
        if status.startswith(("R", "C")):
            changes.append(GitChange(status[0], fields[index + 2]))
            index += 3
        else:
            changes.append(GitChange(status, fields[index + 1]))
            index += 2
    return changes


def classify_changes(changes: Sequence[GitChange]) -> ChangeClassification:
    if len(changes) == 1 and changes[0].status == "A" and changes[0].path.startswith(OPEN_PREFIX) and changes[0].path.endswith(".md"):
        return ChangeClassification("candidate", [])
    if changes and all(
        not change.path.startswith(OPEN_PREFIX)
        and any(change.path.startswith(prefix) for prefix in FORMAL_PREFIXES)
        for change in changes
    ):
        return ChangeClassification("formal_governance", [])
    return ChangeClassification("invalid", ["candidate PR may only add one open candidate"])


def validate_candidate_change(repo: Path, change: GitChange) -> list[str]:
    if change.status != "A" or not change.path.startswith(OPEN_PREFIX):
        return ["candidate PR may only add one open candidate"]
    candidate_path = repo / change.path
    try:
        candidate = Candidate.from_path(candidate_path)
    except (OSError, ValueError) as error:
        return [str(error)]
    return validate_candidate(candidate, candidate_path, candidate_path.parent)


def validate_pr_changes(repo: Path, changes: Sequence[GitChange]) -> list[str]:
    classification = classify_changes(changes)
    if classification.kind == "invalid":
        return classification.errors
    if classification.kind == "formal_governance":
        return []
    return validate_candidate_change(repo, changes[0])
