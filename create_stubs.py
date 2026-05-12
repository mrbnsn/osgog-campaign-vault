#!/usr/bin/env python3
"""
Resolve remaining ghost nodes:
  1. Add aliases to existing notes (Waterfall City, the boatman)
  2. De-link accidental wikilinks (descriptive phrases)
  3. Create minimal stub notes for NPCs, locations, lore, items, battles
  4. Move Council.md from vault root to 08 Campaign Meta/
  5. Fix [[The Grass / Onion guys]] link in Battles.md
  6. Create game-mechanic stubs with aliases
"""

import re
import shutil
from pathlib import Path

VAULT = Path("d:/osgog/The Black Lake of Osgog")
TODAY = "2026-05-12"


# ─── 1. Add aliases to existing notes ────────────────────────────────────────

def add_alias(md: Path, alias: str) -> bool:
    if not md.exists():
        print(f"  NOT FOUND: {md.relative_to(VAULT)}")
        return False
    text = md.read_text(encoding="utf-8")
    if f'"{alias}"' in text:
        return False  # already present
    aliases_block = re.search(r"^aliases:\n((?:  - .*\n)*)", text, re.MULTILINE)
    if aliases_block:
        insert_at = aliases_block.end()
        text = text[:insert_at] + f'  - "{alias}"\n' + text[insert_at:]
    else:
        text = re.sub(
            r"^(last_edited:)",
            f'aliases:\n  - "{alias}"\n\\1',
            text, count=1, flags=re.MULTILINE,
        )
    md.write_text(text, encoding="utf-8")
    return True


ALIAS_FIXES = {
    VAULT / "03 Locations/The Waterfall City.md": ["Waterfall City"],
    VAULT / "02 Characters/NPCs/The Boatman.md":  ["the boatman", "Boatman"],
}


# ─── 2. De-link narrative phrases ────────────────────────────────────────────

DELINKS = {
    VAULT / "05 Battles/Mons and the God of Death.md": [
        "a chariot pulled by demons of shadow",
        "black butterflies with purple eyes on their wings",
        "great axe made of glittering stone",
        "the earth will shake",
    ],
    VAULT / "04 Lore/Religions.md": [
        "balanced stone",
        "monster",
    ],
}


def delink_phrases(md: Path, phrases: list[str]) -> int:
    text = md.read_text(encoding="utf-8")
    count = 0
    for phrase in phrases:
        pattern = r"\[\[" + re.escape(phrase) + r"\]\]"
        new_text = re.sub(pattern, phrase, text, flags=re.IGNORECASE)
        if new_text != text:
            count += 1
            text = new_text
    if count:
        md.write_text(text, encoding="utf-8")
    return count


# ─── 3. Stub note definitions ─────────────────────────────────────────────────

def make_stub(path: Path, title: str, type_: str, tags: list[str],
              aliases: list[str] = None) -> bool:
    if path.exists():
        print(f"  SKIP (exists): {path.relative_to(VAULT)}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    alias_lines = "\n".join(f'  - "{a}"' for a in (aliases or [title]))
    tag_lines   = "\n".join(f'  - "{t}"' for t in tags)
    text = f"""---
title: "{title}"
type: {type_}
tags:
{tag_lines}
aliases:
{alias_lines}
last_edited: {TODAY}
---

*Stub — no content yet.*
"""
    path.write_text(text, encoding="utf-8")
    return True


NPC_STUBS = [
    ("Kel",                        ["Kel"]),
    ("Seren",                      ["Seren"]),
    ("Angarad",                    ["Angarad"]),
    ("Elowen",                     ["Elowen"]),
    ("Jacca",                      ["Jacca"]),
    ("Moon King",                  ["Moon King"]),
    ("Sun King",                   ["Sun King"]),
    ("The Oracle",                 ["The Oracle", "Oracle"]),
    ("Red Guard",                  ["Red Guard"]),
    ("7-Faced Man",                ["7-Faced Man"]),
    ("Black Willem and Lady Fiona",["Black Willem and Lady Fiona",
                                    "Black Willem", "Lady Fiona"]),
]

LOCATION_STUBS = [
    ("Elder Lands",  ["Elder Lands"]),
    ("Raven Island", ["Raven Island"]),
    ("Derwen Trees", ["Derwen Trees", "Derwen"]),
]

LORE_STUBS = [
    ("God of Death",  ["God of Death"]),
    ("Mother Night",  ["Mother Night"]),
]

ITEM_STUBS = [
    ("Scepter of Stone",           ["Scepter of Stone"]),
    ("Crown of Water",             ["Crown of Water"]),
    ("Cloak of Wind",              ["Cloak of Wind"]),
    ("Sword of Darkness Edged in Light", ["Sword of Darkness Edged in Light"]),
    ("Bone Flute",                 ["Bone Flute", "bone flute"]),
]

BATTLE_STUBS = [
    ("The Giant Tree thing that Turned EVIL (Battle)",
     ["The Giant Tree thing that Turned EVIL (Battle)"]),
    ("Monsoth Mafia (Battle)",
     ["Monsoth Mafia (Battle)"]),
    ("The Fire Knights (Battle)",
     ["The Fire Knights (Battle)"]),
    ("The Grass - Onion guys (Battle)",  # / is illegal; dash used instead
     ["The Grass - Onion guys (Battle)", "The Grass / Onion guys (Battle)"]),
    ("The Scary Shadow Thing in the Tower (Battle)",
     ["The Scary Shadow Thing in the Tower (Battle)"]),
    ("The Soldiers who came through the Well (Battle)",
     ["The Soldiers who came through the Well (Battle)"]),
    ("The Stone Knights (Battle)",
     ["The Stone Knights (Battle)"]),
    ("The Water Knights (Battle)",
     ["The Water Knights (Battle)"]),
    ("The Wind Knight (Battle)",
     ["The Wind Knight (Battle)"]),
    ("The Winter Man Fighter and the Ice Dagger Monk Lady (Battle)",
     ["The Winter Man Fighter and the Ice Dagger Monk Lady (Battle)"]),
    ("Three Big Bears (Battle)",
     ["Three Big Bears (Battle)"]),
    ("Three more Big Bears (Battle)",
     ["Three more Big Bears (Battle)"]),
    ("Various Experiments on Innocent animals (Battle)",
     ["Various Experiments on Innocent animals (Battle)"]),
]

MECHANIC_STUBS = [
    ("Adventuring Phase",
     ["Adventuring Phase", "Adventuring Phases"],
     "meta"),
    ("Safe Havens",
     ["Safe Havens", "Safe Haven", "safe haven"],
     "meta"),
    ("Shadow Scars",
     ["Shadow Scars", "Shadow Scar", "Shadow Points and Scars", "Shadow Points"],
     "meta"),
]


# ─── 4. Fix [[The Grass / Onion guys]] link in Battles.md ────────────────────

def fix_battles_grass_link():
    battles = VAULT / "05 Battles/Battles.md"
    text = battles.read_text(encoding="utf-8")
    old = "[[The Grass / Onion guys (Battle)]]"
    new = "[[The Grass - Onion guys (Battle)]]"
    if old in text:
        battles.write_text(text.replace(old, new), encoding="utf-8")
        print("  Fixed Battles.md: [[The Grass / Onion guys]] → dash")


# ─── 5. Move Council.md from vault root ──────────────────────────────────────

def move_council():
    src  = VAULT / "Council.md"
    dest = VAULT / "08 Campaign Meta" / "Council.md"
    if src.exists() and not dest.exists():
        shutil.move(str(src), str(dest))
        print("  Moved Council.md → 08 Campaign Meta/")
    elif not src.exists():
        print("  Council.md not at root (already moved?)")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=== 1. Add aliases to existing notes ===")
    for md, aliases in ALIAS_FIXES.items():
        for alias in aliases:
            if add_alias(md, alias):
                print(f"  +alias '{alias}' -> {md.name}")
    print()

    print("=== 2. De-link narrative phrases ===")
    for md, phrases in DELINKS.items():
        n = delink_phrases(md, phrases)
        if n:
            print(f"  {n} de-link(s): {md.relative_to(VAULT)}")
    print()

    print("=== 3a. NPC stubs ===")
    for title, aliases in NPC_STUBS:
        path = VAULT / "02 Characters/NPCs" / f"{title}.md"
        if make_stub(path, title, "character", ["character", "npc"], aliases):
            print(f"  + {title}.md")

    print("\n=== 3b. Location stubs ===")
    for title, aliases in LOCATION_STUBS:
        path = VAULT / "03 Locations" / f"{title}.md"
        if make_stub(path, title, "location", ["location"], aliases):
            print(f"  + {title}.md")

    print("\n=== 3c. Lore stubs ===")
    for title, aliases in LORE_STUBS:
        path = VAULT / "04 Lore" / f"{title}.md"
        if make_stub(path, title, "lore", ["lore"], aliases):
            print(f"  + {title}.md")

    print("\n=== 3d. Item stubs ===")
    for title, aliases in ITEM_STUBS:
        path = VAULT / "06 Items" / f"{title}.md"
        if make_stub(path, title, "item", ["item"], aliases):
            print(f"  + {title}.md")

    print("\n=== 3e. Battle stubs ===")
    for title, aliases in BATTLE_STUBS:
        path = VAULT / "05 Battles" / f"{title}.md"
        if make_stub(path, title, "battle", ["battle", "combat"], aliases):
            print(f"  + {title}.md")

    print("\n=== 4. Game mechanic stubs ===")
    for title, aliases, type_ in MECHANIC_STUBS:
        path = VAULT / "08 Campaign Meta" / f"{title}.md"
        if make_stub(path, title, type_, ["meta"], aliases):
            print(f"  + {title}.md")

    print("\n=== 5. Fix Battles.md link ===")
    fix_battles_grass_link()

    print("\n=== 6. Move Council.md ===")
    move_council()

    print("\nDone.")


if __name__ == "__main__":
    main()
