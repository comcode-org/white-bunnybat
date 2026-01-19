#!/usr/bin/env fontforge
# diff.py
#
# Usage:
#   diff.py fontA.ttf fontB.ttf
#
# Produces a stable, review-friendly diff:
# - font-wide metric differences
# - glyph presence differences (by stable key: Unicode if present, else name)
# - glyph diffs: widths, bbox (raw + normalized), references, outline stats,
#   and (when comparable) point-level delta previews
#
# Notes:
# - Outline hashing and bbox_norm normalize coordinates by UPM (em), so fonts
#   with different UPM can still be compared meaningfully.
# - Point-level comparison is only meaningful if contour/point structure matches.

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
    Normalize translation (dx, dy) by em so UPM scaling won't change hashes.
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


def outline_stats(g):
    """Return contour/point stats for foreground layer."""
    if g is None:
        return None
    try:
        layer = g.foreground
    except Exception:
        return None

    contours = 0
    points = 0
    oncurve = 0
    offcurve = 0
    per_contour_points = []

    try:
        for c in layer:
            contours += 1
            c_points = 0
            for pt in c:
                points += 1
                c_points += 1
                if getattr(pt, "on_curve", False):
                    oncurve += 1
                else:
                    offcurve += 1
            per_contour_points.append(c_points)
    except Exception:
        pass

    return {
        "contours": contours,
        "points": points,
        "oncurve": oncurve,
        "offcurve": offcurve,
        "per_contour_points": per_contour_points,
    }


def point_delta_preview(gA, gB, emA, emB, limit=10):
    """
    If outline structure matches (same number of contours and points per contour),
    compute coordinate deltas and report first mismatches.
    Deltas are reported in raw font units; normalization can be inferred via em.
    """
    if gA is None or gB is None:
        return None

    try:
        la = gA.foreground
        lb = gB.foreground
    except Exception:
        return None

    ca = []
    cb = []
    try:
        for c in la:
            ca.append([(pt.x, pt.y, bool(pt.on_curve)) for pt in c])
        for c in lb:
            cb.append([(pt.x, pt.y, bool(pt.on_curve)) for pt in c])
    except Exception:
        return None

    if len(ca) != len(cb):
        return {"comparable": False, "reason": "different contour count"}

    for i in range(len(ca)):
        if len(ca[i]) != len(cb[i]):
            return {
                "comparable": False,
                "reason": f"point count differs in contour {i}",
            }

    max_dx = 0.0
    max_dy = 0.0
    mismatches = []

    for ci in range(len(ca)):
        for pi in range(len(ca[ci])):
            xa, ya, ona = ca[ci][pi]
            xb, yb, onb = cb[ci][pi]

            dx = xb - xa
            dy = yb - ya
            if abs(dx) > max_dx:
                max_dx = abs(dx)
            if abs(dy) > max_dy:
                max_dy = abs(dy)

            if dx != 0 or dy != 0 or ona != onb:
                if len(mismatches) < limit:
                    mismatches.append(
                        {
                            "contour": ci,
                            "point": pi,
                            "A": {"x": xa, "y": ya, "on": ona},
                            "B": {"x": xb, "y": yb, "on": onb},
                            "d": {
                                "dx": dx,
                                "dy": dy,
                                "dx_norm": (dx / emB) if emB else None,
                                "dy_norm": (dy / emB) if emB else None,
                            },
                        }
                    )

    return {
        "comparable": True,
        "max_dx": max_dx,
        "max_dy": max_dy,
        "mismatches": mismatches,
    }


def refs_set_from_snapshot(snap):
    """Normalize references into a set for readable diffs."""
    out = set()
    for refname, t in snap.get("references", []):
        out.add((refname, tuple(t)))
    return out


def glyph_snapshot(g, em):
    """Collect properties worth diffing, including a normalized outline hash."""
    snap = {
        "name": g.glyphname,
        "unicode": getattr(g, "unicode", -1),
        "encoding_slot": getattr(g, "encoding", None),  # debug only
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
    Map stable glyph keys -> entry with label + snapshot.
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

    em_a = getattr(fa, "em", None) or 1000
    em_b = getattr(fb, "em", None) or 1000

    glyphsA_by_name = {g.glyphname: g for g in fa.glyphs()}
    glyphsB_by_name = {g.glyphname: g for g in fb.glyphs()}

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

        # We'll print even if only outline_hash differs, but include more context.
        if not diff:
            continue

        changed += 1
        print(f"\n[{k}] {ga['label']}  vs  {gb['label']}")

        # Core field diffs (ordered)
        preferred_order = [
            "width",
            "bbox_norm",
            "bbox",
            "outline_hash",
            "has_outlines",
            "references",
            "unicode",
            "name",
            "encoding_slot",
            "vwidth",
        ]

        for fld in preferred_order:
            if fld in diff:
                v = diff[fld]
                print(f"  - {fld}: {v['A']}  ->  {v['B']}")

        for fld in diff:
            if fld not in preferred_order:
                v = diff[fld]
                print(f"  - {fld}: {v['A']}  ->  {v['B']}")

        # Extra diagnostics (even if not in diff)
        gA_obj = glyphsA_by_name.get(sa["name"])
        gB_obj = glyphsB_by_name.get(sb["name"])

        # Outline stats
        sta = outline_stats(gA_obj)
        stb = outline_stats(gB_obj)
        if sta != stb:
            print(f"  - outline_stats: {sta}  ->  {stb}")

        # Readable refs added/removed (more useful than raw list diffs)
        ra = refs_set_from_snapshot(sa)
        rb = refs_set_from_snapshot(sb)
        if ra != rb:
            removed = sorted(list(ra - rb))
            added = sorted(list(rb - ra))
            if removed:
                print(
                    f"  - references_removed: {removed[:12]}"
                    + (" ..." if len(removed) > 12 else "")
                )
            if added:
                print(
                    f"  - references_added: {added[:12]}"
                    + (" ..." if len(added) > 12 else "")
                )

        # Point delta preview (only if structure matches)
        pv = point_delta_preview(gA_obj, gB_obj, em_a, em_b, limit=10)
        if pv:
            if pv.get("comparable"):
                if pv["max_dx"] != 0 or pv["max_dy"] != 0 or pv["mismatches"]:
                    print(
                        f"  - point_deltas: max_dx={pv['max_dx']} max_dy={pv['max_dy']}"
                    )
                    for mm in pv["mismatches"]:
                        print(
                            f"    * c{mm['contour']} p{mm['point']}: "
                            f"({mm['A']['x']},{mm['A']['y']},{mm['A']['on']}) -> "
                            f"({mm['B']['x']},{mm['B']['y']},{mm['B']['on']}) "
                            f"dx={mm['d']['dx']} dy={mm['d']['dy']}"
                        )
            else:
                print(f"  - point_compare: not comparable ({pv.get('reason')})")

    if changed == 0:
        print("(none)")


if __name__ == "__main__":
    main()
