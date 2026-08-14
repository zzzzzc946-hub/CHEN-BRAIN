import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess

from scripts.governance.diff_gate import (
    GitChange,
    changes_between,
    classify_changes,
    validate_candidate_change,
    validate_pr_changes,
)


OPEN = "03｜CHEN操盘手系统/03｜MAX剪辑系统/08｜规则候选收件箱/open/CR-20260814-120000-max-secondary-video-abc123.md"


class DiffGateTest(unittest.TestCase):
    def test_classifies_one_added_open_candidate_as_candidate_change(self) -> None:
        result = classify_changes([GitChange("A", OPEN)])

        self.assertEqual(result.kind, "candidate")
        self.assertEqual(result.errors, [])

    def test_rejects_a_candidate_change_with_a_formal_rule_edit(self) -> None:
        result = classify_changes([
            GitChange("A", OPEN),
            GitChange("M", "03｜CHEN操盘手系统/03｜MAX剪辑系统/03｜MAX粗剪判断标准.md"),
        ])

        self.assertEqual(result.kind, "invalid")
        self.assertIn("candidate PR may only add one open candidate", result.errors)

    def test_rejects_a_candidate_file_with_missing_schema_fields(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / OPEN
            candidate.parent.mkdir(parents=True)
            candidate.write_text("---\ncandidate_id: CR-20260814-120000-max-secondary-video-abc123\n---\n", encoding="utf-8")

            errors = validate_candidate_change(root, GitChange("A", OPEN))

            self.assertIn("missing required field: machine_id", errors)

    def test_classifies_a_formal_governance_only_change_separately(self) -> None:
        result = classify_changes([
            GitChange(
                "M",
                "03｜CHEN操盘手系统/03｜MAX剪辑系统/06｜剪辑迭代库/剪辑规则.md",
            ),
            GitChange(
                "A",
                "03｜CHEN操盘手系统/03｜MAX剪辑系统/08｜规则候选收件箱/governance/review-batches/RB-20260814-abc123.yaml",
            ),
        ])

        self.assertEqual(result.kind, "formal_governance")
        self.assertEqual(result.errors, [])

    def test_rejects_a_formal_rule_change_without_release_artifacts(self) -> None:
        errors = validate_pr_changes(Path("."), [
            GitChange("M", "03｜CHEN操盘手系统/03｜MAX剪辑系统/03｜MAX粗剪判断标准.md"),
        ])

        self.assertIn("formal rule change requires review batch, release, and current-release update", errors)

    def test_accepts_the_governance_package_initializer(self) -> None:
        result = classify_changes([GitChange("A", "scripts/__init__.py")])

        self.assertEqual(result.kind, "formal_governance")

    def test_pr_validation_rejects_candidate_with_invalid_contents(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / OPEN
            candidate.parent.mkdir(parents=True)
            candidate.write_text("---\ncandidate_id: CR-20260814-120000-max-secondary-video-abc123\n---\n", encoding="utf-8")

            errors = validate_pr_changes(root, [GitChange("A", OPEN)])

            self.assertIn("missing required field: machine_id", errors)

    def test_reads_added_path_from_a_git_commit_range(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "--initial-branch=main"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "base"], cwd=root, check=True, capture_output=True)
            base = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
            ).stdout.strip()
            candidate = root / OPEN
            candidate.parent.mkdir(parents=True)
            candidate.write_text("candidate\n", encoding="utf-8")
            subprocess.run(["git", "add", str(candidate.relative_to(root))], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "candidate"], cwd=root, check=True, capture_output=True)
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
            ).stdout.strip()

            changes = changes_between(root, base, head)

            self.assertEqual(changes, [GitChange("A", OPEN)])


if __name__ == "__main__":
    unittest.main()
