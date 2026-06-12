#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import time


HERE = Path(__file__).resolve().parent
SYNC_SCRIPT = HERE / "00｜同步素材管理到日常语料.py"
MATERIALS_DIR = HERE / "素材管理"
PID_FILE = HERE / ".素材管理自动同步.pid"
LOG_FILE = HERE / ".素材管理自动同步.log"
INTERVAL_SECONDS = 3


def snapshot() -> tuple[tuple[str, int, int], ...]:
    files = []
    for path in MATERIALS_DIR.glob("*.md"):
        if path.name.startswith("."):
            continue
        stat = path.stat()
        files.append((path.name, int(stat.st_mtime), stat.st_size))
    return tuple(sorted(files))


def sync() -> None:
    with LOG_FILE.open("a", encoding="utf-8") as log:
        subprocess.run(
            ["/usr/bin/python3", str(SYNC_SCRIPT)],
            cwd=str(HERE.parents[0]),
            stdout=log,
            stderr=log,
            check=False,
        )


def main() -> None:
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    last = snapshot()
    sync()
    while True:
        time.sleep(INTERVAL_SECONDS)
        current = snapshot()
        if current != last:
            sync()
            last = current


if __name__ == "__main__":
    main()
