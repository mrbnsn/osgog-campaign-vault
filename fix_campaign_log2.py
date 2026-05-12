from pathlib import Path

f = Path("d:/osgog/The Black Lake of Osgog/08 Campaign Meta/Campaign Log.md")
text = f.read_text(encoding="utf-8")

# These lines have \xa0 (non-breaking space) and � (replacement char for
# curly quotes that were mis-encoded during the XML read). Replace the whole
# wikilink with the clean ISO-date version.

replacements = [
    # 7/6/23 — has \xa0 and � around the title
    ('[[7/6/23 Working Title:\xa0 �The One Where Ryan Does A One Man Show of Grizzly Man�]]',
     '[[2023-07-06 Working Title "The One Where Ryan Does A One Man Show of Grizzly Man"]]'),
    # 9/4/23 — \xa0 after date, � around title
    ('[[9/4/23\xa0 �The One Where There Weren�t Enough of Us to Make a Decision��]]',
     '[[2023-09-04 "The One Where There Weren\'t Enough of Us to Make a Decision…"]]'),
    # 5/9/24 — \xa0 inside the link
    ('[[5/9/24  The One Where We Meet The Limb Entity and\xa0 (Some Of Us) Receive Our Shadow Scars]]',
     '[[2024-05-09 The One Where We Meet The Limb Entity and (Some Of Us) Receive Our Shadow Scars]]'),
]

for old, new in replacements:
    if old in text:
        text = text.replace(old, new)
        print(f"Fixed: {new[:80]}")
    else:
        print(f"STILL NOT FOUND (see repr above)")

f.write_text(text, encoding="utf-8")
print("Done.")
