#!/usr/bin/env python3
"""
MediaWiki XML → Obsidian Markdown converter
The Black Lake of Osgog Campaign Wiki
"""

import xml.etree.ElementTree as ET
import re
import os
import sys
from pathlib import Path
from datetime import datetime

# ─── Paths ────────────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent
XML_FILE   = _REPO_ROOT / "black-lake-osgog-wiki-dump.xml"
VAULT_ROOT = _REPO_ROOT / "vault"

# ─── Folder structure ─────────────────────────────────────────────────────────
FOLDERS = [
    "00 Hub",
    "01 Sessions/2023",
    "01 Sessions/2024",
    "01 Sessions/2025",
    "01 Sessions/2026",
    "02 Characters/Players",
    "02 Characters/NPCs",
    "03 Locations",
    "04 Lore",
    "05 Battles",
    "06 Items",
    "07 Stories & Writing",
    "08 Campaign Meta",
    "09 Reference",
    "_attachments",
]

# ─── Classification rules ─────────────────────────────────────────────────────
SESSION_RE = re.compile(
    r"^(\d{1,2})/(\d{1,2})/(\d{2,4})\b"
)

PLAYER_CHARACTERS = {
    "Balthazar", "Balz", "Branwen", "Silas", "Storr", "Krambler", "Aled",
    "Logan",
}

NPC_NAMES = {
    "Cricket", "The Boatman", "Musk", "The Abbot", "The Abbott", "Gorgomog",
    "Mannix", "Myrthn", "Lianna", "Mag", "Mali", "Dama", "Tee Dubs",
    "Merthyn", "Mochyn", "Mog", "Mons", "Noorglass", "Rhiannon", "Torval",
    "Weyland", "The God King", "Kosoleth", "Bardh", "Foamflower", "Geshwa",
    "Glasses Girl", "Kelynnen", "Kerenja", "Kevnis", "Bryok", "Broggy",
    "Bremphyr", "Carrantok", "Den", "Derwen", "Gwanethen", "Gwedhen",
    "Gwrydh", "Henavek (man) & Beryan (woman)", "Mabmnoss", "Prydyh",
    "The Red Blade (NPC)", "Tewlder", "Twrseren",
}

LOCATION_NAMES = {
    "Nyth", "Osgog", "Monsoth", "Meander", "Taymar", "The Cradle",
    "Trenewydh", "Tawesek", "Trevas", "Celliwig", "Din Menydh", "Doldhelan",
    "Doldhelen", "The Waterfall City", "The Haunted Tower", "The Black Lake",
    "The Wicked Isles of Oobyrnyn", "The Tree Island", "The Poet's Rest",
    "Men Myghtern", "The Trilithon", "Lake of the Eye of Night",
    "Mysterious Places (and Some Less Mysterious)", "Under the Waterfall",
    "The Hill of Voices", "Crochenwen", "Priweythva",
}

LORE_NAMES = {
    "Religions", "Constellations", "The God King", "Bears", "Centaurs",
    "Elementals", "Circles, Sacred Groves, and Wells", "Bronze Items",
    "Crone, Woman, Child / Stone, Sea, and Storm",
    "Adapted LOTR Features", "The Black Water", "The Mornaswydh",
    "Traditions we know about and how they might interpret various stories, poems, etc..",
    "Ancient Tree", "Big Overarching Questions",
}

BATTLE_NAMES = {
    "Battles", "Mali & Co. (Battle)", "Ruffians on the Road to Tawesek (Battle)",
    "The Red Guard and the Red Blade (Battle)", "The Stone Giant (Battle)",
    "The Stone Turtle (Battle)", "Two Punks from Trenewydh (Battle)",
    "Mons and Bargos", "Mons and the God of Death",
}

ITEM_NAMES = {
    "Party Items", "Bronze Items",
}

WRITING_NAMES = {
    "Songs", "Poems from the Dark Tower", "Various Writings",
    "Illuminated Manuscript", "The Red Blade (Illuminated Manuscript Story)",
    "Osgog: The Novel", "Osgog and the Dragon", "How Old Brother Found Fire",
    "Riddle from the Haunted Tower", "Runic Messages",
    "Balthazar's Thoughts", "Silas' Conspiracy Corner",
    "Cricket's Conspiracy Corner", "Branwen's Branches",
    "Bedtime Storries",
}

META_NAMES = {
    "Campaign Log", "Fellowship Phases", "Chapter One", "Overview",
    "The Story So Far (Boyz Bop 2022 to The Abbott's Hut)",
    "Catch up", "Existing log", "Decision Points", "Undertakings",
    "Big Overarching Questions", "Chess Games", "Maps",
    "For May 30th session: Bardh and the Fellowship Phase undertakings",
    "Balthazar's Thoughts",
}

# Meta / skip pages
SKIP_TITLES = {
    "Main Page", "24 Pages of Monday Morning QBing",
    "31 Pages of Monday Morning QBing",
}


# ─── WikiText → Markdown conversion ──────────────────────────────────────────
def wikitext_to_markdown(text: str, title: str = "") -> str:
    if not text:
        return ""

    # Remove __TOC__, __NOTOC__, etc.
    text = re.sub(r"__[A-Z_]+__", "", text)

    # Handle <nowiki> sections – protect, then restore
    nowiki_chunks = {}
    def save_nowiki(m):
        key = f"\x00NOWIKI{len(nowiki_chunks)}\x00"
        nowiki_chunks[key] = m.group(1)
        return key
    text = re.sub(r"<nowiki>(.*?)</nowiki>", save_nowiki, text, flags=re.DOTALL)

    # Strip comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Convert File / Image links to a plain note (they won't exist in vault)
    text = re.sub(
        r"\[\[(?:File|Image):([^\|\]]+)(?:\|[^\]]*?)?\]\]",
        lambda m: f"> [!note] Image: `{m.group(1)}`\n",
        text, flags=re.IGNORECASE
    )

    # Strip category links (captured for frontmatter separately)
    text = re.sub(r"\[\[Category:[^\]]*\]\]", "", text)

    # Strip wikipedia: links, keeping the display text if present
    text = re.sub(
        r"\[\[wikipedia:([^\|\]]+)\|([^\]]+)\]\]",
        r"\2",
        text
    )
    text = re.sub(r"\[\[wikipedia:([^\]]+)\]\]", r"\1", text)

    # Convert wikilinks with alt text: [[Target|Display]] → [[Target|Display]]
    # (Obsidian supports this natively – leave as-is)

    # External links: [url text] → [text](url)
    text = re.sub(
        r"\[(\bhttps?://[^\s\]]+)\s+([^\]]+)\]",
        r"[\2](\1)",
        text
    )
    # bare external link
    text = re.sub(r"\[(\bhttps?://[^\s\]]+)\]", r"\1", text)

    # Headings: == H2 == → ## H2  etc.
    for level in range(6, 1, -1):
        eq = "=" * level
        text = re.sub(
            rf"^{eq}\s*(.*?)\s*{eq}\s*$",
            lambda m, l=level: "#" * l + " " + m.group(1),
            text, flags=re.MULTILINE
        )

    # Bold+italic: '''''text''''' → ***text***
    text = re.sub(r"'{5}(.+?)'{5}", r"***\1***", text)
    # Bold: '''text''' → **text**
    text = re.sub(r"'{3}(.+?)'{3}", r"**\1**", text)
    # Italic: ''text'' → *text*
    text = re.sub(r"'{2}(.+?)'{2}", r"*\1*", text)

    # Definition lists: ; term → **term**,  : definition → (indent)
    text = re.sub(r"^;\s*(.+)$", r"**\1**", text, flags=re.MULTILINE)
    text = re.sub(r"^:\s(.+)$", r"  \1", text, flags=re.MULTILINE)

    # Unordered lists: * → -
    text = re.sub(r"^\*{3}\s*", "      - ", text, flags=re.MULTILINE)
    text = re.sub(r"^\*{2}\s*", "   - ", text, flags=re.MULTILINE)
    text = re.sub(r"^\*\s*", "- ", text, flags=re.MULTILINE)

    # Ordered lists: # → 1.
    text = re.sub(r"^#{3}\s*", "      1. ", text, flags=re.MULTILINE)
    text = re.sub(r"^#{2}\s*", "   1. ", text, flags=re.MULTILINE)
    text = re.sub(r"^#\s*", "1. ", text, flags=re.MULTILINE)

    # Horizontal rule
    text = re.sub(r"^-{4,}$", "---", text, flags=re.MULTILINE)

    # HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&nbsp;", " ")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")

    # HTML tags
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<hr\s*/?>", "---", text, flags=re.IGNORECASE)

    # Blockquotes: convert each line inside to > prefix
    def blockquote_to_md(m):
        inner = m.group(1).strip()
        return "\n".join(
            ("> " + line) if line.strip() else ">"
            for line in inner.split("\n")
        )
    text = re.sub(r"<blockquote[^>]*>(.*?)</blockquote>",
                  blockquote_to_md, text, flags=re.DOTALL | re.IGNORECASE)

    text = re.sub(r"</?(?:div|span|p|center|small|big|s|del|ins|u|tt|code|pre|ref)[^>]*>",
                  "", text, flags=re.IGNORECASE)
    text = re.sub(r"<ref[^>]*/?>", "", text, flags=re.IGNORECASE)

    # Simple wiki tables → markdown tables (best-effort)
    text = convert_tables(text)

    # Templates: strip {{template|...}} blocks (keep content if it looks useful)
    # Named infobox-style templates – just strip
    text = re.sub(r"\{\{[^{}]*\}\}", "", text, flags=re.DOTALL)
    # Nested templates (two passes)
    text = re.sub(r"\{\{[^{}]*\}\}", "", text, flags=re.DOTALL)

    # Restore nowiki
    for key, val in nowiki_chunks.items():
        text = text.replace(key, val)

    # Collapse 3+ blank lines → 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def convert_tables(text: str) -> str:
    """Best-effort MediaWiki table → Markdown table."""
    def replace_table(m):
        raw = m.group(0)
        rows = []
        header_done = False
        current_row = []
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("{|") or line.startswith("|}") or line.startswith("|+"):
                continue
            elif line.startswith("|-"):
                if current_row:
                    rows.append(current_row)
                    current_row = []
            elif line.startswith("!"):
                cells = re.split(r"!!|\|", line[1:])
                current_row.extend(c.strip() for c in cells)
                header_done = True
            elif line.startswith("|"):
                cells = re.split(r"\|\|", line[1:])
                current_row.extend(c.strip() for c in cells)
            else:
                current_row.append(line)
        if current_row:
            rows.append(current_row)

        if not rows:
            return ""

        max_cols = max(len(r) for r in rows)
        md_rows = []
        for i, row in enumerate(rows):
            padded = row + [""] * (max_cols - len(row))
            md_rows.append("| " + " | ".join(padded) + " |")
            if i == 0:
                md_rows.append("|" + "---|" * max_cols)
        return "\n".join(md_rows)

    return re.sub(
        r"\{\|.*?\|\}",
        replace_table,
        text,
        flags=re.DOTALL
    )


def extract_categories(text: str) -> list[str]:
    return re.findall(r"\[\[Category:([^\]|]+?)(?:\|[^\]]*)?\]\]", text)


# ─── Page classification ──────────────────────────────────────────────────────
def classify_page(title: str, ns: int, categories: list[str]) -> tuple[str, str, list[str]]:
    """Return (subfolder, page_type, tags)."""
    tags = [c.lower().replace(" ", "-") for c in categories]

    # Skip / meta namespaces
    if ns not in (0, 14):
        return None, None, []

    if title in SKIP_TITLES:
        return None, None, []

    # Category namespace → reference
    if ns == 14:
        return "09 Reference", "category", tags + ["reference", "category"]

    # Session logs
    m = SESSION_RE.match(title)
    if m:
        year_raw = m.group(3)
        year = int(year_raw) + 2000 if len(year_raw) == 2 else int(year_raw)
        return f"01 Sessions/{year}", "session", tags + ["session", f"year-{year}"]

    if title in PLAYER_CHARACTERS:
        return "02 Characters/Players", "character", tags + ["character", "player-character"]

    if title in NPC_NAMES:
        return "02 Characters/NPCs", "character", tags + ["character", "npc"]

    if title in LOCATION_NAMES:
        return "03 Locations", "location", tags + ["location"]

    if title in BATTLE_NAMES:
        return "05 Battles", "battle", tags + ["battle", "combat"]

    if title in ITEM_NAMES:
        return "06 Items", "item", tags + ["item"]

    if title in WRITING_NAMES:
        return "07 Stories & Writing", "writing", tags + ["writing"]

    if title in META_NAMES:
        return "08 Campaign Meta", "meta", tags + ["meta"]

    if title in LORE_NAMES:
        return "04 Lore", "lore", tags + ["lore"]

    # Catch-all heuristics from category membership
    cat_lower = [c.lower() for c in categories]
    if any(c in cat_lower for c in ["session logs", "sessions", "session"]):
        return "01 Sessions/2023", "session", tags + ["session"]
    if any(c in cat_lower for c in ["characters", "npcs", "player characters"]):
        subfolder = "02 Characters/NPCs" if "npcs" in cat_lower else "02 Characters/Players"
        return subfolder, "character", tags + ["character"]
    if any(c in cat_lower for c in ["locations", "places"]):
        return "03 Locations", "location", tags + ["location"]
    if any(c in cat_lower for c in ["battles", "combat"]):
        return "05 Battles", "battle", tags + ["battle"]

    # Default: lore
    return "04 Lore", "lore", tags + ["lore"]


# ─── Filename sanitisation ────────────────────────────────────────────────────
def safe_filename(title: str) -> str:
    # Replace characters illegal in Windows filenames
    name = re.sub(r'[<>:"/\\|?*]', "-", title)
    # Replace multiple spaces/dashes
    name = re.sub(r"[-\s]+", " ", name).strip(" -")
    # Obsidian max path is generous; truncate at 150 chars just in case
    if len(name) > 150:
        name = name[:147] + "..."
    return name + ".md"


# ─── YAML front-matter builder ────────────────────────────────────────────────
def build_frontmatter(title: str, page_type: str, tags: list[str],
                       timestamp: str, contributors: list[str]) -> str:
    # Deduplicate + sort tags, remove empties
    clean_tags = sorted({t.strip() for t in tags if t.strip()})
    tag_yaml = "\n".join(f'  - "{t}"' for t in clean_tags)

    date_str = timestamp[:10] if timestamp else ""
    contrib_yaml = "\n".join(f'  - "{c}"' for c in contributors) if contributors else '  - "unknown"'

    # Aliases: title itself (useful for wikilinks with different capitalisation)
    alias_yaml = f'  - "{title}"'

    fm = f"""---
title: "{title.replace('"', "'")}"
type: {page_type}
tags:
{tag_yaml}
aliases:
{alias_yaml}
last_edited: {date_str}
contributors:
{contrib_yaml}
---

"""
    return fm


# ─── Main conversion ──────────────────────────────────────────────────────────
NS_PREFIX = "http://www.mediawiki.org/xml/export-0.11/"

def ns(tag):
    return f"{{{NS_PREFIX}}}{tag}"


def parse_and_convert():
    print(f"Parsing {XML_FILE} ...")
    tree = ET.parse(XML_FILE)
    root = tree.getroot()

    # Create folders
    for folder in FOLDERS:
        (VAULT_ROOT / folder).mkdir(parents=True, exist_ok=True)

    pages_written = 0
    pages_skipped = 0
    title_to_path: dict[str, str] = {}  # for link verification later

    for page in root.findall(ns("page")):
        title_el = page.find(ns("title"))
        ns_el    = page.find(ns("ns"))
        if title_el is None:
            continue

        title    = title_el.text or ""
        ns_num   = int(ns_el.text) if ns_el is not None else 0

        # Get latest revision
        revisions = page.findall(ns("revision"))
        if not revisions:
            pages_skipped += 1
            continue
        rev = revisions[-1]

        text_el = rev.find(ns("text"))
        raw_text = text_el.text if text_el is not None else ""

        timestamp_el = rev.find(ns("timestamp"))
        timestamp = timestamp_el.text if timestamp_el is not None else ""

        # Contributors (all revisions)
        contributors = []
        for r in revisions:
            contrib_el = r.find(f"{ns('contributor')}/{ns('username')}")
            if contrib_el is not None and contrib_el.text:
                contributors.append(contrib_el.text)
        contributors = sorted(set(contributors))

        # Extract categories before conversion
        categories = extract_categories(raw_text or "")

        # Classify
        subfolder, page_type, tags = classify_page(title, ns_num, categories)
        if subfolder is None:
            pages_skipped += 1
            print(f"  SKIP: {title}")
            continue

        # Convert wikitext
        md_body = wikitext_to_markdown(raw_text or "", title)

        # Build file
        frontmatter = build_frontmatter(title, page_type, tags, timestamp, contributors)
        content = frontmatter + md_body

        filename = safe_filename(title)
        out_path = VAULT_ROOT / subfolder / filename

        out_path.write_text(content, encoding="utf-8")
        title_to_path[title] = str(out_path.relative_to(VAULT_ROOT))
        pages_written += 1
        print(f"  OK  [{subfolder}] {filename}")

    print(f"\nDone. {pages_written} pages written, {pages_skipped} skipped.")
    return title_to_path


if __name__ == "__main__":
    title_to_path = parse_and_convert()
