#!/usr/bin/env python3
"""
fix_frontmatter.py — Repair malformed YAML frontmatter for Quartz v4.

Quartz uses js-yaml which strictly requires that ASCII double-quote characters
(U+0022) inside YAML double-quoted strings be escaped as \".
Python's pyyaml is more lenient, so a file can silently break Quartz while
appearing fine to all Python tooling in this repo.

What this script fixes
──────────────────────
  BROKEN:  - "2023-10-30 "The one where..." (unescaped " inside double-quoted value)
  FIXED:   - "2023-10-30 \"The one where..."

What this script does NOT touch
────────────────────────────────
  - Curly/smart quotes " " (U+201C/U+201D) — fine in YAML, left alone
  - Tags, contributors, or any other field without embedded quotes
  - Anything outside the --- frontmatter block
  - Files where no fix is needed

Safety
──────
  --dry-run     Print what would change, write nothing
  --no-backup   Skip .bak creation (default: creates file.md.bak before writing)

Usage
─────
  python fix_frontmatter.py --dry-run
  python fix_frontmatter.py
  python fix_frontmatter.py --no-backup
  python fix_frontmatter.py "D:/some/other/path"   # target a specific directory
"""

import re
import shutil
import sys
import yaml
from pathlib import Path

# Accept an optional positional path argument; default to the vault.
_args     = [a for a in sys.argv[1:] if not a.startswith("--")]
VAULT     = Path(_args[0]) if _args else Path(__file__).resolve().parent / "vault"
DRY_RUN   = "--dry-run"   in sys.argv
NO_BACKUP = "--no-backup" in sys.argv

# ── Core regex ────────────────────────────────────────────────────────────────
#
# Matches a complete YAML line whose value is a double-quoted string:
#
#   Group 1 (prefix):  leading whitespace + "- " (list item)
#                      OR  key name + ": "   (scalar field like title:)
#   Group 2 (inner):   everything between the opening " and the closing "
#   Group 3 (trail):   optional trailing whitespace
#
# The (.*) is greedy → it matches from the first " to the LAST " on the line,
# so "inner" contains any mid-string " characters that we need to escape.
DQ_LINE = re.compile(r'^((?:\s*-\s+|[\w][\w_-]*:\s+))"(.*)"(\s*)$')


def has_unescaped_quote(s: str) -> bool:
    """True if s contains an ASCII double-quote not preceded by backslash."""
    return bool(re.search(r'(?<!\\)"', s))


def escape_inner_quotes(s: str) -> str:
    """Escape every unescaped ASCII double-quote in s as \\\"."""
    return re.sub(r'(?<!\\)"', '\\"', s)


def fix_frontmatter(fm_raw: str) -> tuple[str, list[str]]:
    """
    Scan the raw frontmatter text (between the --- markers) and fix broken lines.
    Returns (fixed_text, list_of_human_readable_change_descriptions).
    """
    lines = fm_raw.split("\n")
    new_lines = []
    changes = []

    for i, line in enumerate(lines, start=1):
        m = DQ_LINE.match(line)
        if m:
            prefix, inner, trail = m.group(1), m.group(2), m.group(3)
            if has_unescaped_quote(inner):
                fixed_inner = escape_inner_quotes(inner)
                new_line = f'{prefix}"{fixed_inner}"{trail}'
                changes.append(
                    f"  line {i:>3}  BEFORE: {line.rstrip()[:100]!r}\n"
                    f"            AFTER:  {new_line.rstrip()[:100]!r}"
                )
                new_lines.append(new_line)
                continue
        new_lines.append(line)

    return "\n".join(new_lines), changes


def process_file(md: Path) -> bool:
    """
    Read, fix, and (if not dry-run) write one file.
    Returns True if a change was made or would be made.
    """
    text = md.read_text(encoding="utf-8", errors="replace")

    if not text.startswith("---"):
        return False
    end = text.find("\n---\n", 3)
    if end == -1:
        return False

    fm_raw = text[3:end]
    body   = text[end + 5:]

    fixed_fm, changes = fix_frontmatter(fm_raw)
    if not changes:
        return False

    rel = md.relative_to(VAULT)
    print(f"\n{'[DRY RUN] ' if DRY_RUN else ''}Fixing: {rel}")
    for c in changes:
        print(c)

    if DRY_RUN:
        return True

    if not NO_BACKUP:
        shutil.copy2(md, md.with_suffix(md.suffix + ".bak"))

    md.write_text("---" + fixed_fm + "\n---\n" + body, encoding="utf-8")
    return True


def main():
    if DRY_RUN:
        print("=== DRY RUN — nothing will be written ===")

    total_checked = 0
    total_fixed   = 0

    for md in sorted(VAULT.rglob("*.md")):
        total_checked += 1
        if process_file(md):
            total_fixed += 1

    verb = "Would fix" if DRY_RUN else "Fixed"
    print(f"\n-----------------------------------------")
    print(f"Checked {total_checked} files.  {verb} {total_fixed}.")

    if not DRY_RUN and total_fixed:
        if not NO_BACKUP:
            print("Backups written as .md.bak  (delete them once build succeeds).")
        print("\nNext: cd d:/osgog/quartz && npx quartz build")


if __name__ == "__main__":
    main()
