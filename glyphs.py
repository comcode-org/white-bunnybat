#!/usr/bin/env fontforge

"""Lists all unicode glyphs defined in the font, one glyph per line"""

import sys
import fontforge
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", choices=["char", "int", "hex"], default="char")
    args = parser.parse_args()

    font = fontforge.open("white-bunnybat.sfd")
    # sort by codepoint (does fontforge already do this?)
    glyphs = sorted(font.glyphs(), key=lambda glyph: glyph.unicode)
    for glyph in glyphs:
        # omit weird glyphs like .notdef which show up as codepoint -1
        if glyph.unicode > 0:
            match args.output:
                case "char":
                    print(chr(glyph.unicode))
                case "int":
                    print(glyph.unicode)
                case "hex":
                    print("{:04X}".format(glyph.unicode))


if __name__ == "__main__":
    main()
