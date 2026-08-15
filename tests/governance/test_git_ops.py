from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import unittest

from scripts.governance.git_ops import (
    MachineRole,
    load_machine_role,
    preflight,
    prepare_candidate_commit,
    submit_candidate,
)


class CandidateCommitPreparationTest(unittest.TestCase):
    def make_repository(self, root: Path) -> None:
        subprocess.run(["git", "init", "--initial-branch=main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        (root / "README.md").write_text("base\n", encoding="utf-8")
        (root / ".gitignore").write_text("config/machine-role.json\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md", ".gitignore"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=root, check=True, capture_output=True)

    def test_stages_only_one_new_candidate_in_the_open_inbox(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            draft = root / "draft.md"
            draft.write_text("candidate\n", encoding="utf-8")

            changed_paths = prepare_candidate_commit(root, draft, "CR-20260814-120000-max-secondary-video-abc123")

            self.assertEqual(
                changed_paths,
                ["03｜CHEN操盘手系统/03｜MAX剪辑系统/08｜规则候选收件箱/open/CR-20260814-120000-max-secondary-video-abc123.md"],
            )

    def test_loads_editor_role_from_ignored_local_config(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            config = root / "config"
            config.mkdir()
            (config / "machine-role.json").write_text(
                '{"machine_id": "max-secondary", "role": "editor"}\n', encoding="utf-8"
            )

            role = load_machine_role(root)

            self.assertEqual(role, MachineRole(machine_id="max-secondary", role="editor"))

    def test_preflight_rejects_decision_hub_candidate_submission(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            subprocess.run(
                ["git", "remote", "add", "origin", "git@github.com:zzzzzc946-hub/CHEN-BRAIN.git"],
                cwd=root,
                check=True,
            )

            with self.assertRaisesRegex(ValueError, "only editor"):
                preflight(root, MachineRole(machine_id="max-primary", role="decision-hub"))

    def test_preflight_accepts_https_github_remote(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://github.com/zzzzzc946-hub/CHEN-BRAIN.git"],
                cwd=root,
                check=True,
            )
            subprocess.run(["git", "branch", "origin/main"], cwd=root, check=True)

            base_sha = preflight(root, MachineRole(machine_id="max-secondary", role="editor"))

            self.assertEqual(len(base_sha), 40)

    def test_dry_run_uses_temporary_worktree_without_staging_source_repo(self) -> None:
        candidate_id = "CR-20260814-120000-max-secondary-video-abc123"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            self.make_repository(source)
            bare = root / "origin.git"
            subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=source, check=True)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=source, check=True, capture_output=True)
            checkout = root / "checkout"
            subprocess.run(["git", "clone", str(bare), str(checkout)], check=True, capture_output=True)
            subprocess.run(
                ["git", "remote", "set-url", "origin", "git@github.com:zzzzzc946-hub/CHEN-BRAIN.git"],
                cwd=checkout,
                check=True,
            )
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=checkout, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=checkout, check=True)
            config = checkout / "config"
            config.mkdir()
            (config / "machine-role.json").write_text(
                '{"machine_id": "max-secondary", "role": "editor"}\n', encoding="utf-8"
            )
            draft = root / f"{candidate_id}.md"
            draft.write_text(self.valid_candidate(candidate_id), encoding="utf-8")

            result = submit_candidate(checkout, draft, dry_run=True)

            self.assertEqual(result.changed_paths, [
                f"03｜CHEN操盘手系统/03｜MAX剪辑系统/08｜规则候选收件箱/open/{candidate_id}.md"
            ])
            staged = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=checkout,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertEqual(staged, "")

    def test_non_dry_submission_requires_explicit_push_permission(self) -> None:
        candidate_id = "CR-20260814-120000-max-secondary-video-abc123"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            self.make_repository(source)
            subprocess.run(
                ["git", "remote", "add", "origin", "git@github.com:zzzzzc946-hub/CHEN-BRAIN.git"],
                cwd=source,
                check=True,
            )
            subprocess.run(["git", "branch", "origin/main"], cwd=source, check=True)
            config = source / "config"
            config.mkdir()
            (config / "machine-role.json").write_text(
                '{"machine_id": "max-secondary", "role": "editor"}\n', encoding="utf-8"
            )
            draft = root / f"{candidate_id}.md"
            draft.write_text(self.valid_candidate(candidate_id), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "requires explicit push permission"):
                submit_candidate(source, draft, dry_run=False)

    def test_push_submission_commits_and_pushes_candidate_branch(self) -> None:
        candidate_id = "CR-20260814-120000-max-secondary-video-abc123"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            self.make_repository(source)
            bare = root / "origin.git"
            subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=source, check=True)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=source, check=True, capture_output=True)
            subprocess.run(
                ["git", "remote", "set-url", "origin", "https://github.com/zzzzzc946-hub/CHEN-BRAIN.git"],
                cwd=source,
                check=True,
            )
            subprocess.run(
                ["git", "config", "url.file://" + str(bare) + ".insteadOf", "https://github.com/zzzzzc946-hub/CHEN-BRAIN.git"],
                cwd=source,
                check=True,
            )
            config = source / "config"
            config.mkdir()
            (config / "machine-role.json").write_text(
                '{"machine_id": "max-secondary", "role": "editor"}\n', encoding="utf-8"
            )
            draft = root / f"{candidate_id}.md"
            draft.write_text(self.valid_candidate(candidate_id), encoding="utf-8")

            result = submit_candidate(source, draft, dry_run=False, push=True)

            self.assertEqual(result.branch, f"candidate/max-secondary/{candidate_id}")
            pushed = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{result.branch}"],
                cwd=bare,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn(result.branch, pushed)

    @staticmethod
    def valid_candidate(candidate_id: str) -> str:
        sha = "a" * 40
        return f"""---
candidate_id: {candidate_id}
machine_id: max-secondary
video_id: video-001
created_at: "2026-08-14T12:00:00Z"
formal_start_sha: {sha}
candidate_snapshot_ids: []
submission_base_sha: {sha}
topic_tags: [rhythm]
content_type: talking-head
editing_problem: false-start
user_feedback_summary: remove false start
evidence: [evidence.md]
proposed_rule: remove verified false starts
scope: rough-cut
exceptions: []
counterexamples: []
related_formal_rules: []
related_calibrations: []
related_candidates: []
duplicate_of: []
conflicts_with: []
trial_result: verified
status: OPEN_VERIFIED_ONCE
---

Candidate body.
"""


if __name__ == "__main__":
    unittest.main()
