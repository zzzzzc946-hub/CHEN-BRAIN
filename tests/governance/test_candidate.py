from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.governance.candidate import Candidate, validate_candidate


VALID_CANDIDATE = """---
candidate_id: CR-20260814-120000-max-secondary-video-abc123
machine_id: max-secondary
video_id: video
created_at: '2026-08-14T12:00:00Z'
formal_start_sha: 0123456789abcdef0123456789abcdef01234567
candidate_snapshot_ids: []
submission_base_sha: 0123456789abcdef0123456789abcdef01234567
topic_tags: [hook]
content_type: talking-head
editing_problem: hook clarity
user_feedback_summary: Keep the conclusion earlier.
evidence: [00:00:03]
proposed_rule: condition -> action
scope: MAX talking-head videos
exceptions: []
counterexamples: []
related_formal_rules: [F1]
related_calibrations: []
related_candidates: []
duplicate_of: []
conflicts_with: []
trial_result: verified once
status: OPEN_VERIFIED_ONCE
---

# Candidate
"""


class CandidateValidationTest(unittest.TestCase):
    def test_accepts_a_complete_candidate_with_a_matching_filename(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "CR-20260814-120000-max-secondary-video-abc123.md"
            path.write_text(VALID_CANDIDATE, encoding="utf-8")

            candidate = Candidate.from_path(path)

            self.assertEqual(validate_candidate(candidate, path), [])

    def test_rejects_a_candidate_outside_the_open_inbox(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "CR-20260814-120000-max-secondary-video-abc123.md"
            path.write_text(VALID_CANDIDATE, encoding="utf-8")

            errors = validate_candidate(
                Candidate.from_path(path),
                path,
                open_directory=Path(directory) / "open",
            )

            self.assertIn("candidate must be inside the open inbox", errors)


if __name__ == "__main__":
    unittest.main()
