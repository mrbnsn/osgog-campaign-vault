from pathlib import Path

f = Path("d:/osgog/The Black Lake of Osgog/08 Campaign Meta/Campaign Log.md")
text = f.read_text(encoding="utf-8")

fixes = [
    ('[[7/6/23 Working Title:  “The One Where Ryan Does A One Man Show of Grizzly Man”]]',
     '[[2023-07-06 Working Title “The One Where Ryan Does A One Man Show of Grizzly Man”]]'),
    ('[[9/4/23  “The One Where There Weren’t Enough of Us to Make a Decision…”]]',
     '[[2023-09-04 “The One Where There Weren’t Enough of Us to Make a Decision…”]]'),
    ('[[5/9/24  The One Where We Meet The Limb Entity and  (Some Of Us) Receive Our Shadow Scars]]',
     '[[2024-05-09 The One Where We Meet The Limb Entity and (Some Of Us) Receive Our Shadow Scars]]'),
    ('[[4/30/26  Treneweth #2, Electric Boogaloo (The One Where We Meet Jacca)]]',
     '[[2026-04-30 Treneweth]]'),
]

for old, new in fixes:
    if old in text:
        text = text.replace(old, new)
        print(f"Fixed: {old[:70]}")
    else:
        # Try without the curly quotes (straight quote fallback)
        print(f"NOT FOUND: {repr(old[:70])}")

# Fix the Crew one separately — the curly quote in "Boat's" is tricky
import re
text, n = re.subn(
    r'\[\[7/18/24 The One Where We Chat With the Boat.s .Crew.\]\]',
    '[[2024-07-18 The One Where We Chat With the Boat\'s Crew]]',
    text
)
print(f"Fixed Crew link: {n} occurrence(s)")

# Strip <nowiki/> artifacts
before = text.count('<nowiki/>')
text = text.replace('<nowiki/>', '')
print(f"Removed {before} <nowiki/> tags")

f.write_text(text, encoding="utf-8")
print("Done.")
