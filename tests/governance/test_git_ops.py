from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import unittest

from scripts.governance.git_ops import prepare_candidate_commit


class CandidateCommitPreparationTest(unittest.TestCase):
    def test_stages_only_one_new_candidate_in_the_open_inbox(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "--initial-branch=main"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "base"], cwd=root, check=True, capture_output=True)
            draft = root / "draft.md"
            draft.write_text("candidate\n", encoding="utf-8")

            changed_paths = prepare_candidate_commit(root, draft, "CR-20260814-120000-max-secondary-video-abc123")

            self.assertEqual(
                changed_paths,
                ["03｜CHEN操盘手系统/03｜MAX剪辑系统/08｜规则候选收件箱/open/CR-20260814-120000-max-secondary-video-abc123.md"],
            )


if __name__ == "__main__":
    unittest.main()
