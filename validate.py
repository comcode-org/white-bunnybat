#!/usr/bin/env fontforge


import sys
import fontforge


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} INPUT", file=sys.stderr)
        return 2

    in_path = sys.argv[1]
    font = fontforge.open(in_path)
    validation = font.validate()
    if validation != 0:
        print(
            "Validation error! Please use the fontforge GUI to diagnose and fix.",
            file=sys.stderr,
        )
    return validation


if __name__ == "__main__":
    raise SystemExit(main())
