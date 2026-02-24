#!/usr/bin/env fontforge


import sys
import fontforge


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} INPUT", file=sys.stderr)
        return 2

    in_path = sys.argv[1]
    font = fontforge.open(in_path)

    # fontforge built-in validation
    validation = font.validate()
    if validation != 0:
        print(
            "Validation error! Please use the fontforge GUI to diagnose and fix.",
            file=sys.stderr,
        )
        return validation

    # also check there are no comments on glyphs
    glyphs_with_comments = [glyph for glyph in font.glyphs() if glyph.comment != ""]
    if len(glyphs_with_comments) > 0:
        print(
            """
Glyphs should not have comments;
see https://github.com/comcode-org/white-bunnybat/issues/43

Remove comments from the following glyphs:
            """,
            file=sys.stderr,
        )
        for glyph in glyphs_with_comments:
            print(glyph.glyphname + " U+" + "{:04X}".format(glyph.unicode))
        return 1

    # we're good!
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
