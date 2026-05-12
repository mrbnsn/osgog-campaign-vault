#!/usr/bin/env python3
"""
Rewrite old M/D/YY session wikilinks to YYYY-MM-DD format.

The original wiki cross-linked sessions as [[10/9/25 Title]] which Obsidian
reads as a path (folder 10 / folder 9 / file 25 Title), creating stray
directories. This script:
  1. Builds a mapping {original_title → new_stem} from session frontmatter
  2. Rewrites every [[old title]] and [[old title|alias]] in the vault
  3. Also strips #:~:text= anchors (text fragment URLs that Obsidian ignores)
  4. Deletes the stray folders Obsidian already created
"""

import re
import shutil
import yaml
from pathlib import Path

VAULT_ROOT   = Path("d:/osgog/The Black Lake of Osgog")
SESSION_ROOT = VAULT_ROOT / "01 Sessions"

# ─── Step 1: build {original_title → new_file_stem} from frontmatter ─────────
def build_title_map() -> dict[str, str]:
    title_map: dict[str, str] = {}
    for md in SESSION_ROOT.rglob("*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore")
        # Extract YAML frontmatter
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        if end == -1:
            continue
        fm_raw = text[3:end]
        try:
            fm = yaml.safe_load(fm_raw)
        except Exception:
            continue
        original_title = fm.get("title", "")
        if original_title:
            title_map[original_title] = md.stem
    return title_map


# ─── Step 2: build a sorted-longest-first regex from the title map ────────────
def build_pattern(title_map: dict[str, str]) -> re.Pattern:
    # Sort longest first so greedier matches win
    sorted_titles = sorted(title_map.keys(), key=len, reverse=True)
    escaped = [re.escape(t) for t in sorted_titles]
    combined = "|".join(escaped)
    # Match [[title]] [[title|alias]] [[title#anchor]] [[title#anchor|alias]]
    # Also matches #:~:text= fragments (we strip those entirely)
    return re.compile(
        r"\[\[(" + combined + r")((?:#[^\]|]*)?)(\|[^\]]*)?\]\]"
    )


# ─── Step 3: rewrite all vault notes ─────────────────────────────────────────
def rewrite_notes(title_map: dict[str, str], pattern: re.Pattern) -> int:
    total_replacements = 0

    for md in VAULT_ROOT.rglob("*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore")
        original = text

        def replace_link(m: re.Match) -> str:
            old_title   = m.group(1)
            anchor      = m.group(2) or ""   # e.g. "#Some Heading"
            alias_part  = m.group(3) or ""   # e.g. "|Display text"

            new_stem = title_map.get(old_title, old_title)

            # Strip #:~:text= fragments (not valid in Obsidian)
            if "#:~:text=" in anchor:
                anchor = ""

            return f"[[{new_stem}{anchor}{alias_part}]]"

        text = pattern.sub(replace_link, text)

        if text != original:
            count = sum(
                1 for _ in pattern.finditer(original)
            )
            md.write_text(text, encoding="utf-8")
            total_replacements += count
            print(f"  Fixed {count} link(s): {md.relative_to(VAULT_ROOT)}")

    return total_replacements


# ─── Step 4: delete stray folders ─────────────────────────────────────────────
STRAY_ROOTS = [
    VAULT_ROOT / "10",
    VAULT_ROOT / "12",
]

def delete_stray_folders() -> int:
    deleted = 0
    for folder in STRAY_ROOTS:
        if folder.exists() and folder.is_dir():
            # Show what we're removing
            for f in folder.rglob("*"):
                print(f"  Removing: {f.relative_to(VAULT_ROOT)}")
            shutil.rmtree(folder)
            print(f"  Deleted folder: {folder.name}/")
            deleted += 1
    return deleted


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=== Step 1: Building session title map ===")
    title_map = build_title_map()
    print(f"Mapped {len(title_map)} session titles.\n")

    print("=== Step 2: Building replacement pattern ===")
    pattern = build_pattern(title_map)
    print(f"Pattern built.\n")

    print("=== Step 3: Rewriting wikilinks in vault ===")
    total = rewrite_notes(title_map, pattern)
    print(f"\n{total} wikilink(s) rewritten.\n")

    print("=== Step 4: Deleting stray folders ===")
    deleted = delete_stray_folders()
    if deleted == 0:
        print("  No stray folders found.")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
