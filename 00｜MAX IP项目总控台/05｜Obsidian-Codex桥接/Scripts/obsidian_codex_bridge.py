#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import subprocess
import sys
import textwrap


VAULT_ROOT = Path(__file__).resolve().parents[3]
CODEX_BIN = Path.home() / ".local" / "bin" / "codex"
RESULTS_DIR = VAULT_ROOT / "00｜MAX IP项目总控台" / "05｜Obsidian-Codex桥接" / "Results"


def rel_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path.relative_to(VAULT_ROOT)
    return path


def read_note(path: Path) -> str:
    full = VAULT_ROOT / path
    if not full.exists():
        raise SystemExit(f"找不到当前笔记：{path}")
    return full.read_text(encoding="utf-8-sig")


def compact(text: str, limit: int = 120_000) -> str:
    if len(text) <= limit:
        return text
    head = text[: limit // 2]
    tail = text[-limit // 2 :]
    return head + "\n\n<!-- 中间内容过长，已由 Obsidian-Codex 桥接压缩 -->\n\n" + tail


def run_codex(active_file: Path, user_task: str, note_content: str) -> str:
    if not CODEX_BIN.exists():
        raise SystemExit(f"找不到 Codex CLI：{CODEX_BIN}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_file = RESULTS_DIR / f"{stamp}｜Codex结果.md"

    prompt = f"""
你是 CHEN BRAIN 仓库内的 Codex。

当前来源：Obsidian 内触发的 AI 请求。

硬规则：
- 本仓库是 Obsidian Markdown 知识库，不是普通代码项目。
- 不主动扩系统。
- 不修改 02｜MAX顶层思维系统 中的 MAX 原始源文档，除非用户明确要求。
- 不主动 commit / push。
- 如只是回答问题，直接给出结果即可。
- 如需要修改文件，只做用户明确要求的局部修改。

当前活动笔记：
{active_file}

用户在 Obsidian 中输入的任务：
{user_task}

当前活动笔记全文：
```markdown
{compact(note_content)}
```
"""

    cmd = [
        str(CODEX_BIN),
        "-a",
        "never",
        "exec",
        "-C",
        str(VAULT_ROOT),
        "--sandbox",
        "workspace-write",
        "--output-last-message",
        str(output_file),
        "-",
    ]
    proc = subprocess.run(
        cmd,
        input=textwrap.dedent(prompt).strip() + "\n",
        text=True,
        cwd=str(VAULT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=900,
    )
    if proc.returncode != 0:
        details = (proc.stderr or proc.stdout or "").strip()
        raise SystemExit("Codex 执行失败：\n" + details[-4000:])

    if output_file.exists():
        return output_file.read_text(encoding="utf-8-sig").strip()
    return (proc.stdout or "").strip()


def append_result(active_file: Path, user_task: str, result: str) -> None:
    full = VAULT_ROOT / active_file
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = f"""

---

## Codex结果｜{stamp}

**任务**

{user_task}

**结果**

{result.strip()}
"""
    with full.open("a", encoding="utf-8") as f:
        f.write(block.rstrip() + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--active-file", required=True)
    parser.add_argument("--task", required=True)
    args = parser.parse_args()

    active_file = rel_path(args.active_file)
    note_content = read_note(active_file)
    result = run_codex(active_file, args.task, note_content)
    append_result(active_file, args.task, result)
    print("Codex 已完成，并写回当前笔记。")


if __name__ == "__main__":
    main()
