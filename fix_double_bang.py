#!/usr/bin/env python3
from pathlib import Path
VAULT = Path("d:/osgog/The Black Lake of Osgog")
total = 0
for md in VAULT.rglob("*.md"):
    text = md.read_text(encoding="utf-8", errors="ignore")
    if "!![[" in text:
        new_text = text.replace("!![[", "![[")
        count = text.count("!![[")
        md.write_text(new_text, encoding="utf-8")
        total += count
        print(f"  {count} fix(es): {md.relative_to(VAULT)}")
print(f"Total double-bang fixes: {total}")
