#!/usr/bin/env python3
"""
sync.py — One-command weekly wiki sync.

Steps:
  1. Fetch all page titles from the MediaWiki API
  2. Download full XML export via Special:Export
  3. Convert XML → Obsidian Markdown  (convert_wiki)
  4. Fix YAML frontmatter quoting      (fix_frontmatter)
  5. Auto-link entity mentions         (autolink)
  6. Report any unresolved wikilinks   (find_ghost_nodes)

Usage:
    python sync.py               # full sync (downloads fresh XML)
    python sync.py --no-fetch    # skip download, use existing XML dump
"""

import sys
import urllib.request
import urllib.parse
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

WIKI_BASE  = "http://osgog.mrobinson.us"
REPO_ROOT  = Path(__file__).resolve().parent
XML_FILE   = REPO_ROOT / "black-lake-osgog-wiki-dump.xml"

NO_FETCH = "--no-fetch" in sys.argv

# ── Helpers ───────────────────────────────────────────────────────────────────

def banner(step: int, total: int, title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  Step {step}/{total}: {title}")
    print(f"{'─' * 60}")


# ── Step 1 + 2: Fetch XML dump ────────────────────────────────────────────────

def fetch_all_page_titles() -> list[str]:
    """Return every main-namespace page title via the MediaWiki API."""
    titles: list[str] = []
    params = {
        "action": "query",
        "list": "allpages",
        "aplimit": "max",
        "apnamespace": "0",
        "format": "json",
    }
    url = f"{WIKI_BASE}/api.php"
    while True:
        query = urllib.parse.urlencode(params)
        with urllib.request.urlopen(f"{url}?{query}") as resp:
            import json
            data = json.loads(resp.read())
        titles.extend(p["title"] for p in data["query"]["allpages"])
        cont = data.get("continue", {}).get("apcontinue")
        if not cont:
            break
        params["apcontinue"] = cont
    return titles


def download_xml(titles: list[str]) -> None:
    """POST to Special:Export and save the XML dump."""
    payload = urllib.parse.urlencode({
        "pages": "\n".join(titles),
        "curonly": "1",
        "templates": "0",
        "action": "submit",
    }).encode()
    url = f"{WIKI_BASE}/index.php/Special:Export"
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req) as resp:
        XML_FILE.write_bytes(resp.read())


def step_fetch() -> None:
    print("Fetching page list from MediaWiki API...")
    titles = fetch_all_page_titles()
    print(f"  Found {len(titles)} pages")
    print("Downloading XML export...")
    download_xml(titles)
    size_kb = XML_FILE.stat().st_size // 1024
    print(f"  Saved {XML_FILE.name} ({size_kb} KB)")


# ── Step 3: Convert ───────────────────────────────────────────────────────────

def step_convert() -> None:
    from convert_wiki import parse_and_convert
    parse_and_convert()


# ── Step 4: Fix frontmatter ───────────────────────────────────────────────────

def step_fix_frontmatter() -> None:
    from fix_frontmatter import main as fix_main
    # Patch globals so it uses our vault and skips backups
    import fix_frontmatter as fm_mod
    fm_mod.VAULT      = REPO_ROOT / "vault"
    fm_mod.DRY_RUN    = False
    fm_mod.NO_BACKUP  = True
    fix_main()


# ── Step 5: Autolink ──────────────────────────────────────────────────────────

def step_autolink() -> None:
    from autolink import main as autolink_main
    autolink_main(dry_run=False)


# ── Step 6: Ghost nodes ───────────────────────────────────────────────────────

def step_ghost_nodes() -> None:
    from find_ghost_nodes import find_ghosts
    unresolved = find_ghosts()
    if not unresolved:
        print("  No unresolved wikilinks.")
        return
    print(f"  {len(unresolved)} unresolved wikilink(s) — review before committing:\n")
    for target in sorted(unresolved, key=lambda t: (-len(unresolved[t]), t)):
        sources = unresolved[target]
        print(f"    [[{target}]]  ({len(sources)} ref(s))")
        for s in sources[:2]:
            print(f"      <- {s}")
        if len(sources) > 2:
            print(f"      ... and {len(sources) - 2} more")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    total = 5 if NO_FETCH else 6
    step  = 1

    if not NO_FETCH:
        banner(step, total, "Download wiki XML export")
        step_fetch()
        step += 1

    banner(step, total, "Convert XML → Markdown")
    step_convert()
    step += 1

    banner(step, total, "Fix YAML frontmatter")
    step_fix_frontmatter()
    step += 1

    banner(step, total, "Auto-link entity mentions")
    step_autolink()
    step += 1

    banner(step, total, "Check for unresolved wikilinks")
    step_ghost_nodes()

    print(f"\n{'─' * 60}")
    print("  Sync complete. Review any ghost nodes above, then:")
    print("    git add vault/")
    print('    git commit -m "Sync wiki export YYYY-MM-DD"')
    print("    git push")
    print(f"{'─' * 60}\n")


if __name__ == "__main__":
    main()
