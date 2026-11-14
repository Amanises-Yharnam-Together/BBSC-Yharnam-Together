# SPDX-License-Identifier: GPL-2.0-or-later
"""Makes third_party/fonts/NotoSansThai-Overlay.ttf, the overlay's Thai font.

Noto Sans Thai (SIL OFL 1.1, https://github.com/notofonts/thai) places its marks with OpenType
(GPOS), which Dear ImGui does not run. This bakes the places in instead: HarfBuzz shapes a
sample of each case (ก่ กี่ ป่ ปี่ ...), and every mark becomes a zero-width glyph already moved to
where HarfBuzz put it, at the code point thai_shaping.variant() names. Only the Thai block and
those marks are kept; the overlay's own fonts draw everything else.

  pip install fonttools uharfbuzz
  python3 scripts/thai_font.py NotoSansThai[wdth,wght].ttf

The source is the variable font from google/fonts (ofl/notosansthai); it is cut at Regular.
"""
import io
import sys
from pathlib import Path

import uharfbuzz as hb
from fontTools import subset
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thai_shaping import LOWER, MARKS, NIKHAHIT, TAILED, TONES, variant  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'gpu/third_party/fonts/NotoSansThai-Overlay.ttf'
NAME = 'Noto Sans Thai Overlay'
PLAIN, TALL_BASE, TAILED_BASE = 'ก', 'ป', chr(min(TAILED))


def shaped(blob, text):
    """[(glyph name, x offset, y offset)] of the marks HarfBuzz places in `text` (after the base)."""
    face = hb.Face(blob)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {})
    names = [font.glyph_to_string(info.codepoint) for info in buf.glyph_infos]
    out, pen = [], 0
    for name, pos in zip(names, buf.glyph_positions):
        out.append((name, pen + pos.x_offset, pos.y_offset))
        pen += pos.x_advance
    base_advance = buf.glyph_positions[0].x_advance
    # Positions from where ImGui puts a zero-width mark: the end of the base.
    return [(name, x - base_advance, y) for name, x, y in out[1:]]


def placement(blob, mark, left, alt):
    """(glyph, dx, dy) for `mark` in its place: the sample text and which of its glyphs is the mark."""
    base = TALL_BASE if left else PLAIN
    m = chr(mark)
    if mark in TONES:
        sample = base + ('ี' + m if alt else m)
        return shaped(blob, sample)[-1]
    if mark in LOWER:
        if alt:
            # A tailed consonant: HarfBuzz swaps in its short form instead of moving the vowel,
            # so the vowel goes down by the length of the tail.
            glyph, dx, dy = shaped(blob, base + m)[-1]
            return glyph, dx, dy - TAIL_DEPTH
        return shaped(blob, base + m)[-1]
    if mark == NIKHAHIT and alt:
        raise ValueError('no raised nikhahit')
    return shaped(blob, base + m)[-1]


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    font = TTFont(argv[1])
    font = instancer.instantiateVariableFont(font, {'wght': 400, 'wdth': 100})
    data = io.BytesIO()
    font.save(data)
    blob = hb.Blob(data.getvalue())
    font = TTFont(io.BytesIO(data.getvalue()))

    glyf, hmtx, cmap = font['glyf'], font['hmtx'], font.getBestCmap()
    tailed = cmap[min(TAILED)]
    global TAIL_DEPTH
    TAIL_DEPTH = glyf[f'{tailed}.short'].yMin - glyf[tailed].yMin if f'{tailed}.short' in glyf else 0
    glyph_set = font.getGlyphSet()
    placed = {}
    for mark in MARKS:
        for left in (False, True):
            for alt in (False, True):
                if alt and mark not in TONES and mark not in LOWER:
                    continue
                if left and mark in LOWER:
                    continue
                cp = variant(mark, left, alt)
                source, dx, dy = placement(blob, mark, left, alt)
                pen = DecomposingRecordingPen(glyph_set)
                glyph_set[source].draw(pen)
                out = TTGlyphPen(None)
                for op, args in pen.value:
                    getattr(out, op)(*[(a[0] + dx, a[1] + dy) if a is not None else None for a in args])
                name = f'thai.u{cp:04X}'
                font.glyphOrder.append(name)
                glyf[name] = out.glyph()
                glyf[name].recalcBounds(glyf)
                hmtx[name] = (0, glyf[name].xMin if glyf[name].numberOfContours else 0)
                placed[cp] = name
    for table in font['cmap'].tables:
        if table.isUnicode():
            table.cmap.update(placed)

    keep = sorted({cp for cp in font.getBestCmap() if 0x0E01 <= cp <= 0x0E5B} | set(placed))
    options = subset.Options()
    options.layout_features = []
    options.drop_tables += ['GSUB', 'GPOS', 'GDEF', 'STAT']
    options.name_IDs = ['*']
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=keep)
    subsetter.subset(font)
    for record in font['name'].names:
        if record.nameID in (1, 4, 16):
            record.string = NAME
        elif record.nameID == 6:
            record.string = NAME.replace(' ', '') + '-Regular'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    font.save(OUT)
    print(f'wrote {OUT} ({OUT.stat().st_size} bytes, {len(keep)} characters)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
