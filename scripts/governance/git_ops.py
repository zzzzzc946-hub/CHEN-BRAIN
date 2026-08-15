from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from scripts.governance.candidate import Candidate, validate_candidate

OPEN_INBOX = Path("03｜CHEN操盘手系统") / "03｜MAX剪辑系统" / "08｜规则候选收件箱" / "open"
EXPECTED_REPOSITORY = "github.com/zzzzzc946-hub/chen-brain"


@dataclass(frozen=True)
class MachineRole:
    machine_id: str
    role: str


@dataclass(frozen=True)
class SubmissionResult:
    candidate_id: str
    branch: str
    base_sha: str
    changed_paths: list[str]


def _run_git(repo: Path, args: list[str], capture_output: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=capture_output, text=True
    )


def canonical_remote(remote: str) -> str:
    value = remote.strip().rstrip("/")
    if value.startswith("git@") and ":" in value:
        host, repository = value[4:].split(":", 1)
    else:
        parsed = urlparse(value)
        host = parsed.hostname or ""
        repository = parsed.path.lstrip("/")
    return f"{host.lower()}/{repository.removesuffix('.git').strip('/').lower()}"


def load_machine_role(repo: Path) -> MachineRole:
    config_path = repo / "config" / "machine-role.json"
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError("missing ignored config/machine-role.json") from error
    except json.JSONDecodeError as error:
        raise ValueError("machine role config must be valid JSON") from error
    if not isinstance(raw, dict):
        raise ValueError("machine role config must be an object")
    machine_id = raw.get("machine_id")
    role = raw.get("role")
    if not isinstance(machine_id, str) or not machine_id:
        raise ValueError("machine role config requires machine_id")
    if role not in {"editor", "decision-hub"}:
        raise ValueError("machine role config role must be editor or decision-hub")
    return MachineRole(machine_id=machine_id, role=role)


def preflight(repo: Path, role: MachineRole) -> str:
    if role.role != "editor":
        raise ValueError("only editor machines may submit rule candidates")
    try:
        origin = _run_git(repo, ["config", "--get", "remote.origin.url"], capture_output=True).stdout.strip()
    except subprocess.CalledProcessError as error:
        raise ValueError("candidate submission requires an origin remote") from error
    if canonical_remote(origin) != EXPECTED_REPOSITORY:
        raise ValueError("origin must point to zzzzzc946-hub/CHEN-BRAIN")
    try:
        return _run_git(repo, ["rev-parse", "--verify", "origin/main"], capture_output=True).stdout.strip()
    except subprocess.CalledProcessError as error:
        raise ValueError("origin/main must be available before candidate submission") from error


def submit_candidate(repo: Path, draft: Path, dry_run: bool = True, push: bool = False) -> SubmissionResult:
    if not dry_run and not push:
        raise ValueError("candidate submission requires explicit push permission")
    role = load_machine_role(repo)
    base_sha = preflight(repo, role)
    candidate = Candidate.from_path(draft)
    errors = validate_candidate(candidate, draft)
    if errors:
        raise ValueError("; ".join(errors))
    branch = f"candidate/{role.machine_id}/{candidate.candidate_id}"

    with TemporaryDirectory(prefix="chen-brain-candidate-") as temporary_root:
        worktree = Path(temporary_root) / "worktree"
        _run_git(repo, ["worktree", "add", "--detach", str(worktree), "origin/main"])
        try:
            changed_paths = prepare_candidate_commit(worktree, draft, candidate.candidate_id)
            if push:
                _run_git(worktree, ["commit", "-m", f"candidate: {candidate.candidate_id}"])
                _run_git(
                    worktree,
                    ["push", "origin", f"HEAD:refs/heads/{branch}"],
                    capture_output=True,
                )
            return SubmissionResult(
                candidate_id=candidate.candidate_id,
                branch=branch,
                base_sha=base_sha,
                changed_paths=changed_paths,
            )
        finally:
            _run_git(repo, ["worktree", "remove", "--force", str(worktree)])


def prepare_candidate_commit(repo: Path, draft: Path, candidate_id: str) -> list[str]:
    relative_target = OPEN_INBOX / f"{candidate_id}.md"
    target = repo / relative_target
    if target.exists():
        raise ValueError("candidate already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(draft, target)
    _run_git(repo, ["add", "--", str(relative_target)])
    output = _run_git(repo, ["diff", "--cached", "--name-only", "-z"], capture_output=True).stdout.rstrip("\0").split("\0")
    if output != [str(relative_target)]:
        raise ValueError("candidate submission must stage exactly one open candidate")
    return output
