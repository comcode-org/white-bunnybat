#!/usr/bin/env python3

import sys
import os
import re

def write_glyph_list(content: str) -> int:
    out_file_name = "glyph-list.txt"
    try:
        with open(out_file_name, "w") as out:
            out.write(content)
        print(f"Writing {out_file_name} done.")
        return 0
    except FileNotFoundError:
        print("Directory not found", file = sys.stderr)
        return 2
    except PermissionError:
        print("Permission denied", file = sys.stderr)
        return 1
    except OSError as error:
        print(f"Error writing file: {error}", file = sys.stderr)
        return 1

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} INPUT", file = sys.stderr)
        return 2
    try:
        fn = sys.argv[1]
        with open(fn) as spline_font_db:
            print(f"File {os.path.basename(fn)} found.")
            data = spline_font_db.read()
            pattern = r"^StartChar:\s*([\w\.\-]+?)\s*\nEncoding:\s*(\d+)\s+-?\d+\s+\d+$"
            matches = re.findall(pattern, data, re.M)
            glyph_cnt = len(matches)
            
            if glyph_cnt < 1:
                print(f"No glyphs found!")
                return 1

            glyph_list = f"count: {glyph_cnt}\n"
            glyph_list += "UniCode  | Dec   | S | Name\n"
            glyph_list += "---------+-------+---+-----------------\n"
            for match in matches:
                uni = f"\\U+{int(match[1]):04X}"
                dec = f"{int(match[1]):5}"
                sym = f"{chr(int(match[1]))}"
                name = match[0]
                glyph_list += f"{uni:8} | {dec} | {sym} | {name}\n"

            return write_glyph_list(glyph_list)

    except FileNotFoundError:
        print(f"File {os.path.basename(fn)} does not exist.", file=sys.stderr)
        return 2
    except PermissionError:
        print(f"Permission denied for {os.path.basename(fn)}!", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
