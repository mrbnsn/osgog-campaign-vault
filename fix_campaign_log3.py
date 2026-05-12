# -*- coding: utf-8 -*-
from pathlib import Path

f = Path("d:/osgog/The Black Lake of Osgog/08 Campaign Meta/Campaign Log.md")
text = f.read_text(encoding="utf-8")

replacements = [
    (
        '[[7/6/23 Working Title:\xa0 “The One Where Ryan Does A One Man Show of Grizzly Man”]]',
        '[[2023-07-06 Working Title “The One Where Ryan Does A One Man Show of Grizzly Man”]]',
    ),
    (
        '[[9/4/23\xa0 “The One Where There Weren’t Enough of Us to Make a Decision…”]]',
        '[[2023-09-04 “The One Where There Weren’t Enough of Us to Make a Decision…”]]',
    ),
]

for old, new in replacements:
    if old in text:
        text = text.replace(old, new)
        count = 1
        import sys
        sys.stdout.buffer.write(("Fixed: " + new[:80] + "\n").encode("utf-8"))
    else:
        sys.stdout.buffer.write(b"NOT FOUND\n")

f.write_text(text, encoding="utf-8")
sys.stdout.buffer.write(b"Done.\n")
