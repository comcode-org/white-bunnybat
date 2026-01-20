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
#   outline hash, and affine fit diagnostics
#
# Change from previous version:
# - If a glyph is "affine equivalent" (near-perfect scale+translate fit with
#   small residuals), point-by-point diffs are SUPPRESSED automatically.

import sys
import json
import hashlib
import math

import fontforge


def font_metrics(f):
    out = {}
    out["em"] = getattr(f, "em", None)
    out["ascent"] = getattr(f, "ascent", None)
    out["descent"] = getattr(f, "descent", None)
    for k in [
        "os2_typoascent", "os2_typodescent", "os2_typolinegap",
        "os2_winascent", "os2_windescent",
        "hhea_ascent", "hhea_descent", "hhea_linegap",
    ]:
        out[k] = getattr(f, k, None)
    return out


def dict_diff(a, b):
    changes = {}
    keys = set(a.keys()) | set(b.keys())
    for k in sorted(keys):
        if a.get(k) != b.get(k):
            changes[k] = {"A": a.get(k), "B": b.get(k)}
    return changes


def glyph_key(g):
    u = getattr(g, "unicode", -1)
    if u is not None and u != -1:
        return f"U+{u:04X}"
    return f"name:{g.glyphname}"


def glyph_label(g):
    u = getattr(g, "unicode", -1)
    if u is not None and u != -1:
        return f"U+{u:04X} ({g.glyphname})"
    enc = getattr(g, "encoding", None)
    if enc is None:
        return f"{g.glyphname} (unencoded)"
    return f"{g.glyphname} (unencoded, enc={enc})"


def normalize_transform(transform, em):
    t = list(transform)
    if em and len(t) == 6:
        t[4] = t[4] / em
        t[5] = t[5] / em
    return [round(x, 8) for x in t]


def layer_outline_signature(g, em):
    try:
        layer = g.foreground
    except Exception:
        return None

    contours_out = []

    refs_out = []
    try:
        for (refname, transform) in g.references:
            refs_out.append([refname, normalize_transform(transform, em)])
    except Exception:
        pass

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
            return {"comparable": False, "reason": f"point count differs in contour {i}"}

    max_dx = 0.0
    max_dy = 0.0
    mismatches = []

    for ci in range(len(ca)):
        for pi in range(len(ca[ci])):
            xa, ya, ona = ca[ci][pi]
            xb, yb, onb = cb[ci][pi]
            dx = xb - xa
            dy = yb - ya
            max_dx = max(max_dx, abs(dx))
            max_dy = max(max_dy, abs(dy))
            if dx != 0 or dy != 0 or ona != onb:
                if len(mismatches) < limit:
                    mismatches.append({
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
                    })

    return {
        "comparable": True,
        "max_dx": max_dx,
        "max_dy": max_dy,
        "mismatches": mismatches,
    }


def _fit_scale_translate_1d(xs, ys):
    n = len(xs)
    if n == 0:
        return None

    mx = sum(xs) / n
    my = sum(ys) / n

    sxx = 0.0
    sxy = 0.0
    for x, y in zip(xs, ys):
        dx = x - mx
        sxx += dx * dx
        sxy += dx * (y - my)

    if sxx == 0.0:
        s = 0.0
        t = my
    else:
        s = sxy / sxx
        t = my - s * mx

    se = 0.0
    max_abs = 0.0
    for x, y in zip(xs, ys):
        yhat = s * x + t
        e = y - yhat
        se += e * e
        if abs(e) > max_abs:
            max_abs = abs(e)

    rmse = math.sqrt(se / n)
    return s, t, rmse, max_abs


def affine_fit_glyph(gA, gB):
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
            ca.append([(pt.x, pt.y) for pt in c])
        for c in lb:
            cb.append([(pt.x, pt.y) for pt in c])
    except Exception:
        return None

    if len(ca) != len(cb):
        return {"comparable": False, "reason": "different contour count"}

    for i in range(len(ca)):
        if len(ca[i]) != len(cb[i]):
            return {"comparable": False, "reason": f"point count differs in contour {i}"}

    xsA, ysA, xsB, ysB = [], [], [], []
    for ci in range(len(ca)):
        for pi in range(len(ca[ci])):
            xa, ya = ca[ci][pi]
            xb, yb = cb[ci][pi]
            xsA.append(xa); ysA.append(ya)
            xsB.append(xb); ysB.append(yb)

    fx = _fit_scale_translate_1d(xsA, xsB)
    fy = _fit_scale_translate_1d(ysA, ysB)
    if fx is None or fy is None:
        return None

    sx, tx, rmse_x, maxerr_x = fx
    sy, ty, rmse_y, maxerr_y = fy

    rmse_xy = math.sqrt(rmse_x * rmse_x + rmse_y * rmse_y)
    maxerr_xy = math.sqrt(maxerr_x * maxerr_x + maxerr_y * maxerr_y)

    return {
        "comparable": True,
        "sx": sx, "tx": tx,
        "sy": sy, "ty": ty,
        "rmse_x": rmse_x, "rmse_y": rmse_y,
        "rmse_xy": rmse_xy,
        "maxerr_x": maxerr_x, "maxerr_y": maxerr_y,
        "maxerr_xy": maxerr_xy,
        "n_points": len(xsA),
    }


def refs_set_from_snapshot(snap):
    out = set()
    for refname, t in snap.get("references", []):
        out.add((refname, tuple(t)))
    return out


def glyph_snapshot(g, em):
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

    try:
        bb = g.boundingBox()
        snap["bbox"] = tuple(round(x, 3) for x in bb)
        if em:
            snap["bbox_norm"] = tuple(round((x / em), 8) for x in bb)
    except Exception:
        snap["bbox"] = None
        snap["bbox_norm"] = None

    try:
        snap["has_outlines"] = (not g.foreground.isEmpty())
    except Exception:
        snap["has_outlines"] = None

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
    em = getattr(font, "em", None) or 1000
    idx = {}
    for g in font.glyphs():
        k = glyph_key(g)
        entry = {"label": glyph_label(g), "snap": glyph_snapshot(g, em)}
        if k in idx:
            idx[f"{k}/{g.glyphname}"] = entry
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

    ma = font_metrics(fa)
    mb = font_metrics(fb)
    metric_changes = dict_diff(ma, mb)

    print("== Font-wide metric differences ==")
    if metric_changes:
        for k, v in metric_changes.items():
            print(f"- {k}: {v['A']}  ->  {v['B']}")
    else:
        print("(none)")

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

    # Affine equivalence thresholds (in font units of B)
    AFFINE_RMSE_THRESHOLD = 1.0
    AFFINE_MAXERR_THRESHOLD = 2.0

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

        gA_obj = glyphsA_by_name.get(sa["name"])
        gB_obj = glyphsB_by_name.get(sb["name"])

        sta = outline_stats(gA_obj)
        stb = outline_stats(gB_obj)
        if sta != stb:
            print(f"  - outline_stats: {sta}  ->  {stb}")

        ra = refs_set_from_snapshot(sa)
        rb = refs_set_from_snapshot(sb)
        if ra != rb:
            removed = sorted(list(ra - rb))
            added = sorted(list(rb - ra))
            if removed:
                print(f"  - references_removed: {removed[:12]}" + (" ..." if len(removed) > 12 else ""))
            if added:
                print(f"  - references_added: {added[:12]}" + (" ..." if len(added) > 12 else ""))

        # Affine fit (scale+translate per axis)
        affine_equiv = False
        aff = affine_fit_glyph(gA_obj, gB_obj)
        if aff:
            if aff.get("comparable"):
                sx = aff["sx"]; tx = aff["tx"]
                sy = aff["sy"]; ty = aff["ty"]
                rmse_xy = aff["rmse_xy"]
                maxerr_xy = aff["maxerr_xy"]
                print(
                    "  - affine_fit: "
                    f"sx={sx:.9g} tx={tx:.6g}, sy={sy:.9g} ty={ty:.6g}; "
                    f"rmse_xy={rmse_xy:.6g} maxerr_xy={maxerr_xy:.6g} "
                    f"(n={aff['n_points']})"
                )
                if rmse_xy <= AFFINE_RMSE_THRESHOLD and maxerr_xy <= AFFINE_MAXERR_THRESHOLD:
                    affine_equiv = True
                    print(
                        f"  - affine_equivalent: YES "
                        f"(rmse_xy<={AFFINE_RMSE_THRESHOLD}, maxerr_xy<={AFFINE_MAXERR_THRESHOLD})"
                    )
            else:
                print(f"  - affine_fit: not comparable ({aff.get('reason')})")

        # Point diffs: suppress if affine equivalent
        if not affine_equiv:
            pv = point_delta_preview(gA_obj, gB_obj, em_a, em_b, limit=10)
            if pv:
                if pv.get("comparable"):
                    if pv["max_dx"] != 0 or pv["max_dy"] != 0 or pv["mismatches"]:
                        print(f"  - point_deltas: max_dx={pv['max_dx']} max_dy={pv['max_dy']}")
                        for mm in pv["mismatches"]:
                            print(
                                f"    * c{mm['contour']} p{mm['point']}: "
                                f"({mm['A']['x']},{mm['A']['y']},{mm['A']['on']}) -> "
                                f"({mm['B']['x']},{mm['B']['y']},{mm['B']['on']}) "
                                f"dx={mm['d']['dx']} dy={mm['d']['dy']}"
                            )
                else:
                    print(f"  - point_compare: not comparable ({pv.get('reason')})")
        else:
            print("  - point_deltas: (suppressed; affine equivalent)")

    if changed == 0:
        print("(none)")


if __name__ == "__main__":
    main()
