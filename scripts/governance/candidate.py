from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Optional

import yaml


REQUIRED_FIELDS = {
    "candidate_id",
    "machine_id",
    "video_id",
    "created_at",
    "formal_start_sha",
    "candidate_snapshot_ids",
    "submission_base_sha",
    "topic_tags",
    "content_type",
    "editing_problem",
    "user_feedback_summary",
    "evidence",
    "proposed_rule",
    "scope",
    "exceptions",
    "counterexamples",
    "related_formal_rules",
    "related_calibrations",
    "related_candidates",
    "duplicate_of",
    "conflicts_with",
    "trial_result",
    "status",
}
LIST_FIELDS = {
    "candidate_snapshot_ids",
    "topic_tags",
    "evidence",
    "exceptions",
    "counterexamples",
    "related_formal_rules",
    "related_calibrations",
    "related_candidates",
    "duplicate_of",
    "conflicts_with",
}
STATUS_VALUES = {"OPEN_UNTRIED", "OPEN_VERIFIED_ONCE", "REVIEW"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FILENAME_RE = re.compile(r"^(CR-\d{8}-\d{6}-[a-z0-9-]+-[a-z0-9-]+-[a-z0-9]+)\.md$")
ABSOLUTE_PATH_RE = re.compile(r"(^/|^~[/\\]|^[A-Za-z]:[\\/])")


@dataclass(frozen=True)
class Candidate:
    data: dict[str, Any]

    @property
    def candidate_id(self) -> str:
        return str(self.data.get("candidate_id", ""))

    @classmethod
    def from_path(cls, path: Path) -> "Candidate":
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise ValueError("candidate frontmatter must start with ---")
        try:
            frontmatter, _body = text[4:].split("\n---\n", 1)
        except ValueError as error:
            raise ValueError("candidate frontmatter must end with ---") from error
        parsed = yaml.safe_load(frontmatter)
        if not isinstance(parsed, dict):
            raise ValueError("candidate frontmatter must be a mapping")
        return cls(parsed)


def _contains_forbidden_path(value: Any) -> bool:
    if isinstance(value, str):
        return bool(ABSOLUTE_PATH_RE.match(value)) or ".env" in value.lower()
    if isinstance(value, list):
        return any(_contains_forbidden_path(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_forbidden_path(item) for item in value.values())
    return False


def validate_candidate(
    candidate: Candidate,
    path: Path,
    open_directory: Optional[Path] = None,
) -> list[str]:
    errors: list[str] = []
    if open_directory is not None:
        try:
            path.resolve().relative_to(open_directory.resolve())
        except ValueError:
            errors.append("candidate must be inside the open inbox")
    missing = sorted(REQUIRED_FIELDS - candidate.data.keys())
    errors.extend(f"missing required field: {field}" for field in missing)
    if missing:
        return errors

    for field in REQUIRED_FIELDS - LIST_FIELDS:
        if not isinstance(candidate.data[field], str) or not candidate.data[field].strip():
            errors.append(f"{field} must be a non-empty string")
    for field in LIST_FIELDS:
        if not isinstance(candidate.data[field], list):
            errors.append(f"{field} must be a list")

    expected = FILENAME_RE.fullmatch(path.name)
    if not expected or expected.group(1) != candidate.candidate_id:
        errors.append("candidate_id must match filename")
    if not SHA_RE.fullmatch(str(candidate.data["formal_start_sha"])):
        errors.append("formal_start_sha must be a 40-character lowercase SHA")
    if not SHA_RE.fullmatch(str(candidate.data["submission_base_sha"])):
        errors.append("submission_base_sha must be a 40-character lowercase SHA")
    if candidate.data["status"] not in STATUS_VALUES:
        errors.append("status must be OPEN_UNTRIED, OPEN_VERIFIED_ONCE, or REVIEW")
    if isinstance(candidate.data["candidate_snapshot_ids"], list) and len(candidate.data["candidate_snapshot_ids"]) > 3:
        errors.append("candidate_snapshot_ids may contain at most 3 IDs")
    if _contains_forbidden_path(candidate.data):
        errors.append("machine absolute path is forbidden")
    return errors
