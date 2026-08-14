import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAL_GOVERNANCE = "scripts/governance/contract.md"


class GovernanceCliTest(unittest.TestCase):
    def test_validate_pr_accepts_a_formal_governance_commit_range(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            (repo / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, capture_output=True)
            base = self.git_sha(repo)
            formal_path = repo / FORMAL_GOVERNANCE
            formal_path.parent.mkdir(parents=True)
            formal_path.write_text("formal rule\n", encoding="utf-8")
            subprocess.run(["git", "add", FORMAL_GOVERNANCE], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "formal"], cwd=repo, check=True, capture_output=True)
            head = self.git_sha(repo)
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(PROJECT_ROOT)

            result = subprocess.run(
                [sys.executable, "-m", "scripts.governance.cli", "validate-pr", "--base", base, "--head", head],
                cwd=repo,
                env=environment,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"kind": "formal_governance"', result.stdout)

    def test_validate_index_checks_the_staged_change_set(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            self.initialize_repository(repo)
            formal_path = repo / FORMAL_GOVERNANCE
            formal_path.parent.mkdir(parents=True)
            formal_path.write_text("formal rule\n", encoding="utf-8")
            subprocess.run(["git", "add", FORMAL_GOVERNANCE], cwd=repo, check=True)
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(PROJECT_ROOT)

            result = subprocess.run(
                [sys.executable, "-m", "scripts.governance.cli", "validate-index"],
                cwd=repo,
                env=environment,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"kind": "formal_governance"', result.stdout)

    def test_install_hooks_sets_the_repository_hook_path(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            self.initialize_repository(repo)
            hooks = repo / ".githooks"
            hooks.mkdir()
            (hooks / "pre-commit").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(PROJECT_ROOT)

            result = subprocess.run(
                [sys.executable, "-m", "scripts.governance.cli", "install-hooks"],
                cwd=repo,
                env=environment,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            hook_path = subprocess.run(
                ["git", "config", "--get", "core.hooksPath"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(hook_path, ".githooks")

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
