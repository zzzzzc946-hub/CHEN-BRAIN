from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

import yaml

from scripts.governance.review import create_review_batch


OPEN = Path("03｜CHEN操盘手系统") / "03｜MAX剪辑系统" / "08｜规则候选收件箱" / "open"


class ReviewBatchTest(unittest.TestCase):
    def test_batch_freezes_candidate_id_and_head_blob_sha(self) -> None:
        candidate_id = "CR-20260814-120000-max-secondary-video-abc123"
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            self.initialize_repository(repo)
            candidate_path = repo / OPEN / f"{candidate_id}.md"
            candidate_path.parent.mkdir(parents=True)
            candidate_path.write_text("candidate v1\n", encoding="utf-8")
            subprocess.run(["git", "add", str(candidate_path.relative_to(repo))], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "candidate"], cwd=repo, check=True, capture_output=True)

            batch = create_review_batch(repo, [candidate_id], "RB-20260814-abc123")

            expected_blob = subprocess.run(
                ["git", "rev-parse", f"HEAD:{candidate_path.relative_to(repo)}"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(batch.batch_id, "RB-20260814-abc123")
            self.assertEqual(batch.candidates, [{"candidate_id": candidate_id, "blob_sha": expected_blob}])
            parsed = yaml.safe_load(batch.path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["candidates"], batch.candidates)

    @staticmethod
    def initialize_repository(repo: Path) -> None:
        subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        (repo / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
