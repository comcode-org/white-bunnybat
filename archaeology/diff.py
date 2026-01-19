#!/usr/bin/env fontforge
# diff.py
#
# Usage:
#   diff.py fontA.ttf fontB.ttf
#
# Produces a stable, review-friendly diff:
# - font-wide metric differences
# - glyph presence differences
# - glyph diffs keyed by Unicode when available (else glyphname)
# - compares widths, bbox, components, and a normalized outline hash
#
# Notes:
# - Outline hashing normalizes coordinates by UPM (em) so fonts with different UPM
#   can still be compared meaningfully.
# - This is a "structural" outline comparison; visually identical outlines can
#   still hash differently if point order/segmentation differs.

import sys
import json
import hashlib

import fontforge


def font_metrics(f):
    """Collect a small set of font-wide metrics that commonly change."""
    out = {}
    out["em"] = getattr(f, "em", None)
    out["ascent"] = getattr(f, "ascent", None)
    out["descent"] = getattr(f, "descent", None)

    # These exist on many FontForge builds, but not all.
    # Missing ones will appear as None.
    for k in [
        "os2_typoascent",
        "os2_typodescent",
        "os2_typolinegap",
        "os2_winascent",
        "os2_windescent",
        "hhea_ascent",
        "hhea_descent",
        "hhea_linegap",
    ]:
        out[k] = getattr(f, k, None)

    return out


def dict_diff(a, b):
    """Return a dict of fields where values differ."""
    changes = {}
    keys = set(a.keys()) | set(b.keys())
    for k in sorted(keys):
        if a.get(k) != b.get(k):
            changes[k] = {"A": a.get(k), "B": b.get(k)}
    return changes


def glyph_key(g):
    """
    Stable key for matching glyphs across fonts:
    - Prefer Unicode codepoint when present
    - Otherwise fall back to glyph name
    """
    u = getattr(g, "unicode", -1)
    if u is not None and u != -1:
        return f"U+{u:04X}"
    return f"name:{g.glyphname}"


def glyph_label(g):
    """
    Human-friendly label.
    - For encoded glyphs: U+XXXX (name)
    - For unencoded glyphs: name (unencoded, enc=slot)
    """
    u = getattr(g, "unicode", -1)
    if u is not None and u != -1:
        return f"U+{u:04X} ({g.glyphname})"

    enc = getattr(g, "encoding", None)
    if enc is None:
        return f"{g.glyphname} (unencoded)"
    return f"{g.glyphname} (unencoded, enc={enc})"


def normalize_transform(transform, em):
    """
    Transform is typically (xx, xy, yx, yy, dx, dy).
    We normalize translation (dx, dy) by em so UPM scaling won't change hashes.
    """
    t = list(transform)
    if em and len(t) == 6:
        t[4] = t[4] / em
        t[5] = t[5] / em
    return [round(x, 8) for x in t]


def layer_outline_signature(g, em):
    """
    Produce a stable hash of outline geometry:
    - iterate contours and points
    - include on-curve flag
    - normalize coordinates by em to be UPM-invariant
    - include component refs + normalized transforms
    """
    try:
        layer = g.foreground
    except Exception:
        return None

    contours_out = []

    # Component references
    refs_out = []
    try:
        for refname, transform in g.references:
            refs_out.append([refname, normalize_transform(transform, em)])
    except Exception:
        pass

    # Contours and points
    try:
        for contour in layer:
            pts = []
            for pt in contour:
                x = (pt.x / em) if em else pt.x
                y = (pt.y / em) if em else pt.y
                pts.append([round(x, 8), round(y, 8), bool(pt.on_curve)])
            contours_out.append(pts)
    except Exception:
        pass

    payload = {"contours": contours_out, "refs": refs_out}
    b = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def glyph_snapshot(g, em):
    """Collect properties worth diffing, including a normalized outline hash."""
    snap = {
        "name": g.glyphname,
        "unicode": getattr(g, "unicode", -1),
        "encoding_slot": getattr(
            g, "encoding", None
        ),  # useful for debugging, not for matching
        "width": getattr(g, "width", None),
        "vwidth": getattr(g, "vwidth", None),
        "bbox": None,
        "bbox_norm": None,
        "has_outlines": None,
        "references": [],
        "outline_hash": None,
    }

    # Bounding box in font units
    try:
        bb = g.boundingBox()  # (xmin, ymin, xmax, ymax)
        snap["bbox"] = tuple(round(x, 3) for x in bb)
        if em:
            snap["bbox_norm"] = tuple(round((x / em), 8) for x in bb)
    except Exception:
        snap["bbox"] = None
        snap["bbox_norm"] = None

    try:
        snap["has_outlines"] = not g.foreground.isEmpty()
    except Exception:
        snap["has_outlines"] = None

    # References/components (include normalized transforms for robust comparison)
    try:
        snap["references"] = [
            [refname, normalize_transform(transform, em)]
            for (refname, transform) in g.references
        ]
    except Exception:
        snap["references"] = []

    snap["outline_hash"] = layer_outline_signature(g, em)
    return snap


def build_index(font):
    """
    Map stable glyph keys -> {"label":..., "snap":...}
    If key collisions occur (rare), disambiguate by appending glyphname.
    """
    em = getattr(font, "em", None) or 1000
    idx = {}
    for g in font.glyphs():
        k = glyph_key(g)
        entry = {"label": glyph_label(g), "snap": glyph_snapshot(g, em)}
        if k in idx:
            k2 = f"{k}/{g.glyphname}"
            idx[k2] = entry
        else:
            idx[k] = entry
    return idx


def main():
    if len(sys.argv) != 3:
        print("Usage: diff.py fontA.ttf fontB.ttf", file=sys.stderr)
        sys.exit(2)

    path_a, path_b = sys.argv[1], sys.argv[2]
    fa = fontforge.open(path_a)
    fb = fontforge.open(path_b)

    # Font-wide metrics
    ma = font_metrics(fa)
    mb = font_metrics(fb)
    metric_changes = dict_diff(ma, mb)

    print("== Font-wide metric differences ==")
    if metric_changes:
        for k, v in metric_changes.items():
            print(f"- {k}: {v['A']}  ->  {v['B']}")
    else:
        print("(none)")

    # Glyph indices
    ia = build_index(fa)
    ib = build_index(fb)

    keys_a = set(ia.keys())
    keys_b = set(ib.keys())

    only_a = sorted(keys_a - keys_b)
    only_b = sorted(keys_b - keys_a)
    both = sorted(keys_a & keys_b)

    print("\n== Glyph presence ==")
    print(f"Only in A: {len(only_a)}")
    if only_a[:50]:
        print("  " + ", ".join(only_a[:50]) + (" ..." if len(only_a) > 50 else ""))
    print(f"Only in B: {len(only_b)}")
    if only_b[:50]:
        print("  " + ", ".join(only_b[:50]) + (" ..." if len(only_b) > 50 else ""))

    # Glyph diffs
    print("\n== Glyph property / outline differences (matched by Unicode or name) ==")

    changed = 0
    for k in both:
        ga = ia[k]
        gb = ib[k]

        sa = ga["snap"]
        sb = gb["snap"]

        diff = dict_diff(sa, sb)
        if not diff:
            continue

        changed += 1
        print(f"\n[{k}] {ga['label']}  vs  {gb['label']}")

        # Prefer normalized bbox for review if present
        # (you can drop raw bbox if you only want normalized)
        preferred_order = [
            "width",
            "bbox_norm",
            "bbox",
            "references",
            "outline_hash",
            "has_outlines",
            "unicode",
            "name",
            "encoding_slot",
            "vwidth",
        ]

        for fld in preferred_order:
            if fld in diff:
                v = diff[fld]
                print(f"  - {fld}: {v['A']}  ->  {v['B']}")

        # Print any remaining fields (future-proof)
        for fld in diff:
            if fld not in preferred_order:
                v = diff[fld]
                print(f"  - {fld}: {v['A']}  ->  {v['B']}")

    if changed == 0:
        print("(none)")


if __name__ == "__main__":
    main()
