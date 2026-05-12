#!/usr/bin/env python3
"""Fix wikilinks with characters Obsidian cannot use as filenames."""

import re
from pathlib import Path

VAULT = Path("d:/osgog/The Black Lake of Osgog")


def fix_text_fragments(text: str) -> tuple[str, int]:
    """
    [[Page#:~:text=...|Alias]] → [[Page|Alias]]
    [[Page#:~:text=...]]       → [[Page]]
    """
    count = 0

    def replace(m: re.Match) -> str:
        nonlocal count
        page   = m.group(1)           # everything before #:~:text=
        alias  = m.group(2) or ""     # |Alias part, if present
        count += 1
        return f"[[{page}{alias}]]"

    text = re.sub(
        r"\[\[([^\]#|]+)#:~:text=[^\]|]*(\|[^\]]*)?\]\]",
        replace,
        text,
    )
    return text, count


def fix_talk_links(text: str) -> tuple[str, int]:
    """
    [[Talk:...|Alias]] → Alias   (delink — talk pages don't exist in vault)
    [[Talk:...]]       → (removed entirely)
    """
    count = 0

    def replace(m: re.Match) -> str:
        nonlocal count
        alias = m.group(1)
        count += 1
        return alias if alias else ""

    text = re.sub(
        r"\[\[Talk:[^\]|]*(?:\|([^\]]*))?\]\]",
        replace,
        text,
    )
    return text, count


def fix_colon_filenames(text: str) -> tuple[str, int]:
    """Fix the one wikilink whose target has a colon stripped in the filename."""
    old = "[[For May 30th session: Bardh and the Fellowship Phase undertakings]]"
    new = "[[For May 30th session Bardh and the Fellowship Phase undertakings]]"
    count = text.count(old)
    return text.replace(old, new), count


FIXES = [
    ("text-fragment links", fix_text_fragments),
    ("Talk: links",         fix_talk_links),
    ("colon in filename",   fix_colon_filenames),
]


def main():
    totals = {label: 0 for label, _ in FIXES}
    files_changed = 0

    for md in sorted(VAULT.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        original = text
        file_hits = {}

        for label, fn in FIXES:
            text, n = fn(text)
            if n:
                file_hits[label] = n
                totals[label] += n

        if text != original:
            md.write_text(text, encoding="utf-8")
            files_changed += 1
            rel = md.relative_to(VAULT)
            detail = ", ".join(f"{n} {l}" for l, n in file_hits.items())
            print(f"  [{detail}]  {rel}")

    print(f"\nFiles changed: {files_changed}")
    for label, n in totals.items():
        if n:
            print(f"  {label}: {n} fix(es)")


if __name__ == "__main__":
    main()
