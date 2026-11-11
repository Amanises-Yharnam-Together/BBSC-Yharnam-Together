# SPDX-License-Identifier: GPL-2.0-or-later
"""Arabic letters in the shapes they take next to each other (Unicode Arabic Presentation Forms-B), for
the in-game menus: Dear ImGui draws one glyph per character and knows nothing of Arabic joining, so the
table (menu_texts.py) holds the joined forms already, still in reading order. The right-to-left line
order is the drawing's (third_party/imgui/imgui_bidi.h). Vowel marks are dropped: ImGui cannot place
them over a letter. BBSC 2026-11-08."""

# base letter -> (first presentation form, joins to the next letter too)
# Forms follow each other: isolated, final, then for dual-joining letters initial, medial.
_LETTERS = {
    0x0621: (0xFE80, None),  # hamza: no other form
    0x0622: (0xFE81, False), 0x0623: (0xFE83, False), 0x0624: (0xFE85, False), 0x0625: (0xFE87, False),
    0x0626: (0xFE89, True), 0x0627: (0xFE8D, False), 0x0628: (0xFE8F, True), 0x0629: (0xFE93, False),
    0x062A: (0xFE95, True), 0x062B: (0xFE99, True), 0x062C: (0xFE9D, True), 0x062D: (0xFEA1, True),
    0x062E: (0xFEA5, True), 0x062F: (0xFEA9, False), 0x0630: (0xFEAB, False), 0x0631: (0xFEAD, False),
    0x0632: (0xFEAF, False), 0x0633: (0xFEB1, True), 0x0634: (0xFEB5, True), 0x0635: (0xFEB9, True),
    0x0636: (0xFEBD, True), 0x0637: (0xFEC1, True), 0x0638: (0xFEC5, True), 0x0639: (0xFEC9, True),
    0x063A: (0xFECD, True), 0x0641: (0xFED1, True), 0x0642: (0xFED5, True), 0x0643: (0xFED9, True),
    0x0644: (0xFEDD, True), 0x0645: (0xFEE1, True), 0x0646: (0xFEE5, True), 0x0647: (0xFEE9, True),
    0x0648: (0xFEED, False), 0x0649: (0xFEEF, False), 0x064A: (0xFEF1, True),
}
_TATWEEL = 0x0640
# lam + alef: (isolated ligature); the final one is the next code point
_LAM_ALEF = {0x0622: 0xFEF5, 0x0623: 0xFEF7, 0x0625: 0xFEF9, 0x0627: 0xFEFB}


def _mark(c):
    return 0x064B <= c <= 0x065F or c == 0x0670


def _joins_forward(c):
    """The letter connects to the one after it."""
    return c == _TATWEEL or (c in _LETTERS and _LETTERS[c][1] is True)


def _joins_back(c):
    """The letter can take a connection from the one before it."""
    return c == _TATWEEL or (c in _LETTERS and _LETTERS[c][1] is not None)


def shape(text):
    """`text` with every Arabic letter in its joined form; other characters as they were."""
    chars = [ord(ch) for ch in text if not _mark(ord(ch))]
    out = []
    i = 0
    while i < len(chars):
        c = chars[i]
        prev = chars[i - 1] if i > 0 else None
        before = prev is not None and _joins_forward(prev)
        if c == 0x0644 and i + 1 < len(chars) and chars[i + 1] in _LAM_ALEF:
            out.append(_LAM_ALEF[chars[i + 1]] + (1 if before else 0))
            i += 2
            continue
        if c not in _LETTERS or _LETTERS[c][1] is None:
            out.append(c if c not in _LETTERS else _LETTERS[c][0])
            i += 1
            continue
        first, dual = _LETTERS[c]
        nxt = chars[i + 1] if i + 1 < len(chars) else None
        after = dual and nxt is not None and _joins_back(nxt)
        if before and after:
            form = first + 3
        elif before:
            form = first + 1
        elif after:
            form = first + 2
        else:
            form = first
        out.append(form)
        i += 1
    return ''.join(map(chr, out))


if __name__ == '__main__':
    import sys
    for word in sys.argv[1:] or ['السلام عليكم', 'لا', 'الإعدادات']:
        print(word, '->', ' '.join(f'{ord(c):04X}' for c in shape(word)))
