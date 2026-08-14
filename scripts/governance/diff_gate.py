from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from scripts.governance.candidate import Candidate, validate_candidate


OPEN_PREFIX = "03｜CHEN操盘手系统/03｜MAX剪辑系统/08｜规则候选收件箱/open/"


@dataclass(frozen=True)
class GitChange:
    status: str
    path: str


@dataclass(frozen=True)
class ChangeClassification:
    kind: str
    errors: list[str]


def classify_changes(changes: Sequence[GitChange]) -> ChangeClassification:
    if len(changes) == 1 and changes[0].status == "A" and changes[0].path.startswith(OPEN_PREFIX) and changes[0].path.endswith(".md"):
        return ChangeClassification("candidate", [])
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
