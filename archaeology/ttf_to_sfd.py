#!/usr/bin/env fontforge
import sys
import fontforge


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} INPUT.ttf OUTPUT.sfd", file=sys.stderr)
        return 2

    in_path = sys.argv[1]
    out_path = sys.argv[2]

    font = fontforge.open(in_path)
    font.save(out_path)
    font.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
