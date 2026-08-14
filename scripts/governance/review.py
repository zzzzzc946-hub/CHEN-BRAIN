from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Sequence

import yaml


INBOX = Path("03｜CHEN操盘手系统") / "03｜MAX剪辑系统" / "08｜规则候选收件箱"
OPEN = INBOX / "open"
PROCESSED = INBOX / "processed"
REVIEW_BATCHES = INBOX / "governance" / "review-batches"
BATCH_ID_RE = re.compile(r"^RB-\d{8}-[a-z0-9]+$")
DECISION_FIELDS = {
    "disposition",
    "decision_reason",
    "release_id",
    "target_rule_ids",
    "supersedes",
    "processed_at",
}
DISPOSITIONS = {"REJECTED", "EVIDENCE_MERGED", "PROMOTED", "REVISED", "VIDEO_ONLY", "NEEDS_MORE_EVIDENCE"}


@dataclass(frozen=True)
class ReviewBatch:
    batch_id: str
    path: Path
    candidates: list[dict[str, str]]


def create_review_batch(repo: Path, candidate_ids: Sequence[str], batch_id: str) -> ReviewBatch:
    if not BATCH_ID_RE.fullmatch(batch_id):
        raise ValueError("invalid review batch ID")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("review batch candidate IDs must be unique")
    batch_path = repo / REVIEW_BATCHES / f"{batch_id}.yaml"
    if batch_path.exists():
        raise ValueError("review batch already exists")
    candidates: list[dict[str, str]] = []
    for candidate_id in candidate_ids:
        candidate_path = OPEN / f"{candidate_id}.md"
        if not (repo / candidate_path).is_file():
            raise ValueError(f"open candidate not found: {candidate_id}")
        blob_sha = subprocess.run(
            ["git", "rev-parse", f"HEAD:{candidate_path.as_posix()}"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        candidates.append({"candidate_id": candidate_id, "blob_sha": blob_sha})
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "batch_id": batch_id,
                "base_sha": base_sha,
                "candidates": candidates,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return ReviewBatch(batch_id=batch_id, path=batch_path, candidates=candidates)


def validate_processed(repo: Path, batch: ReviewBatch, candidate_ids: Sequence[str]) -> list[str]:
    frozen = {item["candidate_id"]: item["blob_sha"] for item in batch.candidates}
    if set(candidate_ids) != set(frozen):
        return ["processed candidates must exactly match the review batch"]
    errors: list[str] = []
    for candidate_id in candidate_ids:
        original = subprocess.run(
            ["git", "cat-file", "-p", frozen[candidate_id]],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        processed_path = repo / PROCESSED / f"{candidate_id}.md"
        try:
            processed = processed_path.read_text(encoding="utf-8")
        except OSError:
            errors.append(f"processed candidate not found: {candidate_id}")
            continue
        marker = "\n## 裁决\n"
        if not processed.startswith(original) or not processed[len(original):].startswith(marker):
            errors.append("processed candidate body differs from frozen batch blob")
            continue
        decision_text = processed[len(original) + len(marker):]
        decision = yaml.safe_load(decision_text)
        if not isinstance(decision, dict):
            errors.append("processed candidate decision must be a YAML mapping")
            continue
        missing = sorted(DECISION_FIELDS - decision.keys())
        errors.extend(f"processed candidate missing decision field: {field}" for field in missing)
        if decision.get("disposition") not in DISPOSITIONS:
            errors.append("processed candidate disposition is invalid")
        if not isinstance(decision.get("target_rule_ids"), list):
            errors.append("processed candidate target_rule_ids must be a list")
        if not isinstance(decision.get("supersedes"), list):
            errors.append("processed candidate supersedes must be a list")
    return errors
