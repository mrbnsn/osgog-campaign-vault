#!/usr/bin/env python3
"""
autolink.py  —  Find unlinked plain-text mentions of known entities
and wrap them with [[wikilinks]].

Per-section linking: each entity is linked once per ## section, so
long session notes re-establish links at each new section header.
Possessives are handled: "Balthazar's" -> "[[Balthazar]]'s".

Usage:
    python autolink.py              # apply changes
    python autolink.py --dry-run    # preview only (no files written)
"""

import re
import sys
import yaml
from pathlib import Path

VAULT   = Path(__file__).resolve().parent / "vault"
DRY_RUN = "--dry-run" in sys.argv

# ── Which folders contain notes that are valid LINK TARGETS ─────────────────
TARGET_FOLDERS = [
    "02 Characters",
    "03 Locations",
    "04 Lore",
    "05 Battles",
    "06 Items",
]

# ── Names too generic or ambiguous to auto-link ──────────────────────────────
EXCLUSIONS = {
    # Common English words / meta concepts
    "battles", "bears", "songs", "characters", "religions",
    "elementals", "centaurs", "npcs", "lore", "overview",
    "maps", "monster", "monsters", "items", "locations", "players",
    # Game-mechanic terms (too broad)
    "the world", "undertakings", "fellowship phases", "adventuring phase",
    "safe havens", "shadow scars", "new skills", "journeying", "patrons",
    "council", "fountain",
    # Hub / meta nav labels
    "battles hub", "stories hub", "npcs hub", "lore hub",
    "locations hub", "campaign meta hub", "player characters",
    # Very short / risky
    "the",
}

# ── Placeholder tokens (null-byte delimited integers) ────────────────────────
_PH_RE = re.compile(r"\x00(\d+)\x00")


def _store(m: re.Match, tokens: list) -> str:
    idx = len(tokens)
    tokens.append(m.group(0))
    return f"\x00{idx}\x00"


def protect(text: str) -> tuple[str, list]:
    """Replace wikilinks, image embeds, and code blocks with placeholders."""
    tokens: list[str] = []
    store = lambda m: _store(m, tokens)
    # Code blocks first (may contain brackets)
    text = re.sub(r"```[\s\S]*?```", store, text)
    text = re.sub(r"`[^`\n]+`", store, text)
    # Image embeds before plain wikilinks
    text = re.sub(r"!\[\[(?:[^\]]|\](?!\]))*\]\]", store, text)
    # Plain wikilinks
    text = re.sub(r"\[\[(?:[^\]]|\](?!\]))*\]\]", store, text)
    return text, tokens


def restore(text: str, tokens: list) -> str:
    return _PH_RE.sub(lambda m: tokens[int(m.group(1))], text)


# ── Frontmatter parsing ───────────────────────────────────────────────────────

def split_fm(text: str) -> tuple[dict, str, int]:
    """Returns (frontmatter_dict, body, body_start_offset)."""
    if not text.startswith("---"):
        return {}, text, 0
    end = text.find("\n---\n", 3)
    if end == -1:
        return {}, text, 0
    try:
        fm = yaml.safe_load(text[3:end]) or {}
    except Exception:
        fm = {}
    body_start = end + 5           # skip the closing "\n---\n"
    return fm, text[body_start:], body_start


# ── Build entity map ──────────────────────────────────────────────────────────

def build_entity_map() -> list[tuple[str, str]]:
    """
    Returns [(lowercase_name, canonical_stem), ...] sorted by name-length desc.
    Includes note stems + all frontmatter aliases from TARGET_FOLDERS.
    """
    entities: dict[str, str] = {}

    for folder in TARGET_FOLDERS:
        folder_path = VAULT / folder
        if not folder_path.exists():
            continue
        for md in folder_path.rglob("*.md"):
            stem = md.stem
            text = md.read_text(encoding="utf-8", errors="ignore")
            fm, _, _ = split_fm(text)

            def add(name: str, canonical: str) -> None:
                key = name.strip().lower()
                if key and key not in EXCLUSIONS and len(key) >= 3:
                    entities[key] = canonical

            add(stem, stem)
            for alias in (fm.get("aliases") or []):
                add(str(alias), stem)

    # Longest names first — prevents "Boatman" matching before "The Boatman"
    return sorted(entities.items(), key=lambda kv: len(kv[0]), reverse=True)


# ── Per-segment linker ────────────────────────────────────────────────────────

# Apostrophe variants: ASCII ' and Unicode right-single-quote '
_POSS = r"['’]s"
# Characters that may NOT immediately precede or follow a name match
_NOT_LETTER = r"[a-zA-ZÀ-ɏ]"


def _make_link(canonical: str, matched: str, poss: str) -> str:
    if matched.lower() == canonical.lower():
        return f"[[{canonical}]]{poss}"
    return f"[[{canonical}|{matched}]]{poss}"


def link_segment(segment: str,
                 entity_list: list[tuple[str, str]],
                 self_names: set[str]) -> str:
    """Link first occurrence of each entity in this segment."""
    guarded, tokens = protect(segment)
    linked: set[str] = set()

    for name, canonical in entity_list:
        if name in self_names or name in linked:
            continue

        # If this canonical is already linked anywhere in this segment, don't add another.
        if re.search(r'\[\[' + re.escape(canonical) + r'(?:\||\]\])', segment, re.IGNORECASE):
            linked.add(name)
            continue

        pat = re.compile(
            r"(?<!" + _NOT_LETTER + r")"       # not preceded by letter
            + re.escape(name)
            + r"(?P<poss>" + _POSS + r")?"     # optional possessive
            + r"(?!" + _NOT_LETTER + r"|['’])",  # not followed by letter/apostrophe
            re.IGNORECASE,
        )

        def _repl(m: re.Match,
                  _name: str = name,
                  _can: str = canonical) -> str:
            bare = m.group(0)
            poss = m.group("poss") or ""
            bare = bare[: len(bare) - len(poss)]
            return _make_link(_can, bare, poss)

        new_guarded, n = pat.subn(_repl, guarded, count=1)
        if n:
            # Re-protect newly created [[...]] so later entities don't match inside them
            reprotect = lambda m: _store(m, tokens)
            new_guarded = re.sub(r"!\[\[(?:[^\]]|\](?!\]))*\]\]", reprotect, new_guarded)
            new_guarded = re.sub(r"\[\[(?:[^\]]|\](?!\]))*\]\]", reprotect, new_guarded)
            guarded = new_guarded
            linked.add(name)

    return restore(guarded, tokens)


# ── Section-aware body processor ─────────────────────────────────────────────

_HEADING_RE = re.compile(r"(\n#{1,6} [^\n]*)", re.MULTILINE)


def link_body(body: str,
              entity_list: list[tuple[str, str]],
              self_names: set[str]) -> str:
    """Split body at headings; link each section independently."""
    parts = _HEADING_RE.split(body)
    out = []
    for part in parts:
        if _HEADING_RE.fullmatch(part):
            out.append(part)        # headings pass through unchanged
        else:
            out.append(link_segment(part, entity_list, self_names))
    return "".join(out)


# ── Per-file driver ───────────────────────────────────────────────────────────

def process_note(md: Path,
                 entity_list: list[tuple[str, str]],
                 dry_run: bool) -> int:
    text = md.read_text(encoding="utf-8", errors="ignore")
    fm, body, body_start = split_fm(text)

    self_names: set[str] = {md.stem.lower()}
    for alias in (fm.get("aliases") or []):
        self_names.add(str(alias).strip().lower())

    new_body = link_body(body, entity_list, self_names)
    if new_body == body:
        return 0

    delta = new_body.count("[[") - body.count("[[")

    if dry_run:
        rel = md.relative_to(VAULT)
        print(f"\n--- {rel}  (+{delta} links) ---")
        old_lines = body.splitlines()
        new_lines = new_body.splitlines()
        shown = 0
        for old_l, new_l in zip(old_lines, new_lines):
            if old_l != new_l and shown < 6:
                print(f"  - {old_l.strip()[:130]}")
                print(f"  + {new_l.strip()[:130]}")
                shown += 1
    else:
        md.write_text(text[:body_start] + new_body, encoding="utf-8")

    return delta


# ── Main ─────────────────────────────────────────────────────────────────────

def main(dry_run: bool = DRY_RUN) -> int:
    """Run autolinker. Returns total links added (or that would be added)."""
    print("Building entity map...")
    entity_list = build_entity_map()
    print(f"  {len(entity_list)} names/aliases to match\n")

    if dry_run:
        print("=== DRY RUN — no files will be written ===")

    total_links = 0
    files_changed = 0

    for md in sorted(VAULT.rglob("*.md")):
        n = process_note(md, entity_list, dry_run)
        if n > 0:
            total_links += n
            files_changed += 1
            if not dry_run:
                print(f"  +{n:4d}  {md.relative_to(VAULT)}")

    verb = "Would add" if dry_run else "Added"
    print(f"\n{verb} {total_links} links across {files_changed} files.")
    return total_links


if __name__ == "__main__":
    main()
