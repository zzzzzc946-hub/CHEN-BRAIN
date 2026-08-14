from dataclasses import dataclass
from typing import Sequence


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
