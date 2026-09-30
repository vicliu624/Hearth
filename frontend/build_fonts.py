"""Build a small Noto Sans SC subset for Hearth's shipped UI vocabulary.

Run with Python + fonttools[woff] after placing the licensed upstream fonts in
public/fonts. Full fallback is loaded only for characters outside the subset.
"""

from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont

root = Path(__file__).resolve().parent
font_dir = root / "public" / "fonts"
text = "".join(
    path.read_text(encoding="utf-8-sig")
    for directory in (root / "src", root.parent / "src/hearth/web")
    for path in directory.rglob("*")
    if path.suffix in {".tsx", ".ts", ".html", ".py"}
    or (path.suffix == ".json" and path.stem in {"zh-CN", "en"})
)
characters = sorted({ord(char) for char in text if ord(char) > 127})
font = TTFont(font_dir / "noto-sans-sc-full.woff2")
options = subset.Options()
options.flavor = "woff2"
subsetter = subset.Subsetter(options=options)
subsetter.populate(unicodes=characters)
subsetter.subset(font)
font.save(font_dir / "noto-sans-sc-ui.woff2")
rules = [
    f'@font-face{{font-family:Nunito;font-style:normal;font-weight:{weight};font-display:swap;src:url(/fonts/nunito-latin-{weight}-normal.woff2) format("woff2")}}'
    for weight in (500, 700, 900)
]
rules.append(
    '@font-face{font-family:"Noto Sans SC";font-style:normal;font-weight:400 900;font-display:swap;src:url(/fonts/noto-sans-sc-full.woff2) format("woff2")}'
)
rules.append(
    '@font-face{font-family:"Noto Sans SC";font-style:normal;font-weight:400 900;font-display:swap;src:url(/fonts/noto-sans-sc-ui.woff2) format("woff2");unicode-range:'
    + ",".join(f"U+{char:X}" for char in characters)
    + "}"
)
(root / "src/fonts.css").write_text("\n".join(rules) + "\n", encoding="utf-8")
print(
    f"Subset: {len(characters)} characters, {(font_dir / 'noto-sans-sc-ui.woff2').stat().st_size} bytes"
)
