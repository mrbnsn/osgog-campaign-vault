#!/usr/bin/env python3
import re
from pathlib import Path

VAULT = Path(__file__).resolve().parent / "vault"


def find_ghosts(vault: Path = VAULT) -> dict[str, list[str]]:
    """Return {unresolved_target: [source_files, ...]} for all broken wikilinks."""
    existing = {f.stem.lower() for f in vault.rglob("*.md")}

    alias_re = re.compile(r'^\s+- ["\']?(.+?)["\']?\s*$', re.MULTILINE)
    aliases: set[str] = set()
    for f in vault.rglob("*.md"):
        text = f.read_text(encoding="utf-8", errors="ignore")
        fm_end = text.find("\n---\n", 3)
        if fm_end == -1:
            continue
        fm = text[3:fm_end]
        if "aliases:" not in fm:
            continue
        for m in alias_re.finditer(fm[fm.find("aliases:"):]):
            aliases.add(m.group(1).strip().lower())

    resolvable = existing | aliases
    wikilink_re = re.compile(r"(?<!!)\[\[([^\]|#]+)")
    unresolved: dict[str, list[str]] = {}

    for md in sorted(vault.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        fm_end = text.find("\n---\n", 3)
        body = text[fm_end + 4:] if fm_end != -1 else text
        rel = str(md.relative_to(vault))
        for m in wikilink_re.finditer(body):
            target = m.group(1).strip().rstrip("\\")
            if target.startswith("["):
                continue
            if target.lower() not in resolvable:
                unresolved.setdefault(target, []).append(rel)

    return unresolved


def main() -> None:
    unresolved = find_ghosts()
    print(f"Unresolved wikilink targets: {len(unresolved)}\n")
    for target in sorted(unresolved, key=lambda t: (-len(unresolved[t]), t)):
        sources = unresolved[target]
        print(f"  [[{target}]]  ({len(sources)} ref(s))")
        for s in sources[:3]:
            print(f"    <- {s}")
        if len(sources) > 3:
            print(f"    ... and {len(sources) - 3} more")


if __name__ == "__main__":
    main()
