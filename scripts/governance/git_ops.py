from pathlib import Path
import shutil
import subprocess


OPEN_INBOX = Path("03｜CHEN操盘手系统") / "03｜MAX剪辑系统" / "08｜规则候选收件箱" / "open"


def prepare_candidate_commit(repo: Path, draft: Path, candidate_id: str) -> list[str]:
    relative_target = OPEN_INBOX / f"{candidate_id}.md"
    target = repo / relative_target
    if target.exists():
        raise ValueError("candidate already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(draft, target)
    subprocess.run(["git", "add", "--", str(relative_target)], cwd=repo, check=True)
    output = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.rstrip("\0").split("\0")
    if output != [str(relative_target)]:
        raise ValueError("candidate submission must stage exactly one open candidate")
    return output
