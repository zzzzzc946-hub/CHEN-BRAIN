from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Sequence

import yaml


INBOX = Path("03｜CHEN操盘手系统") / "03｜MAX剪辑系统" / "08｜规则候选收件箱"
OPEN = INBOX / "open"
REVIEW_BATCHES = INBOX / "governance" / "review-batches"
BATCH_ID_RE = re.compile(r"^RB-\d{8}-[a-z0-9]+$")


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
