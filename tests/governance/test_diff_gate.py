import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.governance.diff_gate import GitChange, classify_changes, validate_candidate_change


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


if __name__ == "__main__":
    unittest.main()
