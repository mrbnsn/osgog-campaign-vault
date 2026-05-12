#!/usr/bin/env python3
"""
tag_sessions.py — Add 1-3 thematic tags to session notes by matching
case-insensitive substrings against the filename stem.
All patterns for a given session are applied in a single write.
Usage: python tag_sessions.py              # apply
       python tag_sessions.py --dry-run    # preview
"""

import re
import sys
import yaml
from pathlib import Path

VAULT   = Path("d:/osgog/The Black Lake of Osgog")
DRY_RUN = "--dry-run" in sys.argv

# (substring_to_match, [tags])  — case-insensitive; all matching rules applied
SESSION_TAGS = [
    # 2023 ────────────────────────────────────────────────────────────────────
    ("BackInOsgog",                     ["osgog-dragon", "black-water"]),
    ("Grizzly Man",                     ["bear-born"]),
    ("DEBTREE",                         ["derwen"]),
    ("fight bears",                     ["bear-born", "party/silas"]),
    ("left off at the well",            ["well", "party/silas", "party/krambler"]),
    ("waterfall city",                  ["well", "nyth"]),
    ("follow the badger",               ["nyth"]),
    ("Boatman and make our",            ["boatman"]),
    ("hit the festival",                ["harvest-king", "black-water"]),
    ("Cricket's pyre and meet Branwen", ["party/branwen"]),
    # 2024 ────────────────────────────────────────────────────────────────────
    ("dungeon under Cricket",           ["party/branwen"]),
    ("Storr Reads Us A Bedtime",        ["party/storr", "bear-born"]),
    ("Limb Entity",                     ["black-water", "cradle"]),
    ("Map of Nyth",                     ["nyth"]),
    ("The One Where We Journey",        ["mornaswydh"]),
    ("Set Out for the Lake",            ["party/storr", "black-water"]),
    ("Chat With the Boat",              ["boatman", "mornaswydh"]),
    ("Sun King",                        ["harvest-king"]),
    ("Mysteries Island",                ["mornaswydh"]),
    ("Contemplate Trees",               ["party/silas", "party/balz", "derwen"]),
    ("Leave the Island",                ["mornaswydh"]),
    ("Reach the Tower",                 ["twrseren"]),
    ("Eccentric Astronomer",            ["twrseren"]),
    ("Grill Gwen",                      ["twrseren", "sisterhood"]),
    ("Find Out More About Our Hosts",   ["twrseren"]),
    ("Crack Osgog Wide Open",           ["osgog-dragon", "mother-night", "twrseren"]),
    ("Osgog Broke",                     ["osgog-dragon"]),
    ("Harvest Festival",                ["harvest-king"]),
    ("Enjoy the Feast",                 ["harvest-king"]),
    # 2025 ────────────────────────────────────────────────────────────────────
    ("Convalesce at the Waterfall",     ["nyth"]),
    ("Thelma and Louise",               ["nyth"]),
    ("Email Checkin from God",          ["derwen", "raven"]),
    ("Ambivalent Boatman",              ["boatman"]),
    ("tv show LOST",                    ["mornaswydh"]),
    ("Choral Island",                   ["song-magic"]),
    ("Super Chill About Weaving",       ["weaving"]),
    ("Trees and Bees",                  ["derwen"]),
    ("Giant Raven",                     ["raven", "song-magic"]),
    ("Great Bear",                      ["bear-born", "arthyden"]),
    ("Ravened Away",                    ["raven", "bear-born"]),
    ("Level 20 Druid",                  ["bear-born", "song-magic"]),
    ("Part Ways with Myrthn",           ["bear-born", "mornaswydh"]),
]


# ── Frontmatter helpers (identical to apply_tags.py) ─────────────────────────

def split_fm(text):
    if not text.startswith("---"):
        return {}, text, 0, ""
    end = text.find("\n---\n", 3)
    if end == -1:
        return {}, text, 0, ""
    fm_raw = text[3:end]
    try:
        fm = yaml.safe_load(fm_raw) or {}
    except Exception:
        fm = {}
    return fm, text[end + 5:], end + 5, fm_raw


def apply_tags(md: Path, new_tags: list, dry_run: bool) -> int:
    if not new_tags:
        return 0
    text = md.read_text(encoding="utf-8", errors="ignore")
    fm, body, body_start, fm_raw = split_fm(text)
    if not fm_raw:
        return 0

    existing = [str(t) for t in (fm.get("tags") or [])]
    to_add = [t for t in new_tags if t not in existing]
    if not to_add:
        return 0

    tags_block = re.search(r"^tags:\n((?:  - .*\n)*)", fm_raw, re.MULTILINE)
    if tags_block:
        insert_at = tags_block.end()
        addition = "".join(f'  - "{t}"\n' for t in to_add)
        new_fm_raw = fm_raw[:insert_at] + addition + fm_raw[insert_at:]
    else:
        new_fm_raw = re.sub(
            r"^(last_edited:)",
            "tags:\n" + "".join(f'  - "{t}"\n' for t in to_add) + r"\1",
            fm_raw, count=1, flags=re.MULTILINE,
        )

    if dry_run:
        print(f"  {md.relative_to(VAULT)}: +{to_add}")
    else:
        md.write_text("---" + new_fm_raw + "\n---\n" + body, encoding="utf-8")

    return len(to_add)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if DRY_RUN:
        print("=== DRY RUN -- no files will be written ===\n")

    total = 0
    files = 0

    for md in sorted((VAULT / "01 Sessions").rglob("*.md")):
        stem = md.stem.lower()
        matched_tags: list[str] = []
        for pattern, tags in SESSION_TAGS:
            if pattern.lower() in stem:
                matched_tags.extend(tags)
        # deduplicate while preserving order
        seen: set[str] = set()
        unique_tags = [t for t in matched_tags if not (t in seen or seen.add(t))]
        if unique_tags:
            n = apply_tags(md, unique_tags, DRY_RUN)
            if n:
                total += n
                files += 1

    verb = "Would add" if DRY_RUN else "Added"
    print(f"\n{verb} {total} tags across {files} files.")


if __name__ == "__main__":
    main()
