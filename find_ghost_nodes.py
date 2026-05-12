import re
from pathlib import Path

VAULT = Path("d:/osgog/The Black Lake of Osgog")

# All existing note stems (lowercased for case-insensitive match)
existing = {f.stem.lower() for f in VAULT.rglob("*.md")}

# Collect aliases from frontmatter
alias_re = re.compile(r'^\s+- ["\']?(.+?)["\']?\s*$', re.MULTILINE)
aliases = set()
for f in VAULT.rglob("*.md"):
    text = f.read_text(encoding="utf-8", errors="ignore")
    fm_end = text.find("\n---\n", 3)
    if fm_end == -1:
        continue
    fm = text[3:fm_end]
    if "aliases:" not in fm:
        continue
    aliases_section = fm[fm.find("aliases:"):]
    for m in alias_re.finditer(aliases_section):
        aliases.add(m.group(1).strip().lower())

resolvable = existing | aliases

# Find all wikilink targets in note bodies
wikilink_re = re.compile(r"(?<!!)\[\[([^\]|#]+)")
unresolved: dict[str, list[str]] = {}

for md in sorted(VAULT.rglob("*.md")):
    text = md.read_text(encoding="utf-8", errors="ignore")
    fm_end = text.find("\n---\n", 3)
    body = text[fm_end + 4:] if fm_end != -1 else text
    rel = str(md.relative_to(VAULT))
    for m in wikilink_re.finditer(body):
        target = m.group(1).strip().rstrip("\\")  # strip trailing \ from table-escaped pipes
        if target.startswith("["):                 # skip [[[ — wikilink inside a Markdown hyperlink
            continue
        if target.lower() not in resolvable:
            unresolved.setdefault(target, []).append(rel)

print(f"Unresolved wikilink targets: {len(unresolved)}\n")
for target in sorted(unresolved, key=lambda t: (-len(unresolved[t]), t)):
    sources = unresolved[target]
    print(f"  [[{target}]]  ({len(sources)} ref(s))")
    for s in sources[:3]:
        print(f"    <- {s}")
    if len(sources) > 3:
        print(f"    ... and {len(sources) - 3} more")
