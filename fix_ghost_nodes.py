#!/usr/bin/env python3
"""
Fix mechanical ghost nodes:
  1. [[image.jpg]] -> ![[image.jpg]]  for all files in _attachments
  2. Session Archive title mismatches -> regenerated with exact filenames
  3. Near-miss aliases added to existing notes
  4. Path-prefixed links [[04 Lore/X]] -> [[X]]
"""

import re
import yaml
from pathlib import Path

VAULT   = Path("d:/osgog/The Black Lake of Osgog")
ATTACH  = VAULT / "_attachments"

# ─── 1. Convert [[image]] wikilinks to ![[image]] embeds ─────────────────────
attach_names = {f.name for f in ATTACH.iterdir()}
# case-insensitive lookup
attach_lower = {f.name.lower(): f.name for f in ATTACH.iterdir()}

def fix_image_wikilinks(text: str) -> tuple[str, int]:
    count = 0
    def replace(m: re.Match) -> str:
        nonlocal count
        inner = m.group(1)
        ext = inner.rsplit(".", 1)[-1].lower() if "." in inner else ""
        if ext in ("jpg", "jpeg", "png", "gif", "webp", "svg"):
            canonical = attach_lower.get(inner.lower())
            if canonical:
                count += 1
                return f"![[{canonical}]]"
        return m.group(0)
    text = re.sub(r"(?<!!)\[\[([^\]|#]+)\]\]", replace, text)
    return text, count


# ─── 2. Fix path-prefixed wikilinks [[folder/Note]] -> [[Note]] ──────────────
def fix_path_prefixed(text: str) -> tuple[str, int]:
    # Match [[XX Folder/Note Name]] or [[XX Folder/Note Name|alias]]
    pat = re.compile(r"\[\[\d{2} [^/\]]+/([^\]|]+)(\|[^\]]*)?\]\]")
    count = len(pat.findall(text))
    text = pat.sub(lambda m: f"[[{m.group(1)}{m.group(2) or ''}]]", text)
    return text, count


# ─── 3. Near-miss aliases to add to existing notes ───────────────────────────
# Format: {existing_note_stem: [alias, alias, ...]}
ALIASES_TO_ADD = {
    "Songs":            ["Song"],
    # Sun King is a separate antagonist (not The God King / Gorgomog)
    "Fellowship Phases":["fellowship phase", "Fellowship Phase",
                         "Fellowship Rating", "Fellowship rating"],
    # Adventuring Phase is the *opposite* of Fellowship Phase — different concept
    # Safe Havens = where fellowship phases happen; Undertakings = what you do there
    "Kelynnen":         ["Kelynnan"],
    "Carrantok":        ["Carantock"],
    "Gwrydh":           ["Gwreydh"],
    "Bremphyr":         ["Bremfyr"],
    "The Mornaswydh":   ["the Mornaswydh"],
    "Bronze Items":     [],  # already fixed by path-prefix fix
    # Shadow Scars.md does not exist — leaving as intentional stub
    # Undertakings/Safe Havens are different concepts — not aliasing
}

def add_aliases_to_file(md: Path, new_aliases: list[str]) -> int:
    if not md.exists():
        return 0
    text = md.read_text(encoding="utf-8")
    added = 0
    for alias in new_aliases:
        if f'"{alias}"' in text:
            continue
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
        added += 1
    if added:
        md.write_text(text, encoding="utf-8")
    return added


# ─── 4. Rebuild Session Archive with exact filenames ─────────────────────────
def rebuild_session_archive():
    session_root = VAULT / "01 Sessions"
    years = {}
    for md in session_root.rglob("*.md"):
        year = md.parent.name
        text = md.read_text(encoding="utf-8", errors="ignore")
        fm_end = text.find("\n---\n", 3)
        if fm_end == -1:
            continue
        try:
            fm = yaml.safe_load(text[3:fm_end])
        except Exception:
            continue
        years.setdefault(year, []).append((md.stem, fm.get("title", md.stem)))

    archive_path = VAULT / "00 Hub" / "Session Archive.md"
    old = archive_path.read_text(encoding="utf-8")

    # Rebuild only the year tables (keep frontmatter + intro)
    fm_end = old.find("\n---\n", 3) + 4
    header_end = old.find("\n## 2023")
    preamble = old[fm_end:header_end] if header_end != -1 else old[fm_end:fm_end+200]

    lines = [old[:fm_end], preamble.rstrip(), "\n"]

    YEAR_INTROS = {
        "2023": "## 2023 — The Beginning (22 sessions)\n\nThe party forms, [[Cricket]] dies, [[The Boatman]] speaks. The world opens up.",
        "2024": "## 2024 — Into the Wilds (30 sessions)\n\nDungeon under a funeral pyre, fellowship phases, shadow scars, islands, and the Sun King's cronies.",
        "2025": "## 2025 — Deeper Waters (18 sessions)\n\nWaterfalls, ravens, a level 20 druid, eggs, turtles, and questions finally getting answered.",
        "2026": "## 2026 — Present Day (3+ sessions)",
    }

    for year in sorted(years):
        sessions = sorted(years[year], key=lambda x: x[0])
        lines.append("\n---\n")
        lines.append(YEAR_INTROS.get(year, f"## {year}"))
        lines.append("\n")
        lines.append("| Date | Session |")
        lines.append("|---|---|")
        for stem, title in sessions:
            date_part = stem[:10]
            lines.append(f"| {date_part} | [[{stem}]] |")

    archive_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Rebuilt Session Archive with {sum(len(v) for v in years.values())} exact links")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=== 1. Fix [[image]] -> ![[image]] ===")
    img_total = 0
    for md in sorted(VAULT.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        new_text, n = fix_image_wikilinks(text)
        if n:
            md.write_text(new_text, encoding="utf-8")
            img_total += n
            print(f"  {n} fix(es): {md.relative_to(VAULT)}")
    print(f"  Total: {img_total} image wikilinks converted\n")

    print("=== 2. Fix path-prefixed wikilinks ===")
    path_total = 0
    for md in sorted(VAULT.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        new_text, n = fix_path_prefixed(text)
        if n:
            md.write_text(new_text, encoding="utf-8")
            path_total += n
            print(f"  {n} fix(es): {md.relative_to(VAULT)}")
    print(f"  Total: {path_total} path-prefix links fixed\n")

    print("=== 3. Add near-miss aliases ===")
    alias_total = 0
    for stem, aliases in ALIASES_TO_ADD.items():
        if not aliases:
            continue
        found = list(VAULT.rglob(f"{stem}.md"))
        if not found:
            print(f"  NOTE NOT FOUND: {stem}.md")
            continue
        n = add_aliases_to_file(found[0], aliases)
        if n:
            alias_total += n
            print(f"  +{n} alias(es) -> {stem}.md")
    print(f"  Total: {alias_total} aliases added\n")

    print("=== 4. Rebuild Session Archive ===")
    rebuild_session_archive()

    print("\nDone.")

if __name__ == "__main__":
    main()
