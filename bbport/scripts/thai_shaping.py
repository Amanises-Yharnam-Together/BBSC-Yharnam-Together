# SPDX-License-Identifier: GPL-2.0-or-later
"""Thai text for a renderer without shaping (Dear ImGui draws one glyph per character).

Thai vowel and tone marks sit above or below the consonant, and where depends on their
neighbours: a tone goes higher over an upper vowel, every mark moves left on a tall consonant
(ป ฝ ฟ ฬ), a lower vowel goes lower under a tailed one (ฎ ฏ). The port's Thai font
(third_party/fonts/NotoSansThai-Overlay.ttf, made by thai_font.py) holds each mark in every one
of those places at a private-use code point; shape() picks them, so the overlay draws Thai
right with no shaping of its own. menu_texts.py runs the Thai texts through it.
"""

CONSONANTS = range(0x0E01, 0x0E2F)
UPPER_VOWELS = (0x0E31, 0x0E34, 0x0E35, 0x0E36, 0x0E37, 0x0E47, 0x0E4D, 0x0E4E)
TONES = (0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C)
LOWER = (0x0E38, 0x0E39, 0x0E3A)
MARKS = UPPER_VOWELS + TONES + LOWER
TALL = {0x0E1B, 0x0E1D, 0x0E1F, 0x0E2C}  # ป ฝ ฟ ฬ: marks move left
TAILED = {0x0E0E, 0x0E0F}  # ฎ ฏ: lower vowels move down
SARA_AA, SARA_AM, NIKHAHIT = 0x0E32, 0x0E33, 0x0E4D
PUA = 0xF700


def variant(mark, left=False, alt=False):
    """The code point of a placed mark. alt: raised (a tone over an upper vowel or the nikhahit
    of sara am) or lowered (a lower vowel under a tailed consonant)."""
    if not (left or alt):
        return mark
    return PUA + MARKS.index(mark) * 4 + (2 if left else 0) + (1 if alt else 0)


def shape(text):
    """`text` with every Thai mark at the code point of its place (sara am split in two)."""
    out = []
    base, has_upper = None, False
    chars = [ord(c) for c in text]
    i = 0
    while i < len(chars):
        c = chars[i]
        left = base in TALL
        if c in CONSONANTS:
            base, has_upper = c, False
            out.append(c)
        elif base is None:
            out.append(c)
        elif c in TONES and i + 1 < len(chars) and chars[i + 1] == SARA_AM:
            # Tone + sara am (น้ำ): the nikhahit, the tone over it, then sara aa.
            out += [variant(NIKHAHIT, left), variant(c, left, True), SARA_AA]
            base, i = None, i + 1
        elif c == SARA_AM:
            out += [variant(NIKHAHIT, left), SARA_AA]
            base = None
        elif c in UPPER_VOWELS:
            out.append(variant(c, left))
            has_upper = True
        elif c in TONES:
            out.append(variant(c, left, has_upper))
        elif c in LOWER:
            out.append(variant(c, False, base in TAILED))
        else:
            base = None
            out.append(c)
        i += 1
    return ''.join(map(chr, out))
