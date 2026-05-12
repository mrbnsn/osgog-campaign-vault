#!/usr/bin/env python3
"""
1. Delete 4 Obsidian-created phantom files at the vault root.
2. Add redirect-source names as aliases in the target files' frontmatter.
3. Delete the now-redundant redirect stub files.
"""

import re
from pathlib import Path

VAULT = Path("d:/osgog/The Black Lake of Osgog")

# ─── 1. Phantom files to delete outright ─────────────────────────────────────
PHANTOMS = [
    VAULT / "Kelynnan.md",
    VAULT / "New Skills.md",
    VAULT / "Patrons.md",
    VAULT / "Various Experiments on Innocent animals (Battle).md",
]

# ─── 2. Redirects: {stub_file: (alias_to_add, target_file)} ──────────────────
REDIRECTS = {
    VAULT / "03 Locations" / "Priweythva.md": (
        "Priweythva",
        VAULT / "03 Locations" / "Crochenwen.md",
    ),
    VAULT / "04 Lore" / "Morianoth.md": (
        "Morianoth",
        VAULT / "02 Characters" / "NPCs" / "Mabmnoss.md",
    ),
    VAULT / "02 Characters" / "NPCs" / "Bryok.md": (
        "Bryok",
        VAULT / "02 Characters" / "NPCs" / "The Abbot.md",
    ),
    VAULT / "02 Characters" / "NPCs" / "The Abbott.md": (
        "The Abbott",
        VAULT / "02 Characters" / "NPCs" / "The Abbot.md",
    ),
    VAULT / "08 Campaign Meta" / "Big Overarching Questions.md": (
        "Big Overarching Questions",
        VAULT / "07 Stories & Writing" / "Cricket's Conspiracy Corner.md",
    ),
}


def add_alias(target: Path, alias: str) -> bool:
    """Insert alias into the target file's YAML frontmatter. Returns True if changed."""
    if not target.exists():
        print(f"  TARGET NOT FOUND: {target.relative_to(VAULT)}")
        return False

    text = target.read_text(encoding="utf-8")

    # Check if alias already present
    if f'"{alias}"' in text or f"- {alias}\n" in text:
        print(f"  Alias already present in {target.name}: {alias!r}")
        return False

    # Insert after the existing aliases: block
    aliases_block = re.search(r"^aliases:\n((?:  - .*\n)+)", text, re.MULTILINE)
    if aliases_block:
        insert_at = aliases_block.end()
        new_text = text[:insert_at] + f'  - "{alias}"\n' + text[insert_at:]
    else:
        # No aliases block — add one before the closing ---
        new_text = re.sub(
            r"^(last_edited:)",
            f'aliases:\n  - "{alias}"\n\\1',
            text,
            count=1,
            flags=re.MULTILINE,
        )

    if new_text != text:
        target.write_text(new_text, encoding="utf-8")
        print(f"  Added alias {alias!r} to {target.relative_to(VAULT)}")
        return True
    return False


def main():
    print("=== Step 1: Delete phantom files ===")
    for p in PHANTOMS:
        if p.exists():
            p.unlink()
            print(f"  Deleted: {p.name}")
        else:
            print(f"  Already gone: {p.name}")

    print("\n=== Step 2: Add aliases to redirect targets ===")
    for stub, (alias, target) in REDIRECTS.items():
        add_alias(target, alias)

    print("\n=== Step 3: Delete redirect stubs ===")
    for stub in REDIRECTS:
        if stub.exists():
            stub.unlink()
            print(f"  Deleted: {stub.relative_to(VAULT)}")
        else:
            print(f"  Already gone: {stub.relative_to(VAULT)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
