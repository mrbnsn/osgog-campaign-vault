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
content. Roughly once a week, export any changed pages and sync them into
the vault, then push to deploy.

### Step 1 — Export from MediaWiki

1. Go to http://osgog.mrobinson.us/index.php/Special:Export
2. In the **"Add pages manually"** box, you can either:
   - Paste specific page titles (one per line) to export only changed pages, or
   - Check **"Include only the current revision"** and export everything by
     leaving the box empty and using **"Add pages from category"** for bulk exports
3. Leave **"Include only the current revision"** checked (we don't need history)
4. Click **Export** — your browser will download an XML file
5. Save it to `d:/osgog/black-lake-osgog-wiki-dump.xml` (overwrite the existing file)

> **Tip — exporting only recent changes:** On the wiki, visit
> `Special:RecentChanges` to see what's been edited. Note those page titles
> and paste them into the export form to do a targeted export instead of a
> full dump.

### Step 2 — Convert to Obsidian Markdown

Run the converter from the repo root:

```powershell
cd d:/osgog
python convert_wiki.py
```

This parses the XML dump and writes/overwrites `.md` files into `vault/`.
Pages are classified into the correct subfolder automatically (sessions,
characters, locations, etc.) based on their title and wiki categories.

### Step 3 — Check what changed

Before running cleanup, see what git considers modified:

```powershell
git diff --name-only
git status --short
```

This tells you which vault files were actually touched. New files show as `?? vault/...`, modified files as `M vault/...`.

### Step 4 — Run cleanup scripts

Run these from `d:/osgog/` in order:

```powershell
# Fix YAML frontmatter (escaped quotes, encoding issues)
python fix_frontmatter.py

# Auto-link entity mentions (characters, locations, lore) in body text
# Always dry-run first to review proposed changes
python autolink.py --dry-run
python autolink.py

# Check for unresolved wikilinks (ghost nodes)
python find_ghost_nodes.py
```

If `find_ghost_nodes.py` reports broken links, resolve them manually in
Obsidian or by adding the missing note/alias.

> `fix_frontmatter.py` and `autolink.py` are safe to re-run on the full
> vault — they only change files that need it. No data is lost; `.bak`
> backup files are created by default (delete them once things look good).

### Step 5 — Preview locally

```powershell
cd d:/osgog/quartz
npx quartz build --serve
```

Open http://localhost:8080/ in your browser and spot-check the changed pages.

### Step 6 — Commit and push

```powershell
cd d:/osgog
git add vault/
git commit -m "Sync wiki export YYYY-MM-DD"
git push
```

GitHub Actions picks up the push and deploys to GitHub Pages automatically.
The deployment takes about 2–3 minutes. Watch progress at:
`https://github.com/mrbnsn/osgog-campaign-vault/actions`

---

## Scripts reference

### `convert_wiki.py`
Converts a MediaWiki XML export into Obsidian-flavoured Markdown. Classifies
each page into the correct vault subfolder based on its title and categories.
Writes YAML frontmatter with `title`, `type`, `tags`, `aliases`,
`last_edited`, and `contributors`.

**Input:** `black-lake-osgog-wiki-dump.xml`
**Output:** files written into `vault/`

### `fix_frontmatter.py`
Scans all `.md` files in the vault and escapes any unescaped ASCII `"` characters
inside YAML double-quoted strings. Quartz's YAML parser is stricter than Python's,
so without this step certain pages fail to build.

```powershell
python fix_frontmatter.py             # fix in place (creates .bak files)
python fix_frontmatter.py --dry-run   # preview changes without writing
python fix_frontmatter.py --no-backup # fix without creating .bak files
```

### `autolink.py`
Scans all vault notes for plain-text mentions of known entities (characters,
locations, lore, battles, items) and wraps them in `[[wikilinks]]`. Uses
entity names and aliases from the `02–06` folders as its source list.

Always run `--dry-run` first and review the proposed changes before writing.

```powershell
python autolink.py --dry-run   # preview
python autolink.py             # apply
```

### `apply_tags.py`
Batch-applies thematic tags to character, location, and lore notes based on
a mapping in the script. Edit `TAG_MAP` inside the file to add new rules.

### `tag_sessions.py`
Applies thematic tags to session notes by pattern-matching against session
filenames. Edit `SESSION_TAGS` inside the file to add new patterns when new
sessions are added.

### `find_ghost_nodes.py`
Scans all notes for wikilinks that don't resolve to any file or alias in the
vault. Outputs a list of broken links so you can create the missing note or
fix the link.

```powershell
python find_ghost_nodes.py
```

---

## Local development

Requirements: [Node.js](https://nodejs.org/) 22+, Python 3.11+

```powershell
# First time only — install Quartz dependencies
cd d:/osgog/quartz
npm install

# Build and serve
npx quartz build --serve
# → http://localhost:8080/
```

The local build reads content directly from `vault/` and does not affect
the deployed site. The `baseUrl` in `quartz.config.ts` is set to
`mrbnsn.github.io` for local use; the CI pipeline rewrites it to the full
sub-path before deploying.

---

## Deployment

Deployment is fully automated. Push any commit to `main` and GitHub Actions:

1. Rewrites `baseUrl` to `mrbnsn.github.io/osgog-campaign-vault`
2. Runs `npx quartz build --directory $GITHUB_WORKSPACE/vault`
3. Uploads the `quartz/public/` output as a Pages artifact
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
3. Run `python tag_sessions.py` to add thematic tags if the session title
   matches any existing patterns.
4. Run `python autolink.py` to wire up entity mentions.
5. Commit and push.
