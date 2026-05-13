#!/usr/bin/env python3
"""
sync.py — One-command weekly wiki sync.

What it does:
  1. Fetches all page titles from the MediaWiki API
  2. Downloads a full XML export via Special:Export
  3. Converts XML → Obsidian Markdown  (convert_wiki)
  4. Fixes YAML frontmatter quoting      (fix_frontmatter)
  5. Auto-links entity mentions          (autolink)
  6. Reports any unresolved wikilinks    (find_ghost_nodes)
  7. Creates a git branch, commits vault changes, pushes, and opens a PR

Usage:
    python sync.py               # full sync
    python sync.py --no-fetch    # skip download, use existing XML dump
    python sync.py --no-pr       # skip git/PR step (sync files only)
"""

import json
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

WIKI_BASE = "http://osgog.mrobinson.us"
REPO_ROOT = Path(__file__).resolve().parent
XML_FILE  = REPO_ROOT / "black-lake-osgog-wiki-dump.xml"
GITHUB_REPO = "mrbnsn/osgog-campaign-vault"

NO_FETCH = "--no-fetch" in sys.argv
NO_PR    = "--no-pr"    in sys.argv

# ── Helpers ───────────────────────────────────────────────────────────────────

def banner(step: int, total: int, title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  Step {step}/{total}: {title}")
    print(f"{'─' * 60}")


def run_git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=REPO_ROOT, check=True)


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
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
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
    import fix_frontmatter as fm_mod
    fm_mod.VAULT     = REPO_ROOT / "vault"
    fm_mod.DRY_RUN   = False
    fm_mod.NO_BACKUP = True
    fm_mod.main()


# ── Step 5: Autolink ──────────────────────────────────────────────────────────

def step_autolink() -> None:
    from autolink import main as autolink_main
    autolink_main(dry_run=False)


# ── Step 6: Ghost nodes ───────────────────────────────────────────────────────

def step_ghost_nodes() -> bool:
    """Returns True if there are unresolved links (warning, not a blocker)."""
    from find_ghost_nodes import find_ghosts
    unresolved = find_ghosts()
    if not unresolved:
        print("  No unresolved wikilinks.")
        return False
    print(f"  {len(unresolved)} unresolved wikilink(s) found:\n")
    for target in sorted(unresolved, key=lambda t: (-len(unresolved[t]), t)):
        sources = unresolved[target]
        print(f"    [[{target}]]  ({len(sources)} ref(s))")
        for s in sources[:2]:
            print(f"      <- {s}")
        if len(sources) > 2:
            print(f"      ... and {len(sources) - 2} more")
    print("\n  These won't block the PR — fix them in Obsidian after merging if needed.")
    return True


# ── Step 7: Git branch + PR ───────────────────────────────────────────────────

def step_git_pr(today: str) -> None:
    # Must be on main
    current = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.strip()
    if current != "main":
        print(f"  WARNING: currently on branch '{current}', not 'main'.")
        print("  Switch to main first, or commit manually.")
        return

    # Any vault changes to commit?
    diff = subprocess.run(
        ["git", "status", "--porcelain", "vault/"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.strip()
    if not diff:
        print("  No changes in vault/ — nothing to commit.")
        return

    # Pick a unique branch name
    branch = f"sync/{today}"
    existing = subprocess.run(
        ["git", "branch", "--list", f"sync/{today}*"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.strip()
    if existing:
        branch = f"sync/{today}-{len(existing.splitlines()) + 1}"

    try:
        print(f"  Creating branch {branch}...")
        run_git(["checkout", "-b", branch])
        run_git(["add", "vault/"])
        run_git(["commit", "-m", f"Sync wiki export {today}"])

        print(f"  Pushing to origin/{branch}...")
        run_git(["push", "-u", "origin", branch])

        # Create PR via gh CLI
        try:
            result = subprocess.run(
                [
                    "gh", "pr", "create",
                    "--title", f"Sync wiki export {today}",
                    "--body", (
                        "Automated weekly sync from MediaWiki export.\n\n"
                        "Please review the changes below before merging to `main`."
                    ),
                    "--base", "main",
                ],
                capture_output=True, text=True, cwd=REPO_ROOT, check=True,
            )
            print(f"  PR ready for review: {result.stdout.strip()}")
        except FileNotFoundError:
            print("  gh CLI not found — create a PR manually at:")
            print(f"  https://github.com/{GITHUB_REPO}/compare/{branch}")
        except subprocess.CalledProcessError as e:
            print(f"  PR creation failed: {e.stderr.strip()}")
            print(f"  Branch '{branch}' was pushed — open a PR manually.")

    finally:
        # Always return to main
        subprocess.run(["git", "checkout", "main"], cwd=REPO_ROOT, capture_output=True)
        print("  Returned to main.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    today = date.today().strftime("%Y-%m-%d")
    total = (5 if NO_FETCH else 6) + (0 if NO_PR else 1)
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
    step += 1

    if not NO_PR:
        banner(step, total, "Commit, push, and open PR")
        step_git_pr(today)

    print(f"\n{'─' * 60}")
    if NO_PR:
        print("  Sync complete. Commit and push when ready:")
        print("    git checkout -b sync/" + today)
        print("    git add vault/")
        print(f'    git commit -m "Sync wiki export {today}"')
        print("    git push -u origin sync/" + today)
    else:
        print("  Done. Merge the PR on GitHub when you're happy with the changes.")
        print(f"  {' https://github.com/' + GITHUB_REPO + '/pulls'}")
    print(f"{'─' * 60}\n")


if __name__ == "__main__":
    main()
