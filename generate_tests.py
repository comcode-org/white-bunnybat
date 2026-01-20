#!/usr/bin/env fontforge
# generate_tests.py
#
# Usage:
#   ./generate_tests.py
#
# Produces:
#   - white-bunnybat.ttf
#   - test.html
#   - test.js
#
# Changes vs previous version:
# - test.js embedded JSON no longer includes Unicode names OR annotations (keeps only glyph name + codepoint + block grouping)
# - test.html keeps Unicode names (and aliases), but removes Unicode annotations from display (and does not store them in JSON)

import os
import sys
import json
import time

import fontforge


SFD_IN = "white-bunnybat.sfd"
TTF_OUT = "white-bunnybat.ttf"
HTML_OUT = "test.html"
JS_OUT = "test.js"


def html_escape(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def cp_to_uplus(cp):
    return "U+%04X" % cp if cp <= 0xFFFF else "U+%06X" % cp


def cp_to_html_entity(cp):
    return "&#x%X;" % cp


def is_printable_for_showcase(cp):
    if cp < 0x20:
        return False
    if cp == 0x7F:
        return False
    if cp == 0x00AD:
        return False
    return True


def make_contiguous_ranges(sorted_codepoints):
    if not sorted_codepoints:
        return []
    ranges = []
    start = prev = sorted_codepoints[0]
    for cp in sorted_codepoints[1:]:
        if cp == prev + 1:
            prev = cp
            continue
        ranges.append([start, prev])
        start = prev = cp
    ranges.append([start, prev])
    return ranges


# ---- Unicode library helpers (FontForge) ----


def unicode_lib_available():
    try:
        bc = fontforge.UnicodeBlockCountFromLib(0)
    except Exception:
        bc = -1
    try:
        ver = fontforge.UnicodeNamesListVersion()
    except Exception:
        ver = ""
    return (bc is not None and bc >= 0) or (isinstance(ver, str) and ver != "")


def build_block_index():
    blocks = []
    try:
        count = fontforge.UnicodeBlockCountFromLib(0)
    except Exception:
        count = -1

    if count is None or count < 0:
        return blocks

    for i in range(int(count)):
        try:
            start = fontforge.UnicodeBlockStartFromLib(i)
            end = fontforge.UnicodeBlockEndFromLib(i)
            name = fontforge.UnicodeBlockNameFromLib(i) or ""
        except Exception:
            continue
        if start is None or end is None or start < 0 or end < 0:
            continue
        blocks.append({"index": i, "name": name, "start": int(start), "end": int(end)})
    return blocks


def block_for_codepoint(cp, blocks):
    if not blocks:
        return ""
    for b in blocks:
        if b["start"] <= cp <= b["end"]:
            return b["name"]
    return ""


def unicode_name(cp):
    try:
        return fontforge.UnicodeNameFromLib(cp) or ""
    except Exception:
        return ""


def unicode_alias(cp):
    try:
        return fontforge.UnicodeNames2FromLib(cp) or ""
    except Exception:
        return ""


def glyph_name_for_codepoint(cp, font_glyphname=None):
    ffname = ""
    try:
        ffname = fontforge.nameFromUnicode(cp) or ""
    except Exception:
        ffname = ""
    if font_glyphname:
        return font_glyphname
    return ffname or ("uni%04X" % cp if cp <= 0xFFFF else "u%06X" % cp)


def codepoint_for_glyph_name(gname, glyph_unicode=None):
    if isinstance(glyph_unicode, int) and glyph_unicode >= 0:
        return glyph_unicode
    try:
        return int(fontforge.unicodeFromName(gname))
    except Exception:
        return -1


# ---- Data building ----


def build_data_full_for_html(uni_glyphs, nonuni_glyphs, blocks, names_version):
    """
    HTML wants Unicode names (and alias), but NOT annotations.
    """
    by_block = {}
    for item in uni_glyphs:
        cp = item["codepoint"]
        bname = block_for_codepoint(cp, blocks) or "Other / Unmapped Blocks"
        by_block.setdefault(bname, []).append(item)

    blocks_out = []
    for bname in sorted(by_block.keys(), key=lambda n: (n != "Basic Latin", n)):
        items = sorted(by_block[bname], key=lambda x: x["codepoint"])
        cps = sorted({x["codepoint"] for x in items})
        ranges = make_contiguous_ranges(cps)
        blocks_out.append(
            {
                "name": bname,
                "count": len(items),
                "ranges": [{"start": r[0], "end": r[1]} for r in ranges],
                "glyphs": items,  # includes unicode_name / unicode_alias
            }
        )

    return {
        "font": {
            "sfd": SFD_IN,
            "ttf": TTF_OUT,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "unicode_lib": {
            "available": unicode_lib_available(),
            "nameslist_version": names_version,
            "block_count": len(blocks),
        },
        "unicode": {"count": len(uni_glyphs), "blocks": blocks_out},
        "non_unicode": {"count": len(nonuni_glyphs), "glyphs": nonuni_glyphs},
    }


def build_data_slim_for_js(html_data):
    """
    JS should be as small as possible:
    - remove unicode_name / unicode_alias
    - keep only what JS needs to render a text showcase + block/range structure
    """
    slim_blocks = []
    for b in html_data["unicode"]["blocks"]:
        slim_blocks.append(
            {
                "name": b["name"],
                "count": b["count"],
                "ranges": b["ranges"],
                "glyphs": [
                    {"codepoint": g["codepoint"], "name": g.get("name", "")}
                    for g in b["glyphs"]
                ],
            }
        )

    return {
        "font": {
            "ttf": html_data["font"]["ttf"],
        },
        "unicode": {
            "count": html_data["unicode"]["count"],
            "blocks": slim_blocks,
        },
        "non_unicode": {
            "count": html_data["non_unicode"]["count"],
        },
        "unicode_lib": {
            "available": html_data["unicode_lib"]["available"],
            "nameslist_version": html_data["unicode_lib"]["nameslist_version"],
            "block_count": html_data["unicode_lib"]["block_count"],
        },
    }


# ---- Writers ----


def write_html(data):
    css = r"""
:root { color-scheme: light dark; }
body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 16px; }
h1 { margin: 0 0 6px 0; }
.meta { opacity: 0.85; margin: 0 0 16px 0; }
.block { margin: 24px 0; }
.block h2 { margin: 0 0 8px 0; font-size: 18px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
.cell { border: 1px solid rgba(127,127,127,0.35); border-radius: 10px; padding: 10px; }
.glyph { font-family: "White Bunnybat"; font-size: 48px; line-height: 1.1; }
.code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 12px; opacity: 0.9; margin-top: 6px; }
.name { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 12px; opacity: 0.85; margin-top: 2px; word-break: break-word; }
.uniname { font-size: 12px; opacity: 0.85; margin-top: 4px; }
.small { font-size: 13px; opacity: 0.85; }
hr { border: none; border-top: 1px solid rgba(127,127,127,0.35); margin: 24px 0; }
@font-face {
  font-family: "White Bunnybat";
  src: url("./white-bunnybat.ttf") format("truetype");
  font-weight: normal;
  font-style: normal;
}
"""
    parts = []
    parts.append("<!doctype html>")
    parts.append("<html lang='en'>")
    parts.append("<head>")
    parts.append("  <meta charset='utf-8' />")
    parts.append(
        "  <meta name='viewport' content='width=device-width, initial-scale=1' />"
    )
    parts.append("  <title>white-bunnybat — glyph showcase</title>")
    parts.append("  <style>%s</style>" % css)
    parts.append("</head>")
    parts.append("<body>")
    parts.append("  <h1>white-bunnybat — glyph showcase</h1>")

    libline = "Unicode lib: %s" % (
        "available" if data["unicode_lib"]["available"] else "missing/disabled"
    )
    if data["unicode_lib"].get("nameslist_version"):
        libline += " • Nameslist: %s" % data["unicode_lib"]["nameslist_version"]

    parts.append(
        "  <p class='meta'>TTF: <code>%s</code> • Unicode glyphs: <b>%d</b> • Non-Unicode glyphs: <b>%d</b><br/>%s</p>"
        % (
            html_escape(data["font"]["ttf"]),
            data["unicode"]["count"],
            data["non_unicode"]["count"],
            html_escape(libline),
        )
    )

    for block in data["unicode"]["blocks"]:
        bname = block["name"]
        ranges_txt = ", ".join(
            (
                "%s–%s" % (cp_to_uplus(r["start"]), cp_to_uplus(r["end"]))
                if r["start"] != r["end"]
                else cp_to_uplus(r["start"])
            )
            for r in block["ranges"]
        )
        parts.append("  <section class='block'>")
        parts.append(
            "    <h2>%s <span class='small'>(%d glyphs; %s)</span></h2>"
            % (
                html_escape(bname),
                block["count"],
                html_escape(ranges_txt or "no ranges"),
            )
        )
        parts.append("    <div class='grid'>")

        for g in block["glyphs"]:
            cp = g["codepoint"]
            gname = g.get("name", "")
            uname = g.get("unicode_name", "")
            alias = g.get("unicode_alias", "")

            if is_printable_for_showcase(cp):
                glyph_html = cp_to_html_entity(cp)
            else:
                glyph_html = "<span style='opacity:0.5'>∅</span>"

            parts.append("      <div class='cell'>")
            parts.append("        <div class='glyph'>%s</div>" % glyph_html)
            parts.append(
                "        <div class='code'>%s</div>" % html_escape(cp_to_uplus(cp))
            )
            parts.append("        <div class='name'>%s</div>" % html_escape(gname))

            if uname or alias:
                nm = uname
                if alias:
                    nm = (nm + " • alias: " + alias) if nm else ("alias: " + alias)
                parts.append("        <div class='uniname'>%s</div>" % html_escape(nm))

            parts.append("      </div>")

        parts.append("    </div>")
        parts.append("  </section>")

    if data["non_unicode"]["count"] > 0:
        parts.append("  <hr/>")
        parts.append("  <section class='block'>")
        parts.append(
            "    <h2>Non-Unicode glyphs <span class='small'>(%d glyphs)</span></h2>"
            % data["non_unicode"]["count"]
        )
        parts.append(
            "    <p class='small'>These glyphs have no Unicode codepoint (or aren’t assigned one in the SFD). They can’t be displayed by typing a character, but they still exist in the font.</p>"
        )
        parts.append("    <ul>")
        for g in data["non_unicode"]["glyphs"]:
            parts.append("      <li><code>%s</code></li>" % html_escape(g["name"]))
        parts.append("    </ul>")
        parts.append("  </section>")

    parts.append("</body>")
    parts.append("</html>")

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")


def write_js(data_slim):
    # Ensure the quine split("@")[1] yields pure JSON and nothing else.
    json_payload = json.dumps(data_slim, ensure_ascii=False, separators=(",", ":"))

    js = []
    js.append("//@%s@" % json_payload)
    js.append("function (context, args) {")
    js.append('  let data = JSON.parse(#fs.scripts.quine().split("@")[1]);')
    js.append("  let out = [];")
    js.append("  out.push(`Font: ${data.font.ttf}`);")
    js.append("  out.push(`Unicode glyphs: ${data.unicode.count}`);")
    js.append(
        "  if (data.non_unicode && data.non_unicode.count) out.push(`Non-Unicode glyphs: ${data.non_unicode.count}`);"
    )
    js.append('  out.push("");')
    js.append("")
    js.append("  function uplus(cp) {")
    js.append("    let hex = cp.toString(16).toUpperCase();")
    js.append("    hex = (cp <= 0xFFFF) ? hex.padStart(4,'0') : hex.padStart(6,'0');")
    js.append("    return 'U+' + hex;")
    js.append("  }")
    js.append("")
    js.append("  for (let b of data.unicode.blocks) {")
    js.append(
        "    let ranges = (b.ranges || []).map(r => (r.start === r.end) ? uplus(r.start) : `${uplus(r.start)}–${uplus(r.end)}` ).join(', ');"
    )
    js.append(
        "    out.push(`${b.name} (${b.count} glyphs; ${ranges || 'no ranges'})`);"
    )
    js.append("    let line = '';")
    js.append("    for (let g of b.glyphs) {")
    js.append("      let cp = g.codepoint;")
    js.append("      if (cp < 0x20 || cp === 0x7F) continue;")
    js.append("      if (cp === 0x00AD) continue;")
    js.append("      line += String.fromCodePoint(cp);")
    js.append("      if (line.length % 32 === 0) line += ' ';")
    js.append("    }")
    js.append("    out.push(line || '(no directly printable chars in this block)');")
    js.append("    out.push('');")
    js.append("  }")
    js.append("")
    js.append("  return out;")
    js.append("}")
    js.append("")

    with open(JS_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(js))


def main():
    if not os.path.exists(SFD_IN):
        sys.stderr.write("error: missing %s\n" % SFD_IN)
        return 2

    font = fontforge.open(SFD_IN)
    try:
        try:
            font.encoding = "UnicodeFull"
        except Exception:
            pass

        try:
            names_version = fontforge.UnicodeNamesListVersion() or ""
        except Exception:
            names_version = ""

        blocks = build_block_index()

        uni = []
        nonuni = []

        for g in font.glyphs():
            try:
                worth = g.isWorthOutputting()
            except Exception:
                worth = True
            if not worth:
                continue

            gname = (
                getattr(g, "glyphname", None) or getattr(g, "name", None) or "unnamed"
            )
            gunicode = getattr(g, "unicode", -1)

            cp = codepoint_for_glyph_name(gname, gunicode)

            if cp >= 0:
                uni.append(
                    {
                        "name": glyph_name_for_codepoint(cp, gname),
                        "codepoint": cp,
                        "unicode_name": unicode_name(cp),
                        "unicode_alias": unicode_alias(cp),
                        # Intentionally NOT including annotations anywhere.
                    }
                )
            else:
                nonuni.append({"name": gname})

        # De-dupe by codepoint; keep first encountered
        seen = set()
        uni_unique = []
        for item in sorted(uni, key=lambda x: x["codepoint"]):
            cp = item["codepoint"]
            if cp in seen:
                continue
            seen.add(cp)
            uni_unique.append(item)

        html_data = build_data_full_for_html(
            uni_unique,
            sorted(nonuni, key=lambda x: x["name"]),
            blocks,
            names_version,
        )
        js_data = build_data_slim_for_js(html_data)

        # Generate TTF
        font.generate(TTF_OUT)

        # Generate HTML + JS
        write_html(html_data)
        write_js(js_data)

        print("Wrote:", TTF_OUT)
        print("Wrote:", HTML_OUT)
        print("Wrote:", JS_OUT)
        return 0
    finally:
        try:
            font.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
