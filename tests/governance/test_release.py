from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

import yaml

from scripts.governance.release import load_release, validate_release


class ReleaseValidationTest(unittest.TestCase):
    def test_accepts_release_with_my_video_commit_ancestral_to_head(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            my_video = root / "my-video"
            my_video.mkdir()
            self.initialize_repository(my_video)
            release_path = root / "release.yaml"
            release_path.write_text(yaml.safe_dump(self.release_data(self.git_sha(my_video))), encoding="utf-8")

            errors = validate_release(load_release(release_path), my_video)

            self.assertEqual(errors, [])

    def test_rejects_release_with_my_video_commit_not_ancestral_to_head(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            my_video = root / "my-video"
            my_video.mkdir()
            self.initialize_repository(my_video)
            old_commit = self.git_sha(my_video)
            subprocess.run(["git", "checkout", "--orphan", "other"], cwd=my_video, check=True, capture_output=True)
            subprocess.run(["git", "rm", "-rf", "."], cwd=my_video, check=True, capture_output=True)
            (my_video / "other.txt").write_text("other\n", encoding="utf-8")
            subprocess.run(["git", "add", "other.txt"], cwd=my_video, check=True)
            subprocess.run(["git", "commit", "-m", "other root"], cwd=my_video, check=True, capture_output=True)
            release_path = root / "release.yaml"
            release_path.write_text(yaml.safe_dump(self.release_data(old_commit)), encoding="utf-8")

            errors = validate_release(load_release(release_path), my_video)

            self.assertIn("minimum_my_video_commit must be an ancestor of My-Video HEAD", errors)

    @staticmethod
    def release_data(minimum_my_video_commit: str) -> dict:
        return {
            "schema_version": 1,
            "release_id": "MAX-RULES-20260814-001",
            "status": "active",
            "rules_schema": 1,
            "skill_impact": "none",
            "minimum_my_video_commit": minimum_my_video_commit,
            "previous_release_id": "BOOTSTRAP",
            "review_batch_id": "RB-20260814-bootstrap",
        }

    @staticmethod
    def initialize_repository(repo: Path) -> None:
        subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        (repo / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, capture_output=True)

    @staticmethod
    def git_sha(repo: Path) -> str:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
        ).stdout.strip()


if __name__ == "__main__":
    unittest.main()
