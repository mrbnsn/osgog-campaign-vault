# The Black Lake of Osgog — Campaign Wiki

A MediaWiki-backed D&D campaign wiki, published as a static website via
[Quartz v4](https://quartz.jzhao.xyz/) and GitHub Pages.

**Live site:** https://mrbnsn.github.io/osgog-campaign-vault/

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
│   └── deploy.yml          ← GitHub Actions deployment pipeline
├── convert_wiki.py         ← MediaWiki XML → Obsidian Markdown
├── fix_frontmatter.py      ← Fix YAML quote issues post-conversion
├── autolink.py             ← Auto-wrap entity mentions in [[wikilinks]]
├── apply_tags.py           ← Batch-apply tags to character/lore notes
├── tag_sessions.py         ← Apply thematic tags to session notes
└── find_ghost_nodes.py     ← Find unresolved wikilinks
```

---

## Weekly sync workflow

The wiki at http://osgog.mrobinson.us is the source of truth for campaign
content. Roughly once a week, run the sync script and push to deploy.

### Step 1 — Run the sync script

```powershell
python sync.py
```

This does everything in one shot:
1. Fetches all page titles from the MediaWiki API
2. Downloads a full XML export via Special:Export
3. Converts XML → Obsidian Markdown
4. Fixes YAML frontmatter quoting issues
5. Auto-links entity mentions in note bodies
6. Reports any unresolved wikilinks to review

If you already have a fresh XML dump and want to skip the download:

```powershell
python sync.py --no-fetch
```

### Step 2 — Review changes and ghost nodes

Check what changed:

```powershell
git diff --name-only
git status --short
```

New files appear as `?? vault/...`, modified files as `M vault/...`.

If `sync.py` reported any unresolved wikilinks, fix them in Obsidian
before committing (create the missing note, or add the right alias to
an existing one), then re-run `python find_ghost_nodes.py` to confirm.

### Step 3 — Preview locally

```powershell
cd quartz
npx quartz build --serve
```

Open http://localhost:8080/ and spot-check the changed pages.

### Step 4 — Commit and push

```powershell
git add vault/
git commit -m "Sync wiki export YYYY-MM-DD"
git push
```

GitHub Actions picks up the push and deploys automatically. Watch progress at:
https://github.com/mrbnsn/osgog-campaign-vault/actions

The deployment takes about 2–3 minutes.

---

## Scripts reference

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

Always run `--dry-run` first and review the proposed changes.

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

## Local development

Requirements: [Node.js](https://nodejs.org/) 22+, Python 3.11+

```powershell
# First time only — install Quartz dependencies
cd quartz
npm install

# Build and serve
npx quartz build --serve
# → http://localhost:8080/
```

The `baseUrl` in `quartz/quartz.config.ts` is set to `mrbnsn.github.io` for
local use. The CI pipeline rewrites it to the full sub-path before deploying.

---

## Deployment

Deployment is fully automated. Push any commit to `main` and GitHub Actions:

1. Rewrites `baseUrl` to `mrbnsn.github.io/osgog-campaign-vault`
2. Runs `npx quartz build --directory <path-to-vault>`
3. Uploads `quartz/public/` as a Pages artifact
4. Deploys to https://mrbnsn.github.io/osgog-campaign-vault/

The workflow is defined in `.github/workflows/deploy.yml`.

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
5. Commit and push.
