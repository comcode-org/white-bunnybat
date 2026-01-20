#!/usr/bin/env fontforge
# merge_glyphs.py
#
# Usage:
#   ./merge_glyphs.py donor.ttf "U+2800..U+28FF,U+263A,U+1F600..U+1F64F"
#
# Behavior:
# - Always opens base font: white-rabbit.sfd
# - Copies glyphs for the requested Unicode codepoints from donor.ttf into the base font
# - ALWAYS overwrites any existing glyphs in the base font for those codepoints
# - Saves back to: white-rabbit.sfd

import sys
import re

import fontforge


HEX_RE = re.compile(r"^(?:U\+|0x)?([0-9A-Fa-f]{1,6})$")


def parse_codepoint(s: str) -> int:
    s = s.strip()
    m = HEX_RE.match(s)
    if not m:
        raise ValueError(f"Bad codepoint: {s!r}")
    return int(m.group(1), 16)


def parse_ranges(spec: str):
    """
    Accepts comma-separated tokens:
      - U+2800..U+28FF
      - U+2800-U+28FF
      - U+263A
      - 0x41..0x5A
      - 0041..005A
    Returns a sorted list of unique codepoints.
    """
    cps = set()
    for token in (t.strip() for t in spec.split(",") if t.strip()):
        # Normalize range separators
        if ".." in token:
            a, b = token.split("..", 1)
            start = parse_codepoint(a)
            end = parse_codepoint(b)
            if end < start:
                start, end = end, start
            for cp in range(start, end + 1):
                cps.add(cp)
        elif "-" in token:
            a, b = token.split("-", 1)
            start = parse_codepoint(a)
            end = parse_codepoint(b)
            if end < start:
                start, end = end, start
            for cp in range(start, end + 1):
                cps.add(cp)
        else:
            cps.add(parse_codepoint(token))
    return sorted(cps)


def copy_one(donor: "fontforge.font", base: "fontforge.font", cp: int):
    donor_slot = donor.findEncodingSlot(cp)
    if donor_slot == -1:
        return False, "missing-in-donor"

    base_slot = base.findEncodingSlot(cp)
    if base_slot == -1:
        base.createChar(cp)
        base_slot = base.findEncodingSlot(cp)

    # Copy from donor
    donor.selection.none()
    donor.selection.select(donor_slot)
    donor.copy()

    # Paste into base (always overwrite)
    base.selection.none()
    base.selection.select(base_slot)

    try:
        base_g = base[base_slot]
        base_g.clear()
    except Exception:
        pass

    base.paste()

    # Best-effort copy of a few metrics/properties
    try:
        dg = donor[donor_slot]
        bg = base[base_slot]

        for attr in ("width", "vwidth", "left_side_bearing", "right_side_bearing"):
            try:
                setattr(bg, attr, getattr(dg, attr))
            except Exception:
                pass

        try:
            bg.comment = dg.comment
        except Exception:
            pass

        # Setting glyphname can fail if it conflicts; ignore if so.
        try:
            bg.glyphname = dg.glyphname
        except Exception:
            pass

    except Exception:
        pass

    return True, "copied"


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("Usage:\n" '  ./merge_glyphs.py donor.ttf "U+...."\n')
        return 2

    base_path = "white-bunnybat.sfd"
    donor_path = argv[1]
    range_spec = argv[2]

    try:
        cps = parse_ranges(range_spec)
    except Exception as e:
        sys.stderr.write(f"ERROR parsing range spec: {e}\n")
        return 2

    if not cps:
        sys.stderr.write("No codepoints parsed from range spec.\n")
        return 2

    base = fontforge.open(base_path)
    donor = fontforge.open(donor_path)

    # Make sure we're in Unicode
    try:
        base.encoding = "UnicodeFull"
    except Exception:
        pass
    try:
        donor.encoding = "UnicodeFull"
    except Exception:
        pass

    copied = 0
    skipped_missing = 0

    for cp in cps:
        ok, reason = copy_one(donor, base, cp)
        if ok:
            copied += 1
        else:
            if reason == "missing-in-donor":
                skipped_missing += 1

    # Save in-place
    base.save(base_path)

    sys.stderr.write(
        f"Done.\n"
        f"  Base font:  {base_path}\n"
        f"  Donor font: {donor_path}\n"
        f"  Copied: {copied}\n"
        f"  Skipped (missing in donor): {skipped_missing}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
