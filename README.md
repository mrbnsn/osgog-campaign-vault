# The Black Lake of Osgog — Campaign Wiki

A MediaWiki-backed D&D campaign wiki, published as a static website via
[Quartz v4](https://quartz.jzhao.xyz/) and GitHub Pages.

**Live site:** https://mrbnsn.github.io/osgog-campaign-vault/

---

## First-time setup

Requirements: [Node.js](https://nodejs.org/) 22+, Python 3.11+,
[GitHub CLI (`gh`)](https://cli.github.com/)

```powershell
# 1. Clone the repo
git clone https://github.com/mrbnsn/osgog-campaign-vault.git
cd osgog-campaign-vault

# 2. Install Quartz dependencies (only needed once, or after Quartz updates)
cd quartz
npm install
cd ..

# 3. Authenticate the GitHub CLI (only needed once)
gh auth login
```

---

## Repository structure

```
osgog/
├── vault/                  ← Obsidian vault (all campaign content)
│   ├── 00 Hub/
│   ├── 01 Sessions/
│   ├── 02 Characters/
│   ├── 03 Locations/
│   ├── 04 Lore/
│   ├── 05 Battles/
│   ├── 06 Items/
│   ├── 07 Stories & Writing/
│   ├── 08 Campaign Meta/
│   ├── 09 Reference/
│   ├── _attachments/
│   └── index.md
├── quartz/                 ← Quartz static site generator
│   ├── quartz.config.ts    ← site configuration
│   └── quartz.layout.ts    ← layout configuration
├── .github/workflows/
│   ├── deploy.yml          ← GitHub Actions deployment pipeline
│   └── sync.yml            ← Automated daily wiki sync
├── sync.py                 ← One-command weekly sync (see below)
├── convert_wiki.py         ← MediaWiki XML → Obsidian Markdown
├── fix_frontmatter.py      ← Fix YAML quote issues post-conversion
├── autolink.py             ← Auto-wrap entity mentions in [[wikilinks]]
├── apply_tags.py           ← Batch-apply tags to character/lore notes
├── tag_sessions.py         ← Apply thematic tags to session notes
└── find_ghost_nodes.py     ← Find unresolved wikilinks
```

---

## Sync workflow

The wiki at http://osgog.mrobinson.us is the source of truth for campaign
content. Syncing is fully automated — a GitHub Actions workflow runs every
night at 2am UTC, pulls the latest wiki content, and pushes any changes
directly to `main`, which triggers a fresh site deploy.

`sync.py` does the following in sequence:

| # | What | Script |
|---|------|--------|
| 1 | Fetches all page titles from the MediaWiki API | *(built-in)* |
| 2 | Downloads a full XML export via `Special:Export` | *(built-in)* |
| 3 | Converts the XML into Obsidian Markdown files | `convert_wiki.py` |
| 4 | Fixes any YAML frontmatter quoting issues | `fix_frontmatter.py` |
| 5 | Auto-links entity mentions in note bodies | `autolink.py` |
| 6 | Reports any unresolved wikilinks to review | `find_ghost_nodes.py` |

If there are no changes since the last sync, the workflow exits silently
with no commit.

### Trigger a sync manually

To sync immediately without waiting for the nightly run, go to:

**Actions → Daily Wiki Sync → Run workflow**

at https://github.com/mrbnsn/osgog-campaign-vault/actions

### Run the sync locally

```powershell
python sync.py            # full sync (fetches from wiki + commits + pushes)
python sync.py --no-fetch # skip XML download, use existing dump
python sync.py --no-pr    # sync files only, skip git step
```

### Fix ghost nodes (if any)

If the sync reported unresolved wikilinks, fix them in Obsidian
(create the missing note, or add the right alias to an existing one).
Re-run `python find_ghost_nodes.py` to confirm they're resolved, then commit
directly to `main`.

---

## Local preview

To preview the site locally before or after a sync:

```powershell
cd quartz
npm run serve
```

Open http://localhost:8080/ in your browser.

---

## Scripts reference

### `sync.py`
The main entry point for the sync workflow. Orchestrates all the steps below
in sequence. Normally runs automatically via GitHub Actions, but can also be
run locally. See the [Sync workflow](#sync-workflow) section above for full details.

### `convert_wiki.py`
Converts a MediaWiki XML export into Obsidian-flavoured Markdown. Classifies
each page into the correct vault subfolder based on title and wiki categories.
Writes YAML frontmatter with `title`, `type`, `tags`, `aliases`,
`last_edited`, and `contributors`.

**Input:** `black-lake-osgog-wiki-dump.xml` (repo root)  
**Output:** files written into `vault/`

### `fix_frontmatter.py`
Scans all `.md` files in the vault and escapes any unescaped ASCII `"`
characters inside YAML double-quoted strings. Quartz's YAML parser is stricter
than Python's, so without this step certain pages fail to build.

```powershell
python fix_frontmatter.py             # fix in place (creates .bak files)
python fix_frontmatter.py --dry-run   # preview changes without writing
python fix_frontmatter.py --no-backup # fix without creating .bak files
```

### `autolink.py`
Scans all vault notes for plain-text mentions of known entities (characters,
locations, lore, battles, items) and wraps them in `[[wikilinks]]`. Uses
entity names and aliases from the `02–06` folders as its source list.

Always run `--dry-run` first when running manually to review proposed changes.

```powershell
python autolink.py --dry-run   # preview
python autolink.py             # apply
```

### `apply_tags.py`
Batch-applies thematic tags to character, location, and lore notes based on
a mapping defined inside the script. Edit `TAG_MAP` to add new rules.

### `tag_sessions.py`
Applies thematic tags to session notes by pattern-matching against session
filenames. Edit `SESSION_TAGS` inside the file to add patterns for new
sessions.

### `find_ghost_nodes.py`
Scans all notes for wikilinks that don't resolve to any file or alias in the
vault. Outputs a list of broken links to fix.

```powershell
python find_ghost_nodes.py
```

---

## Deployment

Deployment is fully automated — any push to `main` (including the nightly sync)
triggers GitHub Actions, which:

1. Rewrites `baseUrl` to `mrbnsn.github.io/osgog-campaign-vault`
2. Builds the site with `npx quartz build`
3. Deploys to https://mrbnsn.github.io/osgog-campaign-vault/

The workflow is defined in `.github/workflows/deploy.yml`. Deployment takes
about 2–3 minutes. Watch progress at:
https://github.com/mrbnsn/osgog-campaign-vault/actions

---

## Adding a new session manually

If a session was written directly in Obsidian (not on the wiki):

1. Create the file in `vault/01 Sessions/YYYY/` following the naming pattern:
   `YYYY-MM-DD The One Where [description].md`
2. Add YAML frontmatter:
   ```yaml
   ---
   title: "MM/DD/YY The One Where [description]"
   type: session
   tags:
     - "session"
     - "year-YYYY"
   last_edited: YYYY-MM-DD
   contributors:
     - "your-name"
   ---
   ```
3. Run `python tag_sessions.py` to apply thematic tags if the session title
   matches any existing patterns.
4. Run `python autolink.py` to wire up entity mentions.
5. Create a branch, commit, and open a PR:
   ```powershell
   git checkout -b add-session-YYYY-MM-DD
   git add vault/
   git commit -m "Add session YYYY-MM-DD"
   git push -u origin add-session-YYYY-MM-DD
   gh pr create --base main
   ```
