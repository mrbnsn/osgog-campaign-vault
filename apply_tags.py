#!/usr/bin/env python3
"""
apply_tags.py — Batch-apply thematic tags to vault notes.
Adds only missing tags; never removes or duplicates existing ones.
Usage: python apply_tags.py              # apply
       python apply_tags.py --dry-run    # preview only
"""

import re
import sys
import yaml
from pathlib import Path

VAULT   = Path("d:/osgog/The Black Lake of Osgog")
DRY_RUN = "--dry-run" in sys.argv

# ── Tag assignments ──────────────────────────────────────────────────────────
TAG_MAP = {
    # 00 Hub
    "00 Hub/The Cradle.md":                          ["cradle", "black-water", "osgog-dragon"],
    "00 Hub/The World.md":                           ["cradle", "gorg-gwen"],
    "00 Hub/Player Characters.md":                   ["party/balz", "party/branwen", "party/silas",
                                                      "party/storr", "party/krambler"],
    # 02 Characters/NPCs
    "02 Characters/NPCs/Myrthn.md":                  ["song-magic", "bear-born"],
    "02 Characters/NPCs/Doldhelan.md":               ["mother-night", "gorg-gwen", "osgog-dragon"],
    "02 Characters/NPCs/Mabmnoss.md":                ["mother-night", "raven", "derwen", "gorg-gwen"],
    "02 Characters/NPCs/The Boatman.md":             ["boatman", "mornaswydh", "cradle"],
    "02 Characters/NPCs/The God King.md":            ["gorg-gwen", "harvest-king", "mother-night"],
    "02 Characters/NPCs/Gorgomog.md":                ["gorg-gwen", "harvest-king"],
    "02 Characters/NPCs/Derwen.md":                  ["derwen", "mother-night", "raven"],
    "02 Characters/NPCs/Twrseren.md":                ["twrseren", "sisterhood", "nyth"],
    "02 Characters/NPCs/The Abbot.md":               ["well", "derwen", "bear-born"],
    "02 Characters/NPCs/Kelynnen.md":                ["sisterhood"],
    "02 Characters/NPCs/Seren.md":                   ["sisterhood", "party/silas"],
    "02 Characters/NPCs/Glasses Girl.md":            ["twrseren"],
    # 02 Characters/Players
    "02 Characters/Players/Balthazar.md":            ["party/balz", "horned", "black-water"],
    "02 Characters/Players/Silas.md":                ["party/silas", "bear-born", "arthyden"],
    "02 Characters/Players/Branwen.md":              ["party/branwen", "mother-night", "raven"],
    "02 Characters/Players/Storr.md":                ["party/storr"],
    "02 Characters/Players/Krambler.md":             ["party/krambler"],
    # 03 Locations
    "03 Locations/Osgog.md":                         ["osgog-dragon", "black-water", "cradle"],
    "03 Locations/Nyth.md":                          ["nyth"],
    "03 Locations/Taymar.md":                        ["nyth"],
    "03 Locations/Under the Waterfall.md":           ["nyth"],
    "03 Locations/Tawesek.md":                       ["well", "derwen", "bear-born"],
    "03 Locations/Men Myghtern.md":                  ["well"],
    "03 Locations/Raven Island.md":                  ["raven", "derwen"],
    "03 Locations/Derwen Trees.md":                  ["derwen", "raven"],
    # 04 Lore
    "04 Lore/The Black Water.md":                    ["black-water", "cradle"],
    "04 Lore/The Black Lake of Osgog.md":            ["black-water", "osgog-dragon", "cradle"],
    "04 Lore/The Mornaswydh.md":                     ["mornaswydh", "boatman"],
    "04 Lore/Religions.md":                          ["gorg-gwen", "harvest-king", "mother-night", "osgog-dragon"],
    "04 Lore/Bears.md":                              ["bear-born", "arthyden", "cradle", "well"],
    "04 Lore/Crone, Woman, Child Stone, Sea, and Storm.md": ["three-women", "well"],
    "04 Lore/Circles, Sacred Groves, and Wells.md":  ["well", "cradle", "derwen"],
    "04 Lore/Ceridwen.md":                           ["mother-night", "gorg-gwen", "osgog-dragon"],
    "04 Lore/Mother Night.md":                       ["mother-night", "raven", "derwen"],
    "04 Lore/God of Death.md":                       ["mother-night", "gorg-gwen"],
    "04 Lore/Ancient Tree.md":                       ["cradle", "well"],
    "04 Lore/The One Where Balz Gets Crowned the Harvest King.md":
                                                     ["harvest-king", "party/balz"],
    "04 Lore/Traditions we know about and how they might interpret various stories, poems, etc...md":
                                                     ["gorg-gwen", "three-women", "sisterhood",
                                                      "bear-born", "osgog-dragon"],
    # 05 Battles
    "05 Battles/Mons and the God of Death.md":       ["gorg-gwen", "harvest-king"],
    "05 Battles/The Red Guard and the Red Blade (Battle).md": ["red-blade"],
    # 06 Items
    "06 Items/Bronze Items.md":                      ["bronze"],
    "06 Items/Bone Flute.md":                        ["song-magic"],
    "06 Items/Party Items.md":                       ["mornaswydh", "boatman", "raven"],
    # 07 Stories & Writing
    "07 Stories & Writing/Osgog and the Dragon.md":  ["osgog-dragon", "weaving", "mother-night"],
    "07 Stories & Writing/Songs.md":                 ["song-magic", "weaving"],
    "07 Stories & Writing/Silas' Conspiracy Corner.md":
                                                     ["party/silas", "arthyden", "bear-born", "black-water"],
    "07 Stories & Writing/Branwen's Branches.md":    ["party/branwen", "three-women", "derwen", "raven"],
    "07 Stories & Writing/Illuminated Manuscript.md": ["red-blade", "weaving"],
    "07 Stories & Writing/The Red Blade (Illuminated Manuscript Story).md": ["red-blade"],
    # 08 Campaign Meta
    "08 Campaign Meta/Overview.md":                  ["boatman", "mornaswydh", "black-water", "cradle"],
    "08 Campaign Meta/The Story So Far (Boyz Bop 2022 to The Abbott's Hut).md":
                                                     ["bear-born", "arthyden", "gorg-gwen", "boatman"],
    "08 Campaign Meta/Chapter One.md":               ["well", "derwen", "bear-born"],
    "08 Campaign Meta/Shadow Scars.md":              ["black-water", "cradle"],
}


# ── Frontmatter helpers ──────────────────────────────────────────────────────

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
    skipped = []

    for rel, tags in TAG_MAP.items():
        md = VAULT / rel
        if not md.exists():
            skipped.append(rel)
            continue
        n = apply_tags(md, tags, DRY_RUN)
        if n:
            total += n
            files += 1

    if skipped:
        print("\nNot found (skipped):")
        for s in skipped:
            print(f"  {s}")

    verb = "Would add" if DRY_RUN else "Added"
    print(f"\n{verb} {total} tags across {files} files.")


if __name__ == "__main__":
    main()
