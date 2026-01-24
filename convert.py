#!/usr/bin/env fontforge

"""
A fontforge Python script for converting between font formats (ttf, etc) and
fontforge .sfd project files. This was used to produce white-bunnybat.sfd from
Hackmud's current ttf font.

If the output file extension is .sfd, a fontforge project file will be saved.
Otherwise, we ask fontforge to "generate" the output font file; fontforge will
determine the font format based on the extension.

Note that fontforge will fallback to generating some kind of weird PostScript
file for unsupported extensions. Supported extensions include ttf, woff, woff2.
"""

import sys
import fontforge


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} INPUT OUTPUT", file=sys.stderr)
        return 2

    in_path = sys.argv[1]
    out_path = sys.argv[2]

    font = fontforge.open(in_path)
    if out_path.endswith(".sfd"):
        font.save(out_path)
    else:
        font.generate(out_path)
    font.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
