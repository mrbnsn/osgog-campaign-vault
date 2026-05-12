#!/usr/bin/env python3
"""
Download images from the live MediaWiki API and update vault notes.

Steps:
  1. Collect all image names referenced as callouts in the vault
  2. Query the MediaWiki API (in batches) for direct download URLs
  3. Download each image to _attachments/
  4. Replace > [!note] Image: `name` callouts with ![[name]] embeds
"""

import json
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path

VAULT_ROOT  = Path("d:/osgog/The Black Lake of Osgog")
ATTACHMENTS = VAULT_ROOT / "_attachments"
API_BASE    = "http://osgog.mrobinson.us/api.php"
BATCH_SIZE  = 25   # MediaWiki allows up to 50 titles per query

CALLOUT_RE  = re.compile(
    r"> \[!note\] Image: `([^`]+)`\n?",
    re.MULTILINE
)

# ─── Step 1: collect all image names from vault ───────────────────────────────
def collect_image_names() -> dict[str, list[Path]]:
    """Returns {image_name: [list of .md files that reference it]}."""
    refs: dict[str, list[Path]] = {}
    for md_file in VAULT_ROOT.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        for m in CALLOUT_RE.finditer(text):
            name = m.group(1)
            refs.setdefault(name, []).append(md_file)
    return refs


# ─── Step 2: query API for download URLs ─────────────────────────────────────
def fetch_image_urls(names: list[str]) -> dict[str, str]:
    """Query the MediaWiki API in batches; return {name: direct_url}."""
    url_map: dict[str, str] = {}

    for i in range(0, len(names), BATCH_SIZE):
        batch = names[i : i + BATCH_SIZE]
        # Build titles param: "File:Name1|File:Name2|..."
        titles = "|".join(f"File:{n}" for n in batch)
        params = urllib.parse.urlencode({
            "action":  "query",
            "titles":  titles,
            "prop":    "imageinfo",
            "iiprop":  "url",
            "format":  "json",
        })
        req_url = f"{API_BASE}?{params}"
        try:
            req = urllib.request.Request(
                req_url,
                headers={"User-Agent": "OsgogWikiConverter/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"  API error for batch {i//BATCH_SIZE + 1}: {e}")
            continue

        pages = data.get("query", {}).get("pages", {})
        # Also handle normalized titles (spaces ↔ underscores)
        normalized = {
            n["from"].replace("File:", ""): n["to"].replace("File:", "")
            for n in data.get("query", {}).get("normalized", [])
        }

        for page in pages.values():
            title = page.get("title", "").replace("File:", "")
            imageinfo = page.get("imageinfo", [])
            if not imageinfo:
                # Try to map back via normalized
                orig = next((k for k, v in normalized.items() if v == title), title)
                print(f"  WARNING: no URL for '{orig}'")
                continue
            direct_url = imageinfo[0]["url"]
            # Store under the original name (unnormalized)
            orig = next((k for k, v in normalized.items() if v == title), title)
            url_map[orig]   = direct_url
            url_map[title]  = direct_url   # also store normalised form

        time.sleep(0.1)  # be polite to the server

    return url_map


# ─── Step 3: download images ──────────────────────────────────────────────────
def download_images(url_map: dict[str, str], names: list[str]) -> dict[str, Path]:
    """Download each image; return {name: local_path}."""
    ATTACHMENTS.mkdir(parents=True, exist_ok=True)
    local: dict[str, Path] = {}

    for name in names:
        url = url_map.get(name)
        if not url:
            print(f"  SKIP (no URL): {name}")
            continue

        dest = ATTACHMENTS / name
        if dest.exists():
            print(f"  EXISTS: {name}")
            local[name] = dest
            continue

        try:
            headers = {"User-Agent": "OsgogWikiConverter/1.0"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            dest.write_bytes(data)
            kb = len(data) // 1024
            print(f"  Downloaded ({kb} KB): {name}")
            local[name] = dest
        except Exception as e:
            print(f"  FAILED: {name} — {e}")
        time.sleep(0.05)

    return local


# ─── Step 4: update vault notes ───────────────────────────────────────────────
def update_notes(refs: dict[str, list[Path]], downloaded: dict[str, Path]) -> int:
    """Replace callouts with Obsidian image embeds; return count of replacements."""
    replacements = 0

    # Build a set of all files that need updating
    files_to_update: dict[Path, None] = {}
    for name, paths in refs.items():
        if name in downloaded:
            for p in paths:
                files_to_update[p] = None

    for md_file in files_to_update:
        text = md_file.read_text(encoding="utf-8")
        original = text

        def replace_callout(m: re.Match) -> str:
            img_name = m.group(1)
            if img_name in downloaded:
                return f"![[{img_name}]]\n"
            return m.group(0)  # leave unchanged if not downloaded

        text = CALLOUT_RE.sub(replace_callout, text)
        if text != original:
            md_file.write_text(text, encoding="utf-8")
            count = original.count("[!note] Image:") - text.count("[!note] Image:")
            replacements += count
            print(f"  Updated ({count} image(s)): {md_file.relative_to(VAULT_ROOT)}")

    return replacements


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=== Step 1: Scanning vault for image references ===")
    refs = collect_image_names()
    names = sorted(refs.keys())
    print(f"Found {len(names)} unique images across {sum(len(v) for v in refs.values())} note references.\n")

    print("=== Step 2: Querying MediaWiki API for download URLs ===")
    url_map = fetch_image_urls(names)
    found = sum(1 for n in names if n in url_map)
    print(f"Resolved {found}/{len(names)} URLs.\n")

    print("=== Step 3: Downloading images to _attachments/ ===")
    downloaded = download_images(url_map, names)
    print(f"Downloaded {len(downloaded)} images.\n")

    print("=== Step 4: Updating vault notes ===")
    total = update_notes(refs, downloaded)
    print(f"\nDone. {total} callout(s) replaced with image embeds.")

    # Report anything that couldn't be resolved
    missing = [n for n in names if n not in downloaded]
    if missing:
        print(f"\nImages not downloaded ({len(missing)}):")
        for n in missing:
            print(f"  - {n}")


if __name__ == "__main__":
    main()
