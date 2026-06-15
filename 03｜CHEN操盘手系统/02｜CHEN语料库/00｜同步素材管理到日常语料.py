#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import re


CORPUS_DIR = Path(os.environ.get("CHEN_BRAIN_CORPUS_DIR", Path(__file__).resolve().parent))
MATERIALS_DIR = CORPUS_DIR / "素材管理"
TARGET = CORPUS_DIR / "日常语料逐字稿合集.md"
MARKER = "<!-- 素材管理语料合并区 -->"


def normalize_inner(raw: str) -> str:
    raw = raw.replace("\ufeff", "").strip()
    lines: list[str] = []
    for line in raw.splitlines():
        line = line.rstrip()
        heading = re.match(r"^(#+)(\s+.*)$", line)
        if heading:
            line = "#" + heading.group(1) + heading.group(2)
        lines.append(line)
    return "\n".join(lines).strip()


def existing_order(text: str) -> list[str]:
    if MARKER not in text:
        return []
    section = text.split(MARKER, 1)[1]
    stems: list[str] = []
    for match in re.finditer(r"^#\s+\d{2}｜(.+)$", section, re.MULTILINE):
        stems.append(match.group(1).strip())
    return stems


def material_files(previous_order: list[str]) -> list[Path]:
    files = [
        path
        for path in MATERIALS_DIR.glob("*.md")
        if not path.name.startswith(".") and path.name != TARGET.name
    ]
    by_stem = {path.stem: path for path in files}
    ordered: list[Path] = []
    for stem in previous_order:
        path = by_stem.pop(stem, None)
        if path:
            ordered.append(path)
    ordered.extend(sorted(by_stem.values(), key=lambda p: (p.stat().st_mtime, p.name)))
    return ordered


def rebuild() -> None:
    if not TARGET.exists():
        TARGET.write_text("# 日常语料逐字稿合集\n", encoding="utf-8")
    original = TARGET.read_text(encoding="utf-8-sig")
    base = original.split(MARKER, 1)[0].rstrip() if MARKER in original else original.rstrip()
    files = material_files(existing_order(original))

    parts = [
        base,
        "",
        "",
        MARKER,
        "",
        "# 素材管理语料合并区",
        "",
        f"生成日期：{datetime.now().strftime('%Y-%m-%d')}",
        "",
        "合并范围：`03｜CHEN操盘手系统/03｜CHEN语料库/素材管理/` 下当前全部 Markdown 语料文档。",
        "",
        "说明：本区每份素材文档都是同级一级标题；素材内部原有标题统一降一级，避免在 Obsidian 大纲里变成其他文档的子集。",
        "",
        "---",
    ]

    for index, path in enumerate(files, 1):
        parts.extend(
            [
                "",
                f"# {index:02d}｜{path.stem}",
                "",
                f"来源文件：`03｜CHEN操盘手系统/03｜CHEN语料库/素材管理/{path.name}`",
                "",
                "---",
                "",
                normalize_inner(path.read_text(encoding="utf-8-sig")),
                "",
                "---",
            ]
        )

    TARGET.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    rebuild()
