#!/usr/bin/env python3
"""
Sweep the vault for remaining MediaWiki/HTML artifacts and fix them:
  1. <blockquote>...</blockquote>  →  Markdown > blockquote
  2. <nowiki/>                     →  (removed)
  3. \xa0 (non-breaking space)     →  regular space
  4. @TODO                         →  - [ ] TODO
"""

import re
from pathlib import Path

VAULT = Path("d:/osgog/The Black Lake of Osgog")

# ─── Transformations ──────────────────────────────────────────────────────────

def fix_blockquotes(text: str) -> str:
    """Convert <blockquote>...</blockquote> to Markdown > lines."""
    def replace_bq(m: re.Match) -> str:
        inner = m.group(1).strip()
        # Prefix every non-empty line with "> "
        lines = inner.split("\n")
        quoted = "\n".join(
            ("> " + line) if line.strip() else ">"
            for line in lines
        )
        return "\n" + quoted + "\n"

    return re.sub(
        r"<blockquote>(.*?)</blockquote>",
        replace_bq,
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )


def fix_nowiki(text: str) -> str:
    return text.replace("<nowiki/>", "").replace("<nowiki />", "")


def fix_nbsp(text: str) -> str:
    return text.replace("\xa0", " ")


def fix_todo(text: str) -> str:
    return text.replace("@TODO", "- [ ] TODO")


# ─── Pipeline ─────────────────────────────────────────────────────────────────

TRANSFORMS = [
    ("blockquotes",      fix_blockquotes),
    ("<nowiki/>",        fix_nowiki),
    ("non-breaking sp.", fix_nbsp),
    ("@TODO",            fix_todo),
]


def process_file(md: Path) -> list[str]:
    """Apply all transforms; return list of labels that changed something."""
    text = md.read_text(encoding="utf-8", errors="ignore")
    original = text
    applied = []

    for label, fn in TRANSFORMS:
        result = fn(text)
        if result != text:
            applied.append(label)
            text = result

    # Collapse runs of 3+ blank lines that transforms can create
    text = re.sub(r"\n{3,}", "\n\n", text)

    if text != original:
        md.write_text(text, encoding="utf-8")

    return applied


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    totals: dict[str, int] = {label: 0 for label, _ in TRANSFORMS}
    files_changed = 0

    for md in sorted(VAULT.rglob("*.md")):
        applied = process_file(md)
        if applied:
            files_changed += 1
            rel = str(md.relative_to(VAULT))
            print(f"  [{', '.join(applied)}]  {rel}")
            for label in applied:
                totals[label] += 1

    print(f"\nFiles changed: {files_changed}")
    for label, count in totals.items():
        if count:
            print(f"  {label}: {count} file(s)")


if __name__ == "__main__":
    main()
