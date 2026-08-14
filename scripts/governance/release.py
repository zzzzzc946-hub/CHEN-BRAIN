from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Any

import yaml


REQUIRED_FIELDS = {
    "schema_version",
    "release_id",
    "status",
    "rules_schema",
    "skill_impact",
    "minimum_my_video_commit",
    "previous_release_id",
    "review_batch_id",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RELEASE_ID_RE = re.compile(r"^MAX-RULES-\d{8}-\d{3}$")


@dataclass(frozen=True)
class Release:
    data: dict[str, Any]


def load_release(path: Path) -> Release:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"cannot read release: {error}") from error
    if not isinstance(data, dict):
        raise ValueError("release must be a YAML mapping")
    return Release(data=data)


def validate_release(release: Release, my_video_repo: Path) -> list[str]:
    data = release.data
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - data.keys())
    errors.extend(f"missing required field: {field}" for field in missing)
    if missing:
        return errors
    if data["schema_version"] != 1:
        errors.append("schema_version must be 1")
    if not isinstance(data["release_id"], str) or not RELEASE_ID_RE.fullmatch(data["release_id"]):
        errors.append("release_id must match MAX-RULES-YYYYMMDD-NNN")
    if data["status"] != "active":
        errors.append("status must be active")
    if data["rules_schema"] != 1:
        errors.append("rules_schema must be 1")
    if data["skill_impact"] not in {"none", "required"}:
        errors.append("skill_impact must be none or required")
    minimum_commit = data["minimum_my_video_commit"]
    if not isinstance(minimum_commit, str) or not SHA_RE.fullmatch(minimum_commit):
        errors.append("minimum_my_video_commit must be a 40-character lowercase SHA")
        return errors
    if not isinstance(data["previous_release_id"], str) or not data["previous_release_id"]:
        errors.append("previous_release_id must be a non-empty string")
    if not isinstance(data["review_batch_id"], str) or not data["review_batch_id"]:
        errors.append("review_batch_id must be a non-empty string")
    commit_exists = subprocess.run(
        ["git", "cat-file", "-e", f"{minimum_commit}^{{commit}}"],
        cwd=my_video_repo,
        capture_output=True,
        text=True,
    )
    if commit_exists.returncode != 0:
        errors.append("minimum_my_video_commit does not exist in My-Video")
        return errors
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", minimum_commit, "HEAD"],
        cwd=my_video_repo,
        capture_output=True,
        text=True,
    )
    if ancestor.returncode != 0:
        errors.append("minimum_my_video_commit must be an ancestor of My-Video HEAD")
    return errors
