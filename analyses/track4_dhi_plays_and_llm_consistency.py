import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import polars as pl

ATLAS_SRC = Path(r"C:\Users\philip\Documents\ncs-relinquished-atlas\src")
sys.path.insert(0, str(ATLAS_SRC))

from loader import (
    DEFAULT_FACTPAGES_WELLS,
    deduplicate_records,
    find_duplicate_licence_groups,
    load_raw_records,
    safe_canonical_volume_msmo3,
)

OUT_DIR = Path(r"C:\Users\philip\Documents\ncs-relinquished-atlas\analyses")
OUT_JSON = OUT_DIR / "track4_findings.json"
OUT_MD = OUT_DIR / "track4_findings.md"

STAGE_PREDRILL_PRIORITY = {
    "final": 6,
    "drill_or_drop": 5,
    "intermediate": 4,
    "award": 3,
    "application": 2,
    "prior_licence": 1,
    "unknown": 0,
    "post_well": -1,
}

REPORT_DISCOVERY_RESULTS = {
    "discovery_oil",
    "discovery_gas",
    "discovery_oil_gas",
    "discovery_non_commercial",
    "technical_discovery",
}

REPORT_COMMERCIAL_DISCOVERY_RESULTS = {
    "discovery_oil",
    "discovery_gas",
    "discovery_oil_gas",
}

REPORT_DRY_RESULTS = {
    "dry",
    "dry_with_shows",
    "dry_no_shows",
    "water_wet_reservoir",
    "no_reservoir",
}

FACTPAGES_DISCOVERY_CONTENTS = {
    "OIL",
    "GAS",
    "OIL/GAS",
    "GAS/CONDENSATE",
    "OIL/GAS/CONDENSATE",
}

FACTPAGES_SHOWS_CONTENTS = {
    "SHOWS",
    "OIL SHOWS",
    "GAS SHOWS",
    "OIL/GAS SHOWS",
}

FACTPAGES_DRY_CONTENTS = {
    "DRY",
    "WATER",
    "WATER/GAS",
}


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float | None:
    n = a + b + c + d
    if n == 0:
        return None
    r1 = a + b
    r2 = c + d
    c1 = a + c
    denom = math.comb(n, c1)
    if denom == 0:
        return None

    def hyper(k: int) -> float:
        return (math.comb(r1, k) * math.comb(r2, c1 - k)) / denom

    p_obs = hyper(a)
    lo = max(0, c1 - r2)
    hi = min(r1, c1)
    total = 0.0
    for k in range(lo, hi + 1):
        pk = hyper(k)
        if pk <= p_obs + 1e-12:
            total += pk
    return min(1.0, total)


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    s = name.strip().lower()
    s = re.sub(r"\b(prospect|lead|segment|structure|discovery|play)\b", "", s)
    s = re.sub(r"[^a-z0-9æøå]+", " ", s).strip()
    return s


def extract_year(date_str: str | None) -> int | None:
    if not date_str:
        return None
    m = re.search(r"(19\d{2}|20\d{2})", str(date_str))
    return int(m.group(1)) if m else None


def get_report_year(rec: dict[str, Any]) -> int | None:
    lic = rec.get("licence") or {}
    doc = rec.get("document") or {}
    for val in (lic.get("relinquishment_date"), doc.get("date")):
        y = extract_year(val)
        if y:
            return y
    return None


def normalize_pg(val: Any) -> float | None:
    if not isinstance(val, (int, float)) or isinstance(val, bool):
        return None
    v = float(val)
    if v < 0:
        return None
    if 1.0 < v <= 100.0:
        v = v / 100.0
    if v > 1.0:
        return None
    return v


def extract_crest_depth_m(geom: dict[str, Any]) -> float | None:
    cd = geom.get("crest_depth")
    if not isinstance(cd, dict):
        return None
    us = (cd.get("_derived") or {}).get("unit_scale") or {}
    cunit = us.get("canonical_unit")
    cval = (us.get("values") or {}).get("value")
    if isinstance(cval, (int, float)) and not isinstance(cval, bool) and cunit == "m":
        val = float(cval)
        if 100.0 <= val <= 9000.0:
            return val
    raw_val = cd.get("value")
    raw_unit = str(cd.get("unit") or "").lower().strip()
    if isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool):
        v = float(raw_val)
        if "ms" in raw_unit and "msl" not in raw_unit:
            return None
        if raw_unit == "km":
            v *= 1000.0
        elif "ft" in raw_unit:
            v *= 0.3048
        if 100.0 <= v <= 9000.0:
            return v
    return None


def extract_closure_area_km2(geom: dict[str, Any]) -> float | None:
    ca = geom.get("closure_area")
    if not isinstance(ca, dict):
        return None
    val = ca.get("value")
    if isinstance(val, (int, float)) and not isinstance(val, bool) and val > 0:
        return float(val)
    return None


def extract_best_volume_msmo3(assessment: dict[str, Any]) -> float | None:
    vols = assessment.get("volumes") or []
    rec_oe = []
    rec_parts = []
    rec_any = []
    for v in vols:
        if not isinstance(v, dict):
            continue
        if v.get("basis") != "recoverable":
            continue
        m = safe_canonical_volume_msmo3(v, "mean")
        if m is None or m <= 0:
            continue
        phase = str(v.get("phase") or "").lower()
        if phase in ("oil_equivalent", "total_hc"):
            rec_oe.append(m)
        elif phase in ("oil", "gas", "condensate", "associated_gas"):
            rec_parts.append((phase, m))
        rec_any.append(m)
    if rec_oe:
        return max(rec_oe)
    if rec_parts:
        by_phase: dict[str, float] = {}
        for ph, val in rec_parts:
            by_phase[ph] = max(by_phase.get(ph, 0.0), val)
        return sum(by_phase.values())
    if rec_any:
        return max(rec_any)
    return None


def sort_assessments_predrill(assessments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        assessments,
        key=lambda a: STAGE_PREDRILL_PRIORITY.get(str(a.get("stage") or "unknown"), 0),
        reverse=True,
    )


def extract_primary_period(prospect: dict[str, Any]) -> str:
    targets = prospect.get("targets") or []
    ranked = sorted(
        [t for t in targets if isinstance(t, dict)],
        key=lambda t: (t.get("rank") if isinstance(t.get("rank"), int) else 99),
    )
    for t in ranked:
        res = t.get("reservoir") or {}
        per = ((res.get("chrono") or {}).get("period"))
        if per:
            return str(per).strip()
        litho_text = json.dumps(res).lower()
        if "basement" in litho_text:
            return "Basement"
    text_blob = " ".join(
        str(x or "")
        for x in (
            prospect.get("summary"),
            json.dumps(prospect.get("geological_concept") or ""),
            json.dumps(prospect.get("play") or ""),
        )
    ).lower()
    if "basement" in text_blob:
        return "Basement"
    return "Unknown"


def depth_bin(depth_m: float | None) -> str:
    if depth_m is None:
        return "Unknown"
    if depth_m < 1500:
        return "<1500 m"
    if depth_m < 2500:
        return "1500-2500 m"
    if depth_m < 3500:
        return "2500-3500 m"
    if depth_m < 4500:
        return "3500-4500 m"
    return ">4500 m"


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-30) + xi):
            inside = not inside
        j = i
    return inside


def point_in_polygon_coords(x: float, y: float, poly_coords: list[list[list[float]]]) -> bool:
    if not poly_coords or not point_in_ring(x, y, poly_coords[0]):
        return False
    for hole in poly_coords[1:]:
        if point_in_ring(x, y, hole):
            return False
    return True


def point_in_geometry(lon: float, lat: float, geom: dict[str, Any]) -> bool:
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if not coords:
        return False
    if gtype == "Polygon":
        return point_in_polygon_coords(lon, lat, coords)
    if gtype == "MultiPolygon":
        return any(point_in_polygon_coords(lon, lat, poly) for poly in coords)
    return False


def geom_bbox(geom: dict[str, Any]) -> tuple[float, float, float, float] | None:
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if not coords:
        return None
    xs: list[float] = []
    ys: list[float] = []
    if gtype == "Polygon":
        for ring in coords:
            for pt in ring:
                xs.append(pt[0])
                ys.append(pt[1])
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                for pt in ring:
                    xs.append(pt[0])
                    ys.append(pt[1])
    else:
        return None
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def project_geometry_meters(
    geom: dict[str, Any], lon0: float, lat0: float
) -> list[list[list[tuple[float, float]]]]:
    kx = 111320.0 * math.cos(math.radians(lat0))
    ky = 110540.0

    def proj_poly(poly: list[list[list[float]]]) -> list[list[tuple[float, float]]]:
        return [
            [((pt[0] - lon0) * kx, (pt[1] - lat0) * ky) for pt in ring]
            for ring in poly
            if len(ring) >= 3
        ]

    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
    if gtype == "Polygon":
        p = proj_poly(coords)
        return [p] if p else []
    if gtype == "MultiPolygon":
        out = []
        for poly in coords:
            p = proj_poly(poly)
            if p:
                out.append(p)
        return out
    return []


def ring_signed_area_and_centroid(ring: list[tuple[float, float]]) -> tuple[float, float, float]:
    n = len(ring)
    if n < 3:
        return 0.0, 0.0, 0.0
    area2 = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        area2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area = 0.5 * area2
    if abs(area) < 1e-9:
        mx = sum(p[0] for p in ring) / n
        my = sum(p[1] for p in ring) / n
        return 0.0, mx, my
    return area, cx / (6.0 * area), cy / (6.0 * area)


def multipoly_area_and_centroid(
    mpoly: list[list[list[tuple[float, float]]]]
) -> tuple[float, float, float]:
    total_area = 0.0
    wx = 0.0
    wy = 0.0
    for poly in mpoly:
        if not poly:
            continue
        a_out, cx_out, cy_out = ring_signed_area_and_centroid(poly[0])
        a_out = abs(a_out)
        total_area += a_out
        wx += cx_out * a_out
        wy += cy_out * a_out
        for hole in poly[1:]:
            a_h, cx_h, cy_h = ring_signed_area_and_centroid(hole)
            a_h = abs(a_h)
            total_area -= a_h
            wx -= cx_h * a_h
            wy -= cy_h * a_h
    if total_area <= 1e-9:
        pts = [pt for poly in mpoly for ring in poly for pt in ring]
        if not pts:
            return 0.0, 0.0, 0.0
        return 0.0, sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    return total_area, wx / total_area, wy / total_area


def scanline_intervals(
    mpoly: list[list[list[tuple[float, float]]]], y: float
) -> list[tuple[float, float]]:
    xs: list[float] = []
    for poly in mpoly:
        for ring in poly:
            n = len(ring)
            for i in range(n):
                x0, y0 = ring[i]
                x1, y1 = ring[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
    xs.sort()
    intervals = []
    for i in range(0, len(xs) - 1, 2):
        if xs[i + 1] > xs[i]:
            intervals.append((xs[i], xs[i + 1]))
    return intervals


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    intervals.sort()
    merged = [intervals[0]]
    for a, b in intervals[1:]:
        pa, pb = merged[-1]
        if a <= pb:
            merged[-1] = (pa, max(pb, b))
        else:
            merged.append((a, b))
    return merged


def intervals_intersection_len(
    iv1: list[tuple[float, float]], iv2: list[tuple[float, float]]
) -> float:
    i = j = 0
    total = 0.0
    while i < len(iv1) and j < len(iv2):
        lo = max(iv1[i][0], iv2[j][0])
        hi = min(iv1[i][1], iv2[j][1])
        if hi > lo:
            total += hi - lo
        if iv1[i][1] < iv2[j][1]:
            i += 1
        else:
            j += 1
    return total


def compute_polygon_pair_metrics(
    geom1: dict[str, Any], geom2: dict[str, Any], n_slices: int = 350
) -> dict[str, float] | None:
    bb1 = geom_bbox(geom1)
    bb2 = geom_bbox(geom2)
    if not bb1 or not bb2:
        return None
    lon0 = 0.25 * (bb1[0] + bb1[2] + bb2[0] + bb2[2])
    lat0 = 0.25 * (bb1[1] + bb1[3] + bb2[1] + bb2[3])
    mp1 = project_geometry_meters(geom1, lon0, lat0)
    mp2 = project_geometry_meters(geom2, lon0, lat0)
    if not mp1 or not mp2:
        return None
    area1, cx1, cy1 = multipoly_area_and_centroid(mp1)
    area2, cx2, cy2 = multipoly_area_and_centroid(mp2)
    if area1 <= 1.0 or area2 <= 1.0:
        return None
    centroid_dist_m = math.hypot(cx1 - cx2, cy1 - cy2)

    all_y = [pt[1] for mp in (mp1, mp2) for poly in mp for ring in poly for pt in ring]
    ymin, ymax = min(all_y), max(all_y)
    if ymax <= ymin:
        return None

    dy = (ymax - ymin) / n_slices
    inter_area = 0.0
    union_area = 0.0
    for k in range(n_slices):
        y = ymin + (k + 0.5) * dy
        iv1 = merge_intervals(scanline_intervals(mp1, y))
        iv2 = merge_intervals(scanline_intervals(mp2, y))
        if not iv1 and not iv2:
            continue
        if iv1 and iv2:
            inter_len = intervals_intersection_len(iv1, iv2)
            inter_area += inter_len * dy
        u_iv = merge_intervals(iv1 + iv2)
        union_area += sum(b - a for a, b in u_iv) * dy

    iou = (inter_area / union_area) if union_area > 0 else 0.0
    iou = max(0.0, min(1.0, iou))
    area1_km2 = area1 / 1e6
    area2_km2 = area2 / 1e6
    area_ratio = min(area1_km2, area2_km2) / max(area1_km2, area2_km2)
    area_pct_diff = abs(area1_km2 - area2_km2) / (0.5 * (area1_km2 + area2_km2)) * 100.0
    return {
        "iou": iou,
        "centroid_dist_m": centroid_dist_m,
        "area1_km2": area1_km2,
        "area2_km2": area2_km2,
        "area_ratio": area_ratio,
        "area_pct_diff": area_pct_diff,
    }


def extract_prospect_summary(
    stem: str, rec: dict[str, Any], p: dict[str, Any]
) -> dict[str, Any]:
    lic = rec.get("licence") or {}
    area_basin = str(lic.get("area") or "Unknown")
    report_year = get_report_year(rec)

    assessments = [a for a in (p.get("assessments") or []) if isinstance(a, dict)]
    ordered = sort_assessments_predrill(assessments)

    pg_val = None
    pg_before_dhi = None
    for a in ordered:
        r = a.get("risk") or {}
        if pg_val is None:
            pg_val = normalize_pg(r.get("pg"))
        if pg_before_dhi is None:
            pg_before_dhi = normalize_pg(r.get("pg_before_dhi"))

    vol_mean = None
    for a in ordered:
        vol_mean = extract_best_volume_msmo3(a)
        if vol_mean is not None:
            break

    crest_m = None
    closure_km2 = None
    for a in ordered:
        g = a.get("geometry") or {}
        if crest_m is None:
            crest_m = extract_crest_depth_m(g)
        if closure_km2 is None:
            closure_km2 = extract_closure_area_km2(g)

    dhi_any_assessed = False
    dhi_observed = None
    dhi_support = None
    dhi_types: set[str] = set()
    dhi_methods: set[str] = set()
    dhi_has_uplift = False
    dhi_csem_anomaly = False
    for a in ordered:
        dhi = a.get("dhi")
        if not isinstance(dhi, dict):
            continue
        dhi_any_assessed = True
        obs = dhi.get("observed")
        sup = dhi.get("support")
        if dhi_observed is None and isinstance(obs, bool):
            dhi_observed = obs
        elif obs is True:
            dhi_observed = True
        if dhi_support is None and sup is not None:
            dhi_support = str(sup).lower()
        elif sup == "positive":
            dhi_support = "positive"
        for dt in (dhi.get("types") or []):
            dhi_types.add(str(dt).lower())
        for dm in (dhi.get("methods") or []):
            dhi_methods.add(str(dm).lower())
        if dhi.get("uplift"):
            dhi_has_uplift = True
        csem = dhi.get("csem")
        if isinstance(csem, dict) and csem.get("anomaly"):
            dhi_csem_anomaly = True

    if dhi_observed is True and dhi_support == "positive":
        dhi_category = "positive_dhi"
    elif dhi_observed is True:
        dhi_category = "observed_nonpositive_dhi"
    elif dhi_observed is False or dhi_support == "negative":
        dhi_category = "negative_or_no_dhi"
    elif dhi_any_assessed:
        dhi_category = "assessed_unclear"
    else:
        dhi_category = "not_assessed"

    status = str(p.get("status_at_report") or "unknown")
    drilling_list = [d for d in (p.get("drilling") or []) if isinstance(d, dict)]
    drill_results = [str(d.get("result") or "").lower() for d in drilling_list]
    drill_wells = [str(d.get("well_name") or "").strip() for d in drilling_list if d.get("well_name")]

    report_drilled = False
    report_discovery = False
    report_commercial_disc = False
    report_gas_only = False
    report_shows_dry = False

    if status in ("drilled_discovery", "discovery_marginal", "drilled_dry") or drilling_list:
        if any(r in REPORT_DISCOVERY_RESULTS or r in REPORT_DRY_RESULTS for r in drill_results) or status in (
            "drilled_discovery",
            "discovery_marginal",
            "drilled_dry",
        ):
            report_drilled = True

    if status in ("drilled_discovery", "discovery_marginal") or any(
        r in REPORT_DISCOVERY_RESULTS for r in drill_results
    ):
        report_discovery = True
    if status == "drilled_discovery" or any(
        r in REPORT_COMMERCIAL_DISCOVERY_RESULTS for r in drill_results
    ):
        report_commercial_disc = True
    if any(r == "discovery_gas" for r in drill_results) and not any(
        r in ("discovery_oil", "discovery_oil_gas") for r in drill_results
    ):
        report_gas_only = True
    if not report_discovery and any(r == "dry_with_shows" for r in drill_results):
        report_shows_dry = True

    period = extract_primary_period(p)
    hpht_flag = bool(p.get("hpht"))

    return {
        "stem": stem,
        "licence_id": str(lic.get("licence_id") or ""),
        "basin": area_basin,
        "report_year": report_year,
        "prospect_id": str(p.get("prospect_id") or ""),
        "name": str(p.get("name") or ""),
        "norm_name": normalize_name(p.get("name")),
        "classification": str(p.get("classification") or ""),
        "status_at_report": status,
        "period": period,
        "crest_depth_m": crest_m,
        "depth_bin": depth_bin(crest_m),
        "closure_area_km2": closure_km2,
        "pg": pg_val,
        "pg_before_dhi": pg_before_dhi,
        "vol_mean_msmo3": vol_mean,
        "hpht": hpht_flag,
        "dhi_assessed": dhi_any_assessed,
        "dhi_observed": dhi_observed,
        "dhi_support": dhi_support,
        "dhi_category": dhi_category,
        "dhi_types": sorted(dhi_types),
        "dhi_methods": sorted(dhi_methods),
        "dhi_has_uplift": dhi_has_uplift,
        "dhi_csem_anomaly": dhi_csem_anomaly,
        "report_drilled": report_drilled,
        "report_discovery": report_discovery,
        "report_commercial_disc": report_commercial_disc,
        "report_gas_only": report_gas_only,
        "report_shows_dry": report_shows_dry,
        "report_drill_results": drill_results,
        "report_drill_wells": drill_wells,
        "fp_wells_all": [],
        "fp_wells_post": [],
        "poly_area_km2": None,
    }


def attach_factpages_wells(
    prospects: list[dict[str, Any]],
    kept_geo: dict[str, dict[str, Any]],
    wells_df: pl.DataFrame,
) -> dict[str, Any]:
    wildcats = wells_df.filter(
        (pl.col("wlbPurpose") == "WILDCAT")
        & pl.col("wlbNsDecDeg").is_not_null()
        & pl.col("wlbEwDecDeg").is_not_null()
    )
    well_rows = wildcats.select(
        [
            "wlbWellboreName",
            "wlbNsDecDeg",
            "wlbEwDecDeg",
            "wlbContent",
            "wlbDiscoveryWellbore",
            "wlbEntryYear",
            "wlbCompletionYear",
            "wlbMainArea",
            "wlbDiscovery",
        ]
    ).to_dicts()

    by_stem_id: dict[tuple[str, str], dict[str, Any]] = {}
    by_stem_name: dict[tuple[str, str], dict[str, Any]] = {}
    for row in prospects:
        by_stem_id[(row["stem"], row["prospect_id"])] = row
        if row["norm_name"]:
            by_stem_name[(row["stem"], row["norm_name"])] = row

    polygons_linked = 0
    prospects_with_poly = set()

    for stem, geo in kept_geo.items():
        for feat in (geo.get("features") or []):
            props = feat.get("properties") or {}
            if props.get("layer") == "licence":
                continue
            geom = feat.get("geometry") or {}
            if geom.get("type") not in ("Polygon", "MultiPolygon"):
                continue
            bb = geom_bbox(geom)
            if not bb:
                continue

            target_row = None
            puid = str(props.get("prospect_uid") or "")
            if "::" in puid:
                pid = puid.split("::")[-1]
                target_row = by_stem_id.get((stem, pid))
            if target_row is None:
                pname = normalize_name(props.get("prospect_name"))
                if pname:
                    target_row = by_stem_name.get((stem, pname))
            if target_row is None:
                continue

            polygons_linked += 1
            prospects_with_poly.add((stem, target_row["prospect_id"]))
            akm2 = props.get("area_km2_geometry")
            if isinstance(akm2, (int, float)) and akm2 > 0:
                if target_row["poly_area_km2"] is None or props.get("is_primary"):
                    target_row["poly_area_km2"] = float(akm2)

            xmin, ymin, xmax, ymax = bb
            for w in well_rows:
                wx = w["wlbEwDecDeg"]
                wy = w["wlbNsDecDeg"]
                if xmin <= wx <= xmax and ymin <= wy <= ymax:
                    if point_in_geometry(wx, wy, geom):
                        wname = w["wlbWellboreName"]
                        if not any(x["well"] == wname for x in target_row["fp_wells_all"]):
                            content = str(w["wlbContent"] or "").strip().upper()
                            is_disc = (w["wlbDiscoveryWellbore"] == "YES") or (
                                content in FACTPAGES_DISCOVERY_CONTENTS
                            )
                            is_shows = (not is_disc) and (content in FACTPAGES_SHOWS_CONTENTS)
                            is_gas_only = content == "GAS"
                            w_entry = w["wlbEntryYear"]
                            w_rec = {
                                "well": wname,
                                "content": content,
                                "is_disc": is_disc,
                                "is_shows": is_shows,
                                "is_gas_only": is_gas_only,
                                "entry_year": w_entry,
                                "discovery_name": w["wlbDiscovery"],
                            }
                            target_row["fp_wells_all"].append(w_rec)
                            ry = target_row["report_year"]
                            if ry and w_entry and w_entry > ry:
                                target_row["fp_wells_post"].append(w_rec)

    for row in prospects:
        fp_all = row["fp_wells_all"]
        fp_post = row["fp_wells_post"]
        row["fp_drilled"] = len(fp_all) > 0
        row["fp_discovery"] = any(w["is_disc"] for w in fp_all)
        row["fp_shows_only"] = (not row["fp_discovery"]) and any(w["is_shows"] for w in fp_all)
        row["fp_gas_only"] = row["fp_discovery"] and all(
            w["is_gas_only"] for w in fp_all if w["is_disc"]
        )
        row["post_redrilled"] = (not row["report_drilled"]) and len(fp_post) > 0
        row["post_redrill_discovery"] = row["post_redrilled"] and any(
            w["is_disc"] for w in fp_post
        )

        row["any_drilled"] = row["report_drilled"] or row["fp_drilled"]
        row["any_discovery"] = row["report_discovery"] or row["fp_discovery"]
        row["any_shows_only"] = (not row["any_discovery"]) and (
            row["report_shows_dry"] or row["fp_shows_only"]
        )
        row["any_gas_only"] = row["any_discovery"] and (
            (row["fp_discovery"] and row["fp_gas_only"])
            or (not row["fp_discovery"] and row["report_gas_only"])
        )

    return {
        "wildcat_wells_loaded": len(well_rows),
        "polygons_linked": polygons_linked,
        "prospects_with_polygon": len(prospects_with_poly),
        "prospects_report_drilled": sum(1 for r in prospects if r["report_drilled"]),
        "prospects_fp_spatial_drilled": sum(1 for r in prospects if r["fp_drilled"]),
        "prospects_any_drilled": sum(1 for r in prospects if r["any_drilled"]),
        "prospects_post_redrilled": sum(1 for r in prospects if r["post_redrilled"]),
        "prospects_post_redrill_discovery": sum(
            1 for r in prospects if r["post_redrill_discovery"]
        ),
    }


def summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    pgs = [r["pg"] for r in rows if r["pg"] is not None]
    vols = [r["vol_mean_msmo3"] for r in rows if r["vol_mean_msmo3"] is not None]
    areas = [
        r["closure_area_km2"] if r["closure_area_km2"] is not None else r["poly_area_km2"]
        for r in rows
    ]
    areas = [a for a in areas if a is not None and a > 0]
    depths = [r["crest_depth_m"] for r in rows if r["crest_depth_m"] is not None]

    drilled_any = [r for r in rows if r["any_drilled"]]
    disc_any = [r for r in drilled_any if r["any_discovery"]]
    shows_any = [r for r in drilled_any if r["any_shows_only"]]
    gas_only_any = [r for r in disc_any if r["any_gas_only"]]

    drilled_rep = [r for r in rows if r["report_drilled"]]
    disc_rep = [r for r in drilled_rep if r["report_discovery"]]

    drilled_fp = [r for r in rows if r["fp_drilled"]]
    disc_fp = [r for r in drilled_fp if r["fp_discovery"]]

    drilled_post = [r for r in rows if r["post_redrilled"]]
    disc_post = [r for r in drilled_post if r["post_redrill_discovery"]]

    drilled_pgs = [r["pg"] for r in drilled_any if r["pg"] is not None]

    return {
        "n_prospects": n,
        "mean_pg": round(statistics.mean(pgs), 4) if pgs else None,
        "median_pg": round(statistics.median(pgs), 4) if pgs else None,
        "n_pg": len(pgs),
        "mean_vol_msmo3": round(statistics.mean(vols), 2) if vols else None,
        "median_vol_msmo3": round(statistics.median(vols), 2) if vols else None,
        "n_vol": len(vols),
        "median_area_km2": round(statistics.median(areas), 2) if areas else None,
        "mean_area_km2": round(statistics.mean(areas), 2) if areas else None,
        "median_depth_m": round(statistics.median(depths), 1) if depths else None,
        "drilled_any": len(drilled_any),
        "disc_any": len(disc_any),
        "disc_rate_any": round(len(disc_any) / len(drilled_any), 4) if drilled_any else None,
        "shows_rate_among_dry": (
            round(len(shows_any) / (len(drilled_any) - len(disc_any)), 4)
            if (len(drilled_any) - len(disc_any)) > 0
            else None
        ),
        "gas_only_share_of_disc": (
            round(len(gas_only_any) / len(disc_any), 4) if disc_any else None
        ),
        "mean_pg_of_drilled": round(statistics.mean(drilled_pgs), 4) if drilled_pgs else None,
        "drilled_report": len(drilled_rep),
        "disc_report": len(disc_rep),
        "disc_rate_report": round(len(disc_rep) / len(drilled_rep), 4) if drilled_rep else None,
        "drilled_fp": len(drilled_fp),
        "disc_fp": len(disc_fp),
        "disc_rate_fp": round(len(disc_fp) / len(drilled_fp), 4) if drilled_fp else None,
        "drilled_post": len(drilled_post),
        "disc_post": len(disc_post),
        "disc_rate_post": round(len(disc_post) / len(drilled_post), 4) if drilled_post else None,
    }


def analyze_dhi(prospects: list[dict[str, Any]]) -> dict[str, Any]:
    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in prospects:
        by_cat[r["dhi_category"]].append(r)

    overall_by_cat = {k: summarize_group(v) for k, v in sorted(by_cat.items())}

    pos = by_cat["positive_dhi"]
    neg = by_cat["negative_or_no_dhi"]
    not_ass = by_cat["not_assessed"]
    obs_any = [r for r in prospects if r["dhi_observed"] is True]
    no_dhi_all = [r for r in prospects if r["dhi_observed"] is not True]

    def contrast(g1: list[dict[str, Any]], g2: list[dict[str, Any]], label: str) -> dict[str, Any]:
        s1 = summarize_group(g1)
        s2 = summarize_group(g2)
        a = s1["disc_any"]
        b = s1["drilled_any"] - a
        c = s2["disc_any"]
        d = s2["drilled_any"] - c
        p = fisher_exact_two_sided(a, b, c, d)
        return {
            "comparison": label,
            "g1_drilled": s1["drilled_any"],
            "g1_disc": a,
            "g1_rate": s1["disc_rate_any"],
            "g1_mean_pg_drilled": s1["mean_pg_of_drilled"],
            "g2_drilled": s2["drilled_any"],
            "g2_disc": c,
            "g2_rate": s2["disc_rate_any"],
            "g2_mean_pg_drilled": s2["mean_pg_of_drilled"],
            "fisher_p": round(p, 6) if p is not None else None,
        }

    contrasts = [
        contrast(pos, neg, "positive_dhi vs negative_or_no_dhi"),
        contrast(pos, no_dhi_all, "positive_dhi vs all_without_dhi_observed"),
        contrast(obs_any, neg, "any_dhi_observed vs negative_or_no_dhi"),
        contrast(obs_any, not_ass, "any_dhi_observed vs not_assessed"),
    ]

    by_basin: dict[str, Any] = {}
    for basin in ("North Sea", "Norwegian Sea", "Barents Sea"):
        b_rows = [r for r in prospects if r["basin"] == basin]
        b_pos = [r for r in b_rows if r["dhi_category"] == "positive_dhi"]
        b_obs = [r for r in b_rows if r["dhi_observed"] is True]
        b_neg = [r for r in b_rows if r["dhi_category"] == "negative_or_no_dhi"]
        b_none = [r for r in b_rows if r["dhi_observed"] is not True]
        by_basin[basin] = {
            "all": summarize_group(b_rows),
            "positive_dhi": summarize_group(b_pos),
            "any_dhi_observed": summarize_group(b_obs),
            "negative_or_no_dhi": summarize_group(b_neg),
            "no_dhi_observed": summarize_group(b_none),
            "contrast_pos_vs_no_obs": contrast(b_pos, b_none, f"{basin}: positive_dhi vs no_dhi_observed"),
            "contrast_obs_vs_no_obs": contrast(b_obs, b_none, f"{basin}: any_dhi_observed vs no_dhi_observed"),
        }

    by_dhi_type: dict[str, Any] = {}
    for dtype in (
        "flat_spot",
        "bright_spot",
        "avo_anomaly",
        "amplitude_conformance",
        "gas_chimney",
        "csem_anomaly",
        "dim_spot",
    ):
        t_rows = [r for r in prospects if dtype in r["dhi_types"]]
        t_pos = [r for r in t_rows if r["dhi_category"] == "positive_dhi"]
        by_dhi_type[dtype] = {
            "all_with_type": summarize_group(t_rows),
            "positive_with_type": summarize_group(t_pos),
        }

    uplift_deltas = []
    uplift_drilled = []
    for r in prospects:
        if r["pg"] is not None and r["pg_before_dhi"] is not None:
            delta = r["pg"] - r["pg_before_dhi"]
            uplift_deltas.append(delta)
            if r["any_drilled"]:
                uplift_drilled.append(r)

    barents_dhi_drilled_cases = []
    for r in prospects:
        if r["basin"] == "Barents Sea" and r["dhi_observed"] is True and r["any_drilled"]:
            barents_dhi_drilled_cases.append(
                {
                    "licence_id": r["licence_id"],
                    "name": r["name"],
                    "dhi_category": r["dhi_category"],
                    "dhi_types": r["dhi_types"],
                    "pg": r["pg"],
                    "crest_depth_m": r["crest_depth_m"],
                    "period": r["period"],
                    "any_discovery": r["any_discovery"],
                    "any_shows_only": r["any_shows_only"],
                    "any_gas_only": r["any_gas_only"],
                    "report_drill_results": r["report_drill_results"],
                    "fp_wells": [
                        {"well": w["well"], "content": w["content"], "is_disc": w["is_disc"]}
                        for w in r["fp_wells_all"]
                    ],
                }
            )

    return {
        "overall_by_category": overall_by_cat,
        "contrasts": contrasts,
        "by_basin": by_basin,
        "by_dhi_type": by_dhi_type,
        "pg_uplift_analysis": {
            "n_with_pg_before_dhi": len(uplift_deltas),
            "mean_pg_uplift": round(statistics.mean(uplift_deltas), 4) if uplift_deltas else None,
            "median_pg_uplift": round(statistics.median(uplift_deltas), 4) if uplift_deltas else None,
            "drilled_with_pg_before_dhi": summarize_group(uplift_drilled),
        },
        "barents_dhi_drilled_cases": barents_dhi_drilled_cases,
    }


def analyze_plays_and_depth(prospects: list[dict[str, Any]]) -> dict[str, Any]:
    by_period_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in prospects:
        per = r["period"]
        if per in ("Silurian", "Ordovician", "Quaternary"):
            per = "Other_Rare"
        by_period_rows[per].append(r)

    by_period = {
        k: summarize_group(v)
        for k, v in sorted(by_period_rows.items(), key=lambda kv: -len(kv[1]))
    }

    depth_order = ["<1500 m", "1500-2500 m", "2500-3500 m", "3500-4500 m", ">4500 m", "Unknown"]
    by_depth_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in prospects:
        by_depth_rows[r["depth_bin"]].append(r)
    by_depth = {k: summarize_group(by_depth_rows[k]) for k in depth_order if by_depth_rows[k]}

    by_basin_depth: dict[str, dict[str, Any]] = {}
    for basin in ("North Sea", "Norwegian Sea", "Barents Sea"):
        bd = {}
        for db in depth_order[:-1]:
            sub = [r for r in prospects if r["basin"] == basin and r["depth_bin"] == db]
            if sub:
                bd[db] = summarize_group(sub)
        by_basin_depth[basin] = bd

    by_basin_period: dict[str, dict[str, Any]] = {}
    for basin in ("North Sea", "Norwegian Sea", "Barents Sea"):
        bp = {}
        for per in ("Jurassic", "Cretaceous", "Paleogene", "Triassic", "Permian", "Basement"):
            sub = [r for r in prospects if r["basin"] == basin and r["period"] == per]
            if sub:
                bp[per] = summarize_group(sub)
        by_basin_period[basin] = bp

    play_depth_matrix: dict[str, dict[str, Any]] = {}
    for per in ("Jurassic", "Cretaceous", "Paleogene", "Triassic", "Permian"):
        play_depth_matrix[per] = {}
        for db in depth_order[:-1]:
            sub = [r for r in prospects if r["period"] == per and r["depth_bin"] == db]
            if len(sub) >= 5:
                play_depth_matrix[per][db] = summarize_group(sub)

    hpht_rows = [r for r in prospects if r["hpht"]]
    non_hpht_rows = [r for r in prospects if not r["hpht"]]
    deep_gt4000 = [r for r in prospects if r["crest_depth_m"] is not None and r["crest_depth_m"] >= 4000]
    shallow_barents = [
        r
        for r in prospects
        if r["basin"] == "Barents Sea" and r["crest_depth_m"] is not None and r["crest_depth_m"] < 1500
    ]
    basement_rows = [r for r in prospects if r["period"] == "Basement"]

    return {
        "by_period": by_period,
        "by_depth_bin": by_depth,
        "by_basin_depth": by_basin_depth,
        "by_basin_period": by_basin_period,
        "play_depth_matrix": play_depth_matrix,
        "special_plays": {
            "hpht_flagged": summarize_group(hpht_rows),
            "non_hpht": summarize_group(non_hpht_rows),
            "deep_ge4000m": summarize_group(deep_gt4000),
            "shallow_barents_lt1500m": summarize_group(shallow_barents),
            "basement_all": summarize_group(basement_rows),
            "basement_examples": [
                {
                    "licence_id": r["licence_id"],
                    "basin": r["basin"],
                    "name": r["name"],
                    "pg": r["pg"],
                    "vol_mean_msmo3": r["vol_mean_msmo3"],
                    "crest_depth_m": r["crest_depth_m"],
                    "any_drilled": r["any_drilled"],
                    "any_discovery": r["any_discovery"],
                }
                for r in basement_rows[:15]
            ],
        },
    }


def collect_primary_polygons(geo: dict[str, Any]) -> dict[str, tuple[dict[str, Any], str]]:
    by_name: dict[str, tuple[int, dict[str, Any], str]] = {}
    for feat in (geo.get("features") or []):
        props = feat.get("properties") or {}
        if props.get("layer") == "licence":
            continue
        geom = feat.get("geometry") or {}
        if geom.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        nm = normalize_name(props.get("prospect_name"))
        if not nm:
            continue
        score = 0
        if props.get("is_primary"):
            score += 4
        if props.get("geometry_role") == "outline_mapped":
            score += 2
        if props.get("stage") == "final":
            score += 1
        gs = props.get("geometry_source")
        method = str(gs.get("method") or "unknown") if isinstance(gs, dict) else "unknown"
        prev = by_name.get(nm)
        if prev is None or score > prev[0]:
            by_name[nm] = (score, geom, method)
    return {k: (v[1], v[2]) for k, v in by_name.items()}


def collect_licence_polygon(geo: dict[str, Any]) -> dict[str, Any] | None:
    for feat in (geo.get("features") or []):
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        if props.get("layer") == "licence" and geom.get("type") in ("Polygon", "MultiPolygon"):
            return geom
    return None


def analyze_llm_consistency(
    raw_json: dict[str, dict[str, Any]],
    raw_geo: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    dup_groups = find_duplicate_licence_groups(raw_json)
    pair_reports = []

    exact_count_matches = 0
    count_abs_diffs = []
    jaccards = []

    vol_rel_diffs = []
    vol_exact_1pct = 0
    vol_within_5pct = 0
    vol_within_10pct = 0
    vol_catastrophic_50pct = 0
    vol_outliers = []

    pg_abs_diffs = []
    pg_exact = 0
    pg_within_005 = 0
    pg_outliers = []

    dhi_obs_agree = 0
    dhi_obs_total = 0
    dhi_sup_agree = 0
    dhi_sup_total = 0

    period_agree = 0
    period_total = 0

    depth_abs_diffs = []
    depth_exact_10m = 0

    poly_ious = []
    poly_centroid_dists = []
    poly_area_pct_diffs = []
    poly_area_ratios = []
    poly_outliers = []

    dig_ious = []
    dig_centroid_dists = []
    dig_area_pct_diffs = []
    shp_ious = []
    shp_centroid_dists = []
    identical_poly_count = 0

    lic_ious = []
    lic_centroid_dists = []

    total_matched_prospects = 0
    total_union_prospects = 0

    for lic_id, stems in sorted(dup_groups.items()):
        s1, s2 = stems[0], stems[1]
        r1, r2 = raw_json[s1], raw_json[s2]
        g1, g2 = raw_geo[s1], raw_geo[s2]

        p1_list = [extract_prospect_summary(s1, r1, p) for p in (r1.get("prospects") or [])]
        p2_list = [extract_prospect_summary(s2, r2, p) for p in (r2.get("prospects") or [])]

        n1, n2 = len(p1_list), len(p2_list)
        if n1 == n2:
            exact_count_matches += 1
        count_abs_diffs.append(abs(n1 - n2))

        map1 = {p["norm_name"]: p for p in p1_list if p["norm_name"]}
        map2 = {p["norm_name"]: p for p in p2_list if p["norm_name"]}
        set1, set2 = set(map1.keys()), set(map2.keys())
        inter = sorted(set1 & set2)
        union = set1 | set2
        jacc = len(inter) / len(union) if union else 1.0
        jaccards.append(jacc)
        total_matched_prospects += len(inter)
        total_union_prospects += len(union)

        pair_vols = 0
        pair_pgs = 0
        pair_ious = []
        pair_cdists = []

        for nm in inter:
            a, b = map1[nm], map2[nm]
            if a["vol_mean_msmo3"] is not None and b["vol_mean_msmo3"] is not None:
                v1, v2 = a["vol_mean_msmo3"], b["vol_mean_msmo3"]
                avg = 0.5 * (v1 + v2)
                rdiff = abs(v1 - v2) / avg * 100.0 if avg > 0 else 0.0
                vol_rel_diffs.append(rdiff)
                pair_vols += 1
                if rdiff <= 1.0:
                    vol_exact_1pct += 1
                if rdiff <= 5.0:
                    vol_within_5pct += 1
                if rdiff <= 10.0:
                    vol_within_10pct += 1
                if rdiff > 50.0:
                    vol_catastrophic_50pct += 1
                    vol_outliers.append(
                        {
                            "licence_id": lic_id,
                            "name": a["name"],
                            "vol_run1": round(v1, 3),
                            "vol_run2": round(v2, 3),
                            "rel_diff_pct": round(rdiff, 1),
                        }
                    )

            if a["pg"] is not None and b["pg"] is not None:
                diff = abs(a["pg"] - b["pg"])
                pg_abs_diffs.append(diff)
                pair_pgs += 1
                if diff <= 0.001:
                    pg_exact += 1
                if diff <= 0.05:
                    pg_within_005 += 1
                if diff > 0.10:
                    pg_outliers.append(
                        {
                            "licence_id": lic_id,
                            "name": a["name"],
                            "pg_run1": round(a["pg"], 4),
                            "pg_run2": round(b["pg"], 4),
                            "abs_diff": round(diff, 4),
                        }
                    )

            if a["dhi_observed"] is not None and b["dhi_observed"] is not None:
                dhi_obs_total += 1
                if a["dhi_observed"] == b["dhi_observed"]:
                    dhi_obs_agree += 1

            if a["dhi_support"] is not None and b["dhi_support"] is not None:
                dhi_sup_total += 1
                if a["dhi_support"] == b["dhi_support"]:
                    dhi_sup_agree += 1

            if a["period"] != "Unknown" and b["period"] != "Unknown":
                period_total += 1
                if a["period"] == b["period"]:
                    period_agree += 1

            if a["crest_depth_m"] is not None and b["crest_depth_m"] is not None:
                dd = abs(a["crest_depth_m"] - b["crest_depth_m"])
                depth_abs_diffs.append(dd)
                if dd <= 10.0:
                    depth_exact_10m += 1

        polys1 = collect_primary_polygons(g1)
        polys2 = collect_primary_polygons(g2)
        poly_inter = sorted(set(polys1.keys()) & set(polys2.keys()))
        for nm in poly_inter:
            geom_a, meth_a = polys1[nm]
            geom_b, meth_b = polys2[nm]
            m = compute_polygon_pair_metrics(geom_a, geom_b)
            if m is None:
                continue
            is_ident = geom_a.get("coordinates") == geom_b.get("coordinates")
            if is_ident:
                identical_poly_count += 1
            poly_ious.append(m["iou"])
            poly_centroid_dists.append(m["centroid_dist_m"])
            poly_area_pct_diffs.append(m["area_pct_diff"])
            poly_area_ratios.append(m["area_ratio"])
            pair_ious.append(m["iou"])
            pair_cdists.append(m["centroid_dist_m"])
            if meth_a == "digitised_figure" and meth_b == "digitised_figure":
                dig_ious.append(m["iou"])
                dig_centroid_dists.append(m["centroid_dist_m"])
                dig_area_pct_diffs.append(m["area_pct_diff"])
            elif meth_a == "shapefile" and meth_b == "shapefile":
                shp_ious.append(m["iou"])
                shp_centroid_dists.append(m["centroid_dist_m"])
            if m["iou"] < 0.25:
                poly_outliers.append(
                    {
                        "licence_id": lic_id,
                        "name": nm,
                        "method_1": meth_a,
                        "method_2": meth_b,
                        "iou": round(m["iou"], 4),
                        "centroid_dist_m": round(m["centroid_dist_m"], 1),
                        "area1_km2": round(m["area1_km2"], 2),
                        "area2_km2": round(m["area2_km2"], 2),
                    }
                )

        lpoly1 = collect_licence_polygon(g1)
        lpoly2 = collect_licence_polygon(g2)
        lic_iou = None
        lic_cd = None
        if lpoly1 and lpoly2:
            lm = compute_polygon_pair_metrics(lpoly1, lpoly2)
            if lm:
                lic_iou = lm["iou"]
                lic_cd = lm["centroid_dist_m"]
                lic_ious.append(lic_iou)
                lic_centroid_dists.append(lic_cd)

        pair_reports.append(
            {
                "licence_id": lic_id,
                "stem1": s1,
                "stem2": s2,
                "page_count": (r1.get("document") or {}).get("page_count"),
                "n_prospects_1": n1,
                "n_prospects_2": n2,
                "matched_names": len(inter),
                "union_names": len(union),
                "name_jaccard": round(jacc, 4),
                "matched_vols": pair_vols,
                "matched_pgs": pair_pgs,
                "matched_polygons": len(pair_ious),
                "median_poly_iou": round(statistics.median(pair_ious), 4) if pair_ious else None,
                "median_centroid_dist_m": (
                    round(statistics.median(pair_cdists), 1) if pair_cdists else None
                ),
                "licence_boundary_iou": round(lic_iou, 4) if lic_iou is not None else None,
            }
        )

    def pct(num: int, den: int) -> float | None:
        return round(100.0 * num / den, 2) if den > 0 else None

    def quantile(vals: list[float], q: float) -> float | None:
        if not vals:
            return None
        s = sorted(vals)
        idx = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
        return s[idx]

    n_pairs = len(dup_groups)
    n_vol = len(vol_rel_diffs)
    n_pg = len(pg_abs_diffs)
    n_poly = len(poly_ious)
    n_depth = len(depth_abs_diffs)

    return {
        "n_duplicate_pairs": n_pairs,
        "prospect_count_agreement": {
            "exact_match_pairs": exact_count_matches,
            "exact_match_pct": pct(exact_count_matches, n_pairs),
            "mean_abs_count_diff": round(statistics.mean(count_abs_diffs), 2),
            "max_abs_count_diff": max(count_abs_diffs) if count_abs_diffs else 0,
        },
        "prospect_name_overlap": {
            "macro_mean_jaccard": round(statistics.mean(jaccards), 4),
            "macro_median_jaccard": round(statistics.median(jaccards), 4),
            "micro_jaccard": round(total_matched_prospects / total_union_prospects, 4),
            "total_matched_prospects": total_matched_prospects,
            "total_union_prospects": total_union_prospects,
        },
        "volume_agreement": {
            "n_matched_with_volume": n_vol,
            "exact_within_1pct_n": vol_exact_1pct,
            "exact_within_1pct_pct": pct(vol_exact_1pct, n_vol),
            "within_5pct_pct": pct(vol_within_5pct, n_vol),
            "within_10pct_pct": pct(vol_within_10pct, n_vol),
            "catastrophic_gt50pct_n": vol_catastrophic_50pct,
            "catastrophic_gt50pct_pct": pct(vol_catastrophic_50pct, n_vol),
            "median_rel_diff_pct": round(statistics.median(vol_rel_diffs), 3) if n_vol else None,
            "mean_rel_diff_pct": round(statistics.mean(vol_rel_diffs), 2) if n_vol else None,
            "p90_rel_diff_pct": round(quantile(vol_rel_diffs, 0.90), 2) if n_vol else None,
            "outliers": sorted(vol_outliers, key=lambda x: -x["rel_diff_pct"])[:15],
        },
        "pg_agreement": {
            "n_matched_with_pg": n_pg,
            "exact_match_n": pg_exact,
            "exact_match_pct": pct(pg_exact, n_pg),
            "within_5pp_pct": pct(pg_within_005, n_pg),
            "mae": round(statistics.mean(pg_abs_diffs), 4) if n_pg else None,
            "median_ae": round(statistics.median(pg_abs_diffs), 4) if n_pg else None,
            "max_ae": round(max(pg_abs_diffs), 4) if n_pg else None,
            "outliers": sorted(pg_outliers, key=lambda x: -x["abs_diff"])[:15],
        },
        "secondary_field_agreement": {
            "dhi_observed_n": dhi_obs_total,
            "dhi_observed_agree_pct": pct(dhi_obs_agree, dhi_obs_total),
            "dhi_support_n": dhi_sup_total,
            "dhi_support_agree_pct": pct(dhi_sup_agree, dhi_sup_total),
            "reservoir_period_n": period_total,
            "reservoir_period_agree_pct": pct(period_agree, period_total),
            "crest_depth_n": n_depth,
            "crest_depth_within_10m_pct": pct(depth_exact_10m, n_depth),
            "crest_depth_median_abs_diff_m": (
                round(statistics.median(depth_abs_diffs), 1) if n_depth else None
            ),
            "crest_depth_mean_abs_diff_m": (
                round(statistics.mean(depth_abs_diffs), 1) if n_depth else None
            ),
        },
        "geojson_polygon_consistency": {
            "n_matched_polygons": n_poly,
            "median_iou": round(statistics.median(poly_ious), 4) if n_poly else None,
            "mean_iou": round(statistics.mean(poly_ious), 4) if n_poly else None,
            "p10_iou": round(quantile(poly_ious, 0.10), 4) if n_poly else None,
            "p25_iou": round(quantile(poly_ious, 0.25), 4) if n_poly else None,
            "p75_iou": round(quantile(poly_ious, 0.75), 4) if n_poly else None,
            "p90_iou": round(quantile(poly_ious, 0.90), 4) if n_poly else None,
            "iou_ge_050_pct": pct(sum(1 for x in poly_ious if x >= 0.50), n_poly),
            "iou_ge_070_pct": pct(sum(1 for x in poly_ious if x >= 0.70), n_poly),
            "iou_ge_080_pct": pct(sum(1 for x in poly_ious if x >= 0.80), n_poly),
            "iou_lt_010_pct": pct(sum(1 for x in poly_ious if x < 0.10), n_poly),
            "zero_overlap_n": sum(1 for x in poly_ious if x == 0.0),
            "median_centroid_dist_m": (
                round(statistics.median(poly_centroid_dists), 1) if n_poly else None
            ),
            "mean_centroid_dist_m": (
                round(statistics.mean(poly_centroid_dists), 1) if n_poly else None
            ),
            "p90_centroid_dist_m": (
                round(quantile(poly_centroid_dists, 0.90), 1) if n_poly else None
            ),
            "max_centroid_dist_m": round(max(poly_centroid_dists), 1) if n_poly else None,
            "median_area_pct_diff": (
                round(statistics.median(poly_area_pct_diffs), 2) if n_poly else None
            ),
            "median_area_ratio": (
                round(statistics.median(poly_area_ratios), 4) if n_poly else None
            ),
            "licence_boundary_n": len(lic_ious),
            "licence_boundary_median_iou": (
                round(statistics.median(lic_ious), 4) if lic_ious else None
            ),
            "licence_boundary_median_centroid_dist_m": (
                round(statistics.median(lic_centroid_dists), 1) if lic_centroid_dists else None
            ),
            "byte_identical_polygons_n": identical_poly_count,
            "digitised_figure_only": {
                "n": len(dig_ious),
                "median_iou": round(statistics.median(dig_ious), 4) if dig_ious else None,
                "mean_iou": round(statistics.mean(dig_ious), 4) if dig_ious else None,
                "p10_iou": round(quantile(dig_ious, 0.10), 4) if dig_ious else None,
                "p25_iou": round(quantile(dig_ious, 0.25), 4) if dig_ious else None,
                "p75_iou": round(quantile(dig_ious, 0.75), 4) if dig_ious else None,
                "p90_iou": round(quantile(dig_ious, 0.90), 4) if dig_ious else None,
                "iou_ge_070_pct": pct(sum(1 for x in dig_ious if x >= 0.70), len(dig_ious)),
                "iou_ge_050_pct": pct(sum(1 for x in dig_ious if x >= 0.50), len(dig_ious)),
                "median_centroid_dist_m": (
                    round(statistics.median(dig_centroid_dists), 1) if dig_centroid_dists else None
                ),
                "mean_centroid_dist_m": (
                    round(statistics.mean(dig_centroid_dists), 1) if dig_centroid_dists else None
                ),
                "p90_centroid_dist_m": (
                    round(quantile(dig_centroid_dists, 0.90), 1) if dig_centroid_dists else None
                ),
                "median_area_pct_diff": (
                    round(statistics.median(dig_area_pct_diffs), 2) if dig_area_pct_diffs else None
                ),
            },
            "shapefile_only": {
                "n": len(shp_ious),
                "median_iou": round(statistics.median(shp_ious), 4) if shp_ious else None,
                "mean_iou": round(statistics.mean(shp_ious), 4) if shp_ious else None,
                "median_centroid_dist_m": (
                    round(statistics.median(shp_centroid_dists), 1) if shp_centroid_dists else None
                ),
            },
            "low_iou_outliers": sorted(poly_outliers, key=lambda x: x["iou"])[:20],
        },
        "per_pair_summary": pair_reports,
    }


def fmt_pct(val: float | None) -> str:
    if val is None:
        return "—"
    return f"{val * 100:.1f}%"


def fmt_num(val: float | None, dec: int = 1) -> str:
    if val is None:
        return "—"
    return f"{val:.{dec}f}"


def write_markdown_report(findings: dict[str, Any]) -> None:
    meta = findings["metadata"]
    dhi = findings["angle_a1_dhi_paradox"]
    plays = findings["angle_a2_plays_and_depth"]
    llm = findings["angle_b_llm_consistency"]

    lines = [
        "# Track 4: DHI Paradox, Play/Depth Sweet Spots & AI Extraction Consistency",
        "",
        "## Dataset & Linkage Summary",
        f"- Deduplicated licences: **{meta['n_licences_dedup']}** ({meta['n_prospects_dedup']} prospects)",
        f"- Prospect GeoJSON polygons linked: **{meta['spatial_join']['polygons_linked']}** covering **{meta['spatial_join']['prospects_with_polygon']}** prospects",
        f"- SODIR FactPages wildcat wells loaded: **{meta['spatial_join']['wildcat_wells_loaded']}**",
        f"- Drilled prospects: **{meta['spatial_join']['prospects_any_drilled']}** total "
        f"(report-recorded: **{meta['spatial_join']['prospects_report_drilled']}**, "
        f"FactPages spatial polygon hit: **{meta['spatial_join']['prospects_fp_spatial_drilled']}**, "
        f"post-relinquishment re-drills: **{meta['spatial_join']['prospects_post_redrilled']}** "
        f"with **{meta['spatial_join']['prospects_post_redrill_discovery']}** discoveries)",
        "",
        "---",
        "",
        "## (A1) The DHI Paradox",
        "",
        "### Overall Discovery Rate by DHI Category (Combined Report + FactPages Wildcats)",
        "| DHI Category | Prospects | Mean Pg | Drilled | Discoveries | Discovery Rate | Mean Pg (Drilled) | Report Disc Rate | FactPages Disc Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cat in ("positive_dhi", "observed_nonpositive_dhi", "negative_or_no_dhi", "assessed_unclear", "not_assessed"):
        s = dhi["overall_by_category"].get(cat)
        if not s:
            continue
        lines.append(
            f"| {cat} | {s['n_prospects']} | {fmt_pct(s['mean_pg'])} | {s['drilled_any']} | {s['disc_any']} | "
            f"**{fmt_pct(s['disc_rate_any'])}** | {fmt_pct(s['mean_pg_of_drilled'])} | "
            f"{fmt_pct(s['disc_rate_report'])} | {fmt_pct(s['disc_rate_fp'])} |"
        )

    lines += ["", "### Fisher Exact Tests (Overall DHI Contrasts)"]
    for c in dhi["contrasts"]:
        lines.append(
            f"- **{c['comparison']}**: {fmt_pct(c['g1_rate'])} ({c['g1_disc']}/{c['g1_drilled']}) vs "
            f"{fmt_pct(c['g2_rate'])} ({c['g2_disc']}/{c['g2_drilled']}), Fisher p = **{c['fisher_p']}**"
        )

    lines += [
        "",
        "### Basin Comparison: North Sea vs Norwegian Sea vs Barents Sea",
        "| Basin | Positive DHI Disc Rate (n) | Any DHI Observed Disc Rate (n) | No DHI Observed Disc Rate (n) | Fisher p (Pos vs No DHI) | Pos DHI Mean Pg (Drilled) | Pos DHI Gas-Only Share |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for basin in ("North Sea", "Norwegian Sea", "Barents Sea"):
        b = dhi["by_basin"][basin]
        p_s = b["positive_dhi"]
        o_s = b["any_dhi_observed"]
        n_s = b["no_dhi_observed"]
        cp = b["contrast_pos_vs_no_obs"]["fisher_p"]
        lines.append(
            f"| {basin} | **{fmt_pct(p_s['disc_rate_any'])}** ({p_s['disc_any']}/{p_s['drilled_any']}) | "
            f"{fmt_pct(o_s['disc_rate_any'])} ({o_s['disc_any']}/{o_s['drilled_any']}) | "
            f"{fmt_pct(n_s['disc_rate_any'])} ({n_s['disc_any']}/{n_s['drilled_any']}) | "
            f"{cp} | {fmt_pct(p_s['mean_pg_of_drilled'])} | {fmt_pct(p_s['gas_only_share_of_disc'])} |"
        )

    lines += [
        "",
        "### Discovery Rate by Specific DHI Type",
        "| DHI Type | All Prospects | All Drilled Disc Rate (n) | Positive-Support Drilled Disc Rate (n) | Mean Pg (All) |",
        "|---|---:|---:|---:|---:|",
    ]
    for dtype, vals in dhi["by_dhi_type"].items():
        a_s = vals["all_with_type"]
        p_s = vals["positive_with_type"]
        lines.append(
            f"| {dtype} | {a_s['n_prospects']} | {fmt_pct(a_s['disc_rate_any'])} ({a_s['disc_any']}/{a_s['drilled_any']}) | "
            f"**{fmt_pct(p_s['disc_rate_any'])}** ({p_s['disc_any']}/{p_s['drilled_any']}) | {fmt_pct(a_s['mean_pg'])} |"
        )

    up = dhi["pg_uplift_analysis"]
    lines += [
        "",
        f"### Operator Self-Granted DHI Pg Uplift (`pg` vs `pg_before_dhi`)",
        f"- Prospects reporting `pg_before_dhi`: **{up['n_with_pg_before_dhi']}**",
        f"- Mean Pg uplift: **+{fmt_pct(up['mean_pg_uplift'])}** (median **+{fmt_pct(up['median_pg_uplift'])}**)",
        f"- Drilled subset with explicit DHI uplift: **{up['drilled_with_pg_before_dhi']['disc_any']}/{up['drilled_with_pg_before_dhi']['drilled_any']}** "
        f"(**{fmt_pct(up['drilled_with_pg_before_dhi']['disc_rate_any'])}** discovery rate vs mean drilled Pg {fmt_pct(up['drilled_with_pg_before_dhi']['mean_pg_of_drilled'])})",
        "",
        "---",
        "",
        "## (A2) Play / Reservoir Age & Depth Sweet Spots",
        "",
        "### By Reservoir Geological Period",
        "| Period | Prospects | Mean Pg | Mean Vol (MSm3 oe) | Median Vol | Median Area (km2) | Median Depth (m) | Drilled | Disc Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for per, s in plays["by_period"].items():
        lines.append(
            f"| {per} | {s['n_prospects']} | {fmt_pct(s['mean_pg'])} | {fmt_num(s['mean_vol_msmo3'], 1)} | "
            f"{fmt_num(s['median_vol_msmo3'], 1)} | {fmt_num(s['median_area_km2'], 1)} | "
            f"{fmt_num(s['median_depth_m'], 0)} | {s['drilled_any']} | **{fmt_pct(s['disc_rate_any'])}** |"
        )

    lines += [
        "",
        "### By Crest Depth Bin",
        "| Depth Bin | Prospects | Mean Pg | Mean Vol (MSm3 oe) | Median Vol | Median Area (km2) | Drilled | Discoveries | Disc Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for db, s in plays["by_depth_bin"].items():
        lines.append(
            f"| {db} | {s['n_prospects']} | {fmt_pct(s['mean_pg'])} | {fmt_num(s['mean_vol_msmo3'], 1)} | "
            f"{fmt_num(s['median_vol_msmo3'], 1)} | {fmt_num(s['median_area_km2'], 1)} | "
            f"{s['drilled_any']} | {s['disc_any']} | **{fmt_pct(s['disc_rate_any'])}** |"
        )

    sp = plays["special_plays"]
    lines += [
        "",
        "### Special Plays & Anomalies",
        f"- **HPHT-flagged prospects**: n={sp['hpht_flagged']['n_prospects']}, Mean Pg={fmt_pct(sp['hpht_flagged']['mean_pg'])}, "
        f"Mean Vol={fmt_num(sp['hpht_flagged']['mean_vol_msmo3'], 1)} MSm3 oe, Drilled={sp['hpht_flagged']['drilled_any']}, "
        f"Disc Rate=**{fmt_pct(sp['hpht_flagged']['disc_rate_any'])}**",
        f"- **Deep (>=4000 m)**: n={sp['deep_ge4000m']['n_prospects']}, Mean Pg={fmt_pct(sp['deep_ge4000m']['mean_pg'])}, "
        f"Mean Vol={fmt_num(sp['deep_ge4000m']['mean_vol_msmo3'], 1)} MSm3 oe, Drilled={sp['deep_ge4000m']['drilled_any']}, "
        f"Disc Rate=**{fmt_pct(sp['deep_ge4000m']['disc_rate_any'])}**",
        f"- **Shallow Barents (<1500 m)**: n={sp['shallow_barents_lt1500m']['n_prospects']}, Mean Pg={fmt_pct(sp['shallow_barents_lt1500m']['mean_pg'])}, "
        f"Mean Vol={fmt_num(sp['shallow_barents_lt1500m']['mean_vol_msmo3'], 1)} MSm3 oe, Drilled={sp['shallow_barents_lt1500m']['drilled_any']}, "
        f"Disc Rate=**{fmt_pct(sp['shallow_barents_lt1500m']['disc_rate_any'])}**",
        f"- **Basement play**: n={sp['basement_all']['n_prospects']}, Mean Pg={fmt_pct(sp['basement_all']['mean_pg'])}, "
        f"Mean Vol={fmt_num(sp['basement_all']['mean_vol_msmo3'], 1)} MSm3 oe, Drilled={sp['basement_all']['drilled_any']}, "
        f"Disc Rate=**{fmt_pct(sp['basement_all']['disc_rate_any'])}**",
        "",
        "---",
        "",
        "## (B) The Accidental Natural Experiment in AI Geoscience Extraction (18 Duplicate PDF Pairs)",
        "",
        f"- **Exact prospect count match**: **{llm['prospect_count_agreement']['exact_match_pairs']}/{llm['n_duplicate_pairs']}** "
        f"(**{llm['prospect_count_agreement']['exact_match_pct']}%**), mean abs diff = {llm['prospect_count_agreement']['mean_abs_count_diff']}",
        f"- **Prospect name Jaccard overlap**: macro mean **{llm['prospect_name_overlap']['macro_mean_jaccard']:.3f}**, "
        f"median **{llm['prospect_name_overlap']['macro_median_jaccard']:.3f}**, "
        f"micro **{llm['prospect_name_overlap']['micro_jaccard']:.3f}** "
        f"({llm['prospect_name_overlap']['total_matched_prospects']}/{llm['prospect_name_overlap']['total_union_prospects']} union prospects)",
        f"- **Matched Volume agreement** (n={llm['volume_agreement']['n_matched_with_volume']}): "
        f"exact (<=1% diff) = **{llm['volume_agreement']['exact_within_1pct_pct']}%**, "
        f"within 5% = **{llm['volume_agreement']['within_5pct_pct']}%**, "
        f"median % diff = **{llm['volume_agreement']['median_rel_diff_pct']}%**, "
        f"mean % diff = **{llm['volume_agreement']['mean_rel_diff_pct']}%**, "
        f"catastrophic (>50% diff) = **{llm['volume_agreement']['catastrophic_gt50pct_n']}** ({llm['volume_agreement']['catastrophic_gt50pct_pct']}%)",
        f"- **Matched Pg agreement** (n={llm['pg_agreement']['n_matched_with_pg']}): "
        f"exact match = **{llm['pg_agreement']['exact_match_pct']}%**, "
        f"within 5 pp = **{llm['pg_agreement']['within_5pp_pct']}%**, "
        f"MAE = **{llm['pg_agreement']['mae']:.4f}** ({llm['pg_agreement']['mae']*100:.2f} pp), "
        f"max error = **{llm['pg_agreement']['max_ae']:.4f}**",
        f"- **Secondary fields**: DHI observed agreement = **{llm['secondary_field_agreement']['dhi_observed_agree_pct']}%** "
        f"(n={llm['secondary_field_agreement']['dhi_observed_n']}), "
        f"DHI support agreement = **{llm['secondary_field_agreement']['dhi_support_agree_pct']}%** "
        f"(n={llm['secondary_field_agreement']['dhi_support_n']}), "
        f"Reservoir period agreement = **{llm['secondary_field_agreement']['reservoir_period_agree_pct']}%** "
        f"(n={llm['secondary_field_agreement']['reservoir_period_n']}), "
        f"Crest depth within 10 m = **{llm['secondary_field_agreement']['crest_depth_within_10m_pct']}%** "
        f"(n={llm['secondary_field_agreement']['crest_depth_n']}, median abs diff = {llm['secondary_field_agreement']['crest_depth_median_abs_diff_m']} m)",
        f"- **GeoJSON Polygon Digitization Consistency** (n={llm['geojson_polygon_consistency']['n_matched_polygons']} matched prospect polygons): "
        f"median IoU = **{llm['geojson_polygon_consistency']['median_iou']:.3f}**, "
        f"mean IoU = **{llm['geojson_polygon_consistency']['mean_iou']:.3f}**, "
        f"IoU >= 0.70 = **{llm['geojson_polygon_consistency']['iou_ge_070_pct']}%**, "
        f"IoU >= 0.50 = **{llm['geojson_polygon_consistency']['iou_ge_050_pct']}%**, "
        f"IoU < 0.10 = **{llm['geojson_polygon_consistency']['iou_lt_010_pct']}%** (zero overlap: {llm['geojson_polygon_consistency']['zero_overlap_n']})",
        f"- **Polygon Centroid Shift (All)**: median **{llm['geojson_polygon_consistency']['median_centroid_dist_m']} m**, "
        f"mean **{llm['geojson_polygon_consistency']['mean_centroid_dist_m']} m**, "
        f"P90 **{llm['geojson_polygon_consistency']['p90_centroid_dist_m']} m**, "
        f"median area diff = **{llm['geojson_polygon_consistency']['median_area_pct_diff']}%** "
        f"(byte-identical polygons: {llm['geojson_polygon_consistency']['byte_identical_polygons_n']}/{llm['geojson_polygon_consistency']['n_matched_polygons']})",
        f"- **Independently Digitized Map Figures Only (`digitised_figure` vs `digitised_figure`, n={llm['geojson_polygon_consistency']['digitised_figure_only']['n']})**: "
        f"median IoU = **{llm['geojson_polygon_consistency']['digitised_figure_only']['median_iou']:.3f}**, "
        f"mean IoU = **{llm['geojson_polygon_consistency']['digitised_figure_only']['mean_iou']:.3f}**, "
        f"IoU >= 0.70 = **{llm['geojson_polygon_consistency']['digitised_figure_only']['iou_ge_070_pct']}%**, "
        f"IoU >= 0.50 = **{llm['geojson_polygon_consistency']['digitised_figure_only']['iou_ge_050_pct']}%**, "
        f"median centroid shift = **{llm['geojson_polygon_consistency']['digitised_figure_only']['median_centroid_dist_m']} m** "
        f"(mean {llm['geojson_polygon_consistency']['digitised_figure_only']['mean_centroid_dist_m']} m, "
        f"P90 {llm['geojson_polygon_consistency']['digitised_figure_only']['p90_centroid_dist_m']} m), "
        f"median area diff = **{llm['geojson_polygon_consistency']['digitised_figure_only']['median_area_pct_diff']}%**",
        f"- **Companion Shapefile Only (`shapefile` vs `shapefile`, n={llm['geojson_polygon_consistency']['shapefile_only']['n']})**: "
        f"median IoU = **{llm['geojson_polygon_consistency']['shapefile_only']['median_iou']}**, "
        f"mean IoU = **{llm['geojson_polygon_consistency']['shapefile_only']['mean_iou']}**, "
        f"median centroid shift = **{llm['geojson_polygon_consistency']['shapefile_only']['median_centroid_dist_m']} m**",
        f"- **Licence Boundary Baseline** (n={llm['geojson_polygon_consistency']['licence_boundary_n']}): "
        f"median IoU = **{llm['geojson_polygon_consistency']['licence_boundary_median_iou']}**, "
        f"median centroid dist = **{llm['geojson_polygon_consistency']['licence_boundary_median_centroid_dist_m']} m**",
        "",
        "### Per-Pair Summary (18 Duplicate Multi-Licence PDFs)",
        "| Licence | Pages | N1 | N2 | Matched | Jaccard | Matched Polys | Median IoU | Median Centroid Dist (m) | Licence IoU |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for pr in llm["per_pair_summary"]:
        lines.append(
            f"| {pr['licence_id']} | {pr['page_count']} | {pr['n_prospects_1']} | {pr['n_prospects_2']} | "
            f"{pr['matched_names']} | {pr['name_jaccard']:.3f} | {pr['matched_polygons']} | "
            f"{fmt_num(pr['median_poly_iou'], 3)} | {fmt_num(pr['median_centroid_dist_m'], 0)} | "
            f"{fmt_num(pr['licence_boundary_iou'], 3)} |"
        )

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_json, raw_geo = load_raw_records()
    kept_json, kept_geo, dropped = deduplicate_records(raw_json, raw_geo)
    wells_df = pl.read_parquet(DEFAULT_FACTPAGES_WELLS)

    prospects: list[dict[str, Any]] = []
    for stem, rec in kept_json.items():
        for p in (rec.get("prospects") or []):
            prospects.append(extract_prospect_summary(stem, rec, p))

    spatial_meta = attach_factpages_wells(prospects, kept_geo, wells_df)
    dhi_res = analyze_dhi(prospects)
    plays_res = analyze_plays_and_depth(prospects)
    llm_res = analyze_llm_consistency(raw_json, raw_geo)

    findings = {
        "metadata": {
            "n_licences_raw": len(raw_json),
            "n_licences_dedup": len(kept_json),
            "n_dropped_duplicates": len(dropped),
            "n_prospects_dedup": len(prospects),
            "spatial_join": spatial_meta,
        },
        "angle_a1_dhi_paradox": dhi_res,
        "angle_a2_plays_and_depth": plays_res,
        "angle_b_llm_consistency": llm_res,
    }

    OUT_JSON.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    write_markdown_report(findings)
    print("Wrote", OUT_JSON, "and", OUT_MD)


if __name__ == "__main__":
    main()
