#!/usr/bin/env python3
"""Rename session files from "M D YY Title.md" to "YYYY-MM-DD Title.md"."""

import re
import os
from pathlib import Path

VAULT_ROOT = Path("d:/osgog/The Black Lake of Osgog")
SESSION_DIRS = [
    VAULT_ROOT / "01 Sessions" / "2023",
    VAULT_ROOT / "01 Sessions" / "2024",
    VAULT_ROOT / "01 Sessions" / "2025",
    VAULT_ROOT / "01 Sessions" / "2026",
]

# Pattern: "M D YY rest" or "M D YYYY rest"
FILENAME_RE = re.compile(r"^(\d{1,2}) (\d{1,2}) (\d{2,4}) (.+)\.md$")

for session_dir in SESSION_DIRS:
    year_from_folder = int(session_dir.name)
    for f in sorted(session_dir.iterdir()):
        if not f.name.endswith(".md"):
            continue
        m = FILENAME_RE.match(f.name)
        if not m:
            # might already be renamed or different format
            continue
        month, day, year_raw, rest = m.groups()
        year = int(year_raw) + 2000 if len(year_raw) == 2 else int(year_raw)
        if year != year_from_folder:
            year = year_from_folder  # use folder year as source of truth
        new_name = f"{year:04d}-{int(month):02d}-{int(day):02d} {rest}.md"
        new_path = f.parent / new_name
        if new_path != f:
            f.rename(new_path)
            print(f"  {f.name}")
            print(f"  -> {new_name}\n")

print("Done renaming sessions.")
