import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import polars as pl

sys.path.insert(0, r"C:\Users\philip\Documents\ncs-relinquished-atlas\src")
from loader import (
    DEFAULT_FACTPAGES_WELLS,
    deduplicate_records,
    load_raw_records,
    safe_canonical_volume_msmo3,
)

OUT_DIR = Path(r"C:\Users\philip\Documents\ncs-relinquished-atlas\analyses")

DISCOVERY_RESULTS = {
    "discovery_oil",
    "discovery_gas",
    "discovery_oil_gas",
    "discovery_non_commercial",
    "technical_discovery",
}
COMMERCIAL_DISCOVERY_RESULTS = {
    "discovery_oil",
    "discovery_gas",
    "discovery_oil_gas",
}
DRY_RESULTS = {
    "dry",
    "dry_with_shows",
    "dry_no_shows",
    "water_wet_reservoir",
    "no_reservoir",
}
FP_DISCOVERY_CONTENTS = {
    "OIL",
    "GAS",
    "OIL/GAS",
    "GAS/CONDENSATE",
    "OIL/GAS/CONDENSATE",
    "CONDENSATE",
    "WATER/GAS",
}
FP_DRY_CONTENTS = {
    "DRY",
    "SHOWS",
    "OIL SHOWS",
    "GAS SHOWS",
    "OIL/GAS SHOWS",
    "WATER",
}
FP_EXCLUDE_STATUS = {
    "WILL NEVER BE DRILLED",
    "JUNKED",
    "DRILLING",
}

PRE_DRILL_STAGE_ORDER = [
    "drill_or_drop",
    "intermediate",
    "application",
    "award",
    "prior_licence",
]

POST_WELL_KEYWORDS = (
    "post-well",
    "post well",
    "post-drill",
    "post drill",
    "after well",
    "after the ",
    "remaining",
    "updip",
    "discovery: all probabilities",
)

FAILURE_TO_FACTOR = {
    "reservoir_quality": "reservoir",
    "reservoir_absent": "reservoir",
    "reservoir_absent_at_location": "reservoir",
    "migration": "charge",
    "charge": "charge",
    "source_absent": "charge",
    "timing": "charge",
    "phase": "charge",
    "top_seal": "retention",
    "fault_seal": "retention",
    "biodegradation": "retention",
    "trap": "trap",
}

ELEMENT_TO_FACTOR = {
    "reservoir": "reservoir",
    "reservoir_presence": "reservoir",
    "reservoir_quality": "reservoir",
    "reservoir_producibility": "reservoir",
    "trap": "trap",
    "trap_geometry": "trap",
    "trap_seal": "retention",
    "seal": "retention",
    "top_seal": "retention",
    "lateral_fault_seal": "retention",
    "retention": "retention",
    "charge": "charge",
    "migration": "charge",
    "source_presence": "charge",
    "source_migration": "charge",
    "source_maturity": "charge",
    "timing": "charge",
    "hc_phase": "charge",
}

CALIBRATION_BINS = [
    ("<15%", 0.0, 0.15),
    ("15-25%", 0.15, 0.25),
    ("25-35%", 0.25, 0.35),
    ("35-50%", 0.35, 0.50),
    ("50%+", 0.50, 1.01),
]


def normalize_operator(raw: str | None) -> str:
    if not raw:
        return "Unknown"
    s = raw.strip().lower()
    if any(k in s for k in ("equinor", "statoil", "norsk hydro")):
        return "Equinor"
    if any(k in s for k in ("aker bp", "det norske", "bp norge")):
        return "Aker BP"
    if "lundin" in s:
        return "Lundin"
    if any(k in s for k in ("vår energi", "var energi", "eni norge", "point resources")):
        return "Vår Energi"
    if any(k in s for k in ("wintershall", "dea norge")):
        return "Wintershall Dea"
    if "conocophillips" in s:
        return "ConocoPhillips"
    if any(k in s for k in ("shell", "bg norge")):
        return "Shell"
    if "omv" in s:
        return "OMV"
    if any(k in s for k in ("dno", "faroe")):
        return "DNO"
    if any(k in s for k in ("total", "maersk")):
        return "TotalEnergies"
    if any(k in s for k in ("spirit", "centrica", "bayerngas")):
        return "Spirit / Centrica"
    if any(k in s for k in ("neptune", "gdf suez", "engie")):
        return "Neptune / ENGIE"
    if "okea" in s:
        return "OKEA"
    if any(k in s for k in ("repsol", "talisman")):
        return "Repsol"
    if "tullow" in s:
        return "Tullow"
    if "wellesley" in s:
        return "Wellesley"
    if any(k in s for k in ("suncor", "petro-canada")):
        return "Suncor"
    if "edison" in s:
        return "Edison"
    if "vng" in s:
        return "VNG"
    if "mol " in s or s == "mol":
        return "MOL"
    if any(k in s for k in ("pgnig", "orlen")):
        return "PGNiG / ORLEN"
    if "e.on" in s:
        return "E.ON"
    if "premier" in s:
        return "Premier Oil"
    if "sval" in s:
        return "Sval Energi"
    if "harbour" in s:
        return "Harbour Energy"
    return "Other"


def extract_year(value: Any) -> int | None:
    if value is None:
        return None
    m = re.search(r"(19\d{2}|20\d{2})", str(value))
    return int(m.group(1)) if m else None


def get_report_year(rec: dict[str, Any]) -> int | None:
    doc = rec.get("document") or {}
    lic = rec.get("licence") or {}
    for val in (doc.get("date"), lic.get("relinquishment_date")):
        y = extract_year(val)
        if y is not None:
            return y
    return None


def get_decade(year: int | None) -> str | None:
    if year is None:
        return None
    if 2000 <= year <= 2009:
        return "2000s"
    if 2010 <= year <= 2019:
        return "2010s"
    if 2020 <= year <= 2029:
        return "2020s"
    return None


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def point_in_polygon_coords(x: float, y: float, poly_coords: list[list[list[float]]]) -> bool:
    if not poly_coords:
        return False
    if not point_in_ring(x, y, poly_coords[0]):
        return False
    for hole in poly_coords[1:]:
        if point_in_ring(x, y, hole):
            return False
    return True


def point_in_geom(x: float, y: float, geom: dict[str, Any]) -> bool:
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
    if gtype == "Polygon":
        return point_in_polygon_coords(x, y, coords)
    if gtype == "MultiPolygon":
        return any(point_in_polygon_coords(x, y, poly) for poly in coords)
    return False


def geom_bbox(geom: dict[str, Any]) -> tuple[float, float, float, float] | None:
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
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
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def two_sided_normal_p(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2.0))


def is_valid_prob(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 0.0 <= float(v) <= 1.0


def get_assessment_pg(a: dict[str, Any]) -> float | None:
    r = a.get("risk") or {}
    pg = r.get("pg")
    return float(pg) if is_valid_prob(pg) else None


def get_assessment_factors(a: dict[str, Any]) -> dict[str, float]:
    r = a.get("risk") or {}
    out: dict[str, float] = {}
    for k, label in (
        ("p_reservoir", "reservoir"),
        ("p_trap", "trap"),
        ("p_charge", "charge"),
        ("p_retention", "retention"),
    ):
        v = r.get(k)
        if is_valid_prob(v):
            out[label] = float(v)
    return out


def is_already_discovery_assessment(a: dict[str, Any]) -> bool:
    pg = get_assessment_pg(a)
    if pg is not None and (pg >= 0.99 or pg <= 0.0):
        return True
    if str(a.get("classification_at_stage") or "").lower() == "discovery":
        return True
    return False


def looks_post_well(a: dict[str, Any], drill_year: int | None) -> bool:
    if a.get("stage") == "post_well":
        return True
    if is_already_discovery_assessment(a):
        return True
    text = f"{a.get('label') or ''} {(a.get('risk') or {}).get('summary') or ''}".lower()
    if any(kw in text for kw in POST_WELL_KEYWORDS):
        return True
    ay = extract_year(a.get("assessment_year") or a.get("date"))
    if ay is not None and drill_year is not None and ay > drill_year:
        return True
    return False


def pick_pre_drill_assessment(
    prospect: dict[str, Any],
    drill_year: int | None,
    allow_vetted_final: bool = False,
    exclude_existing_discoveries: bool = True,
) -> dict[str, Any] | None:
    assessments = prospect.get("assessments") or []
    by_stage: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in assessments:
        if get_assessment_pg(a) is not None:
            if exclude_existing_discoveries and is_already_discovery_assessment(a):
                continue
            by_stage[str(a.get("stage") or "unknown")].append(a)
    for st in PRE_DRILL_STAGE_ORDER:
        if by_stage.get(st):
            return by_stage[st][-1]
    if allow_vetted_final:
        for a in by_stage.get("final", []):
            if not looks_post_well(a, drill_year):
                return a
    return None


def pick_representative_assessment(prospect: dict[str, Any]) -> dict[str, Any] | None:
    assessments = [a for a in (prospect.get("assessments") or []) if get_assessment_pg(a) is not None]
    if not assessments:
        return None
    is_drilled = bool(prospect.get("drilling")) or prospect.get("status_at_report") in (
        "drilled_dry",
        "drilled_discovery",
        "discovery_marginal",
    )
    if is_drilled:
        drill_years = [extract_year(d.get("year")) for d in (prospect.get("drilling") or []) if isinstance(d, dict)]
        drill_year = min([y for y in drill_years if y is not None], default=None)
        pre = pick_pre_drill_assessment(
            prospect, drill_year, allow_vetted_final=True, exclude_existing_discoveries=True
        )
        if pre is not None:
            return pre
    for st in ("final", "drill_or_drop", "intermediate", "application", "award", "prior_licence"):
        cands = [a for a in assessments if a.get("stage") == st and not is_already_discovery_assessment(a)]
        if cands:
            return cands[-1]
    return None


def classify_drilling_outcome(
    prospect: dict[str, Any],
    fp_by_npdid: dict[int, dict[str, Any]],
    fp_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    drilling = [d for d in (prospect.get("drilling") or []) if isinstance(d, dict)]
    status = prospect.get("status_at_report")
    if not drilling and status not in ("drilled_dry", "drilled_discovery", "discovery_marginal"):
        return None

    results = [str(d.get("result")) for d in drilling if d.get("result") is not None]
    years = [extract_year(d.get("year")) for d in drilling]
    drill_year = min([y for y in years if y is not None], default=None)
    well_names = [str(d.get("well_name")) for d in drilling if d.get("well_name")]
    npdids = [int(d["npdid"]) for d in drilling if isinstance(d.get("npdid"), int)]

    outcome: str | None = None
    is_commercial = False
    source = "json_drilling"

    if any(r in DISCOVERY_RESULTS for r in results):
        outcome = "discovery"
        is_commercial = any(r in COMMERCIAL_DISCOVERY_RESULTS for r in results)
    elif any(r in DRY_RESULTS for r in results):
        outcome = "dry"
    else:
        for npdid in npdids:
            fp = fp_by_npdid.get(npdid)
            if fp:
                c = fp["wlbContent"]
                if c in FP_DISCOVERY_CONTENTS:
                    outcome = "discovery"
                    is_commercial = True
                    source = "factpages_npdid"
                    break
                if c in FP_DRY_CONTENTS:
                    outcome = "dry"
                    source = "factpages_npdid"
                    break
        if outcome is None:
            for wn in well_names:
                fp = fp_by_name.get(wn.strip().upper())
                if fp:
                    c = fp["wlbContent"]
                    if c in FP_DISCOVERY_CONTENTS:
                        outcome = "discovery"
                        is_commercial = True
                        source = "factpages_name"
                        break
                    if c in FP_DRY_CONTENTS:
                        outcome = "dry"
                        source = "factpages_name"
                        break
        if outcome is None:
            if status in ("drilled_discovery", "discovery_marginal"):
                outcome = "discovery"
                is_commercial = status == "drilled_discovery"
                source = "status_at_report"
            elif status == "drilled_dry":
                outcome = "dry"
                source = "status_at_report"

    if outcome is None:
        return None

    failure_reasons: list[str] = []
    for d in drilling:
        fr = d.get("failure_reason")
        if isinstance(fr, list):
            failure_reasons.extend(str(x) for x in fr if x)
        elif fr:
            failure_reasons.append(str(fr))
        if d.get("result") == "no_reservoir" and "reservoir_absent" not in failure_reasons:
            failure_reasons.append("reservoir_absent")

    return {
        "outcome": outcome,
        "is_commercial": is_commercial,
        "drill_year": drill_year,
        "well_names": well_names,
        "npdids": npdids,
        "results": results,
        "failure_reasons": failure_reasons,
        "source": source,
    }


def compute_calibration_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    pgs = [r["pg"] for r in rows]
    ys = [1 if r["outcome"] == "discovery" else 0 for r in rows]
    mean_pg = sum(pgs) / n
    disc = sum(ys)
    actual_rate = disc / n
    brier = sum((p - y) ** 2 for p, y in zip(pgs, ys)) / n
    var_sum = sum(p * (1.0 - p) for p in pgs)
    z_stat = (disc - sum(pgs)) / math.sqrt(var_sum) if var_sum > 0 else 0.0
    p_val = two_sided_normal_p(z_stat)
    ci_lo, ci_hi = wilson_ci(disc, n)

    bins_out = []
    ece = 0.0
    for label, lo, hi in CALIBRATION_BINS:
        sub = [r for r in rows if lo <= r["pg"] < hi]
        bn = len(sub)
        if bn == 0:
            bins_out.append({"bin": label, "n": 0})
            continue
        b_pg = sum(r["pg"] for r in sub) / bn
        b_disc = sum(1 for r in sub if r["outcome"] == "discovery")
        b_rate = b_disc / bn
        b_lo, b_hi = wilson_ci(b_disc, bn)
        ece += (bn / n) * abs(b_rate - b_pg)
        bins_out.append(
            {
                "bin": label,
                "n": bn,
                "mean_pg": round(b_pg, 4),
                "discoveries": b_disc,
                "actual_rate": round(b_rate, 4),
                "gap_pp": round((b_rate - b_pg) * 100.0, 2),
                "ci_95": [round(b_lo, 4), round(b_hi, 4)],
            }
        )

    return {
        "n": n,
        "discoveries": disc,
        "mean_predicted_pg": round(mean_pg, 4),
        "actual_discovery_rate": round(actual_rate, 4),
        "gap_pp": round((actual_rate - mean_pg) * 100.0, 2),
        "actual_ci_95": [round(ci_lo, 4), round(ci_hi, 4)],
        "brier_score": round(brier, 4),
        "ece": round(ece, 4),
        "z_stat": round(z_stat, 3),
        "p_value": round(p_val, 6),
        "bins": bins_out,
    }


def extract_p10_p90_ratio(assessment: dict[str, Any]) -> float | None:
    ratios: list[float] = []
    for vol in assessment.get("volumes") or []:
        if not isinstance(vol, dict):
            continue
        if str(vol.get("risking") or "").lower() not in ("unrisked", ""):
            continue
        p10 = safe_canonical_volume_msmo3(vol, "p10")
        p90 = safe_canonical_volume_msmo3(vol, "p90")
        if p10 is not None and p90 is not None and p10 > 0 and p90 > 0:
            hi = max(p10, p90)
            lo = min(p10, p90)
            r = hi / lo
            if 1.0 <= r <= 1000.0:
                ratios.append(r)
    if not ratios:
        return None
    return statistics.median(ratios)


def main() -> None:
    raw_j, raw_g = load_raw_records()
    kept_j, kept_g, dropped = deduplicate_records(raw_j, raw_g)

    df_w = pl.read_parquet(DEFAULT_FACTPAGES_WELLS)
    fp_by_npdid: dict[int, dict[str, Any]] = {}
    fp_by_name: dict[str, dict[str, Any]] = {}
    fp_wildcats: list[dict[str, Any]] = []

    for row in df_w.iter_rows(named=True):
        npdid = row.get("wlbNpdidWellbore")
        wname = row.get("wlbWellboreName")
        if npdid is not None:
            fp_by_npdid[int(npdid)] = row
        if wname:
            fp_by_name[str(wname).strip().upper()] = row
        status = str(row.get("wlbStatus") or "").upper()
        content = str(row.get("wlbContent") or "").upper()
        purpose = str(row.get("wlbPurpose") or "").upper()
        lon = row.get("wlbEwDecDeg")
        lat = row.get("wlbNsDecDeg")
        if (
            purpose == "WILDCAT"
            and status not in FP_EXCLUDE_STATUS
            and (content in FP_DISCOVERY_CONTENTS or content in FP_DRY_CONTENTS)
            and lon is not None
            and lat is not None
        ):
            fp_wildcats.append(
                {
                    "well_name": str(wname),
                    "npdid": int(npdid) if npdid is not None else None,
                    "lon": float(lon),
                    "lat": float(lat),
                    "entry_year": int(row["wlbEntryYear"]) if row.get("wlbEntryYear") is not None else None,
                    "content": content,
                    "outcome": "discovery" if content in FP_DISCOVERY_CONTENTS else "dry",
                    "operator": str(row.get("wlbDrillingOperator") or ""),
                    "licence": str(row.get("wlbProductionLicence") or ""),
                }
            )

    prospect_geoms: dict[tuple[str, str], list[tuple[tuple[float, float, float, float], dict[str, Any], float | None, str]]] = defaultdict(list)
    for stem, g in kept_g.items():
        for feat in g.get("features") or []:
            props = feat.get("properties") or {}
            layer = str(props.get("layer") or "")
            if layer not in ("prospect", "lead", "segment", "discovery", "idea"):
                continue
            geom = feat.get("geometry") or {}
            if geom.get("type") not in ("Polygon", "MultiPolygon"):
                continue
            pid = (((props.get("_derived") or {}).get("links") or {}).get("prospect") or {}).get("prospect_id")
            if not pid:
                pid = props.get("prospect_uid")
            if not pid:
                continue
            bb = geom_bbox(geom)
            if bb is not None:
                akm2 = props.get("area_km2_geometry")
                area_val = float(akm2) if isinstance(akm2, (int, float)) else None
                prospect_geoms[(stem, str(pid))].append((bb, geom, area_val, layer))

    strict_in_licence_rows: list[dict[str, Any]] = []
    full_in_licence_rows: list[dict[str, Any]] = []
    post_relinq_rows: list[dict[str, Any]] = []
    post_relinq_tight_rows: list[dict[str, Any]] = []
    stage_evolution_pairs: list[dict[str, Any]] = []
    dry_hole_records: list[dict[str, Any]] = []

    atlas_lowest_factor = Counter()
    atlas_high_risk_elements = Counter()
    all_prospect_profiles: list[dict[str, Any]] = []
    pg_math_records: list[dict[str, Any]] = []

    total_prospects = 0
    in_licence_drilled_total = 0
    in_licence_drilled_outcomes = Counter()
    spatial_post_matched_total = 0

    for stem, rec in kept_j.items():
        lic = rec.get("licence") or {}
        doc = rec.get("document") or {}
        licence_id = str(lic.get("licence_id") or stem)
        area = str(lic.get("area") or "Unknown")
        raw_op = str(lic.get("operator") or doc.get("author_company") or "")
        op = normalize_operator(raw_op)
        rep_year = get_report_year(rec)
        decade = get_decade(rep_year)

        for p in rec.get("prospects") or []:
            total_prospects += 1
            pid = str(p.get("prospect_id") or p.get("name") or total_prospects)
            pname = str(p.get("name") or pid)

            drill_info = classify_drilling_outcome(p, fp_by_npdid, fp_by_name)
            if drill_info is not None:
                in_licence_drilled_total += 1
                in_licence_drilled_outcomes[drill_info["outcome"]] += 1
                pre_strict = pick_pre_drill_assessment(
                    p, drill_info["drill_year"], allow_vetted_final=False, exclude_existing_discoveries=True
                )
                pre_full = pick_pre_drill_assessment(
                    p, drill_info["drill_year"], allow_vetted_final=True, exclude_existing_discoveries=True
                )

                if pre_strict is not None:
                    pg = get_assessment_pg(pre_strict)
                    strict_in_licence_rows.append(
                        {
                            "licence_id": licence_id,
                            "prospect_name": pname,
                            "operator": op,
                            "area": area,
                            "decade": decade,
                            "stage": pre_strict.get("stage"),
                            "pg": pg,
                            "outcome": drill_info["outcome"],
                            "is_commercial": drill_info["is_commercial"],
                            "source": "in_licence_strict",
                        }
                    )
                if pre_full is not None:
                    pg = get_assessment_pg(pre_full)
                    full_in_licence_rows.append(
                        {
                            "licence_id": licence_id,
                            "prospect_name": pname,
                            "operator": op,
                            "area": area,
                            "decade": decade,
                            "stage": pre_full.get("stage"),
                            "pg": pg,
                            "outcome": drill_info["outcome"],
                            "is_commercial": drill_info["is_commercial"],
                            "source": "in_licence_full",
                        }
                    )

                by_st = {
                    str(a.get("stage")): get_assessment_pg(a)
                    for a in (p.get("assessments") or [])
                    if get_assessment_pg(a) is not None and not is_already_discovery_assessment(a)
                }
                if "application" in by_st and "drill_or_drop" in by_st:
                    stage_evolution_pairs.append(
                        {
                            "licence_id": licence_id,
                            "prospect_name": pname,
                            "pg_application": by_st["application"],
                            "pg_dod": by_st["drill_or_drop"],
                            "outcome": drill_info["outcome"],
                        }
                    )

                if drill_info["outcome"] == "dry":
                    pre_for_factors = pre_full
                    if pre_for_factors is None:
                        for a in p.get("assessments") or []:
                            if get_assessment_factors(a) and not looks_post_well(a, drill_info["drill_year"]):
                                pre_for_factors = a
                                break
                    factors = get_assessment_factors(pre_for_factors) if pre_for_factors else {}
                    qual_fears = set()
                    for a in p.get("assessments") or []:
                        if a.get("stage") == "post_well":
                            continue
                        for el in (a.get("risk") or {}).get("elements") or []:
                            if isinstance(el, dict) and el.get("rating") in ("high", "very_high"):
                                mapped = ELEMENT_TO_FACTOR.get(str(el.get("element") or ""))
                                if mapped:
                                    qual_fears.add(mapped)
                    actual_factors = sorted(
                        {
                            FAILURE_TO_FACTOR[fr]
                            for fr in drill_info["failure_reasons"]
                            if fr in FAILURE_TO_FACTOR
                        }
                    )
                    dry_hole_records.append(
                        {
                            "licence_id": licence_id,
                            "prospect_name": pname,
                            "operator": op,
                            "area": area,
                            "pg": get_assessment_pg(pre_for_factors) if pre_for_factors else None,
                            "factors": factors,
                            "qual_fears": sorted(qual_fears),
                            "raw_failure_reasons": drill_info["failure_reasons"],
                            "actual_factors": actual_factors,
                            "results": drill_info["results"],
                        }
                    )
            else:
                geoms = prospect_geoms.get((stem, pid), [])
                if geoms and rep_year is not None:
                    matched_wells = []
                    matched_areas: list[float] = []
                    for w in fp_wildcats:
                        if w["entry_year"] is None or w["entry_year"] <= rep_year:
                            continue
                        wx, wy = w["lon"], w["lat"]
                        for bb, geom, area_val, layer in geoms:
                            if bb[0] <= wx <= bb[2] and bb[1] <= wy <= bb[3]:
                                if point_in_geom(wx, wy, geom):
                                    matched_wells.append(w)
                                    if area_val is not None:
                                        matched_areas.append(area_val)
                                    break
                    if matched_wells:
                        spatial_post_matched_total += 1
                        rep_a = pick_representative_assessment(p)
                        if rep_a is not None:
                            pg = get_assessment_pg(rep_a)
                            if pg is not None and 0.0 < pg < 0.99:
                                outcome = "discovery" if any(w["outcome"] == "discovery" for w in matched_wells) else "dry"
                                min_area = min(matched_areas) if matched_areas else None
                                row_obj = {
                                    "licence_id": licence_id,
                                    "prospect_name": pname,
                                    "operator": op,
                                    "area": area,
                                    "decade": decade,
                                    "report_year": rep_year,
                                    "well_year": min(w["entry_year"] for w in matched_wells),
                                    "well_names": [w["well_name"] for w in matched_wells],
                                    "min_polygon_area_km2": round(min_area, 2) if min_area is not None else None,
                                    "stage": rep_a.get("stage"),
                                    "pg": pg,
                                    "outcome": outcome,
                                    "is_commercial": outcome == "discovery",
                                    "source": "post_relinquishment_spatial",
                                }
                                post_relinq_rows.append(row_obj)
                                if min_area is not None and min_area <= 50.0:
                                    post_relinq_tight_rows.append(row_obj)

            rep_a = pick_representative_assessment(p)
            if rep_a is not None:
                pg = get_assessment_pg(rep_a)
                factors = get_assessment_factors(rep_a)
                p10_p90 = extract_p10_p90_ratio(rep_a)
                if len(factors) == 4:
                    min_val = min(factors.values())
                    lowest = [k for k, v in factors.items() if v == min_val]
                    if len(lowest) == 1:
                        atlas_lowest_factor[lowest[0]] += 1
                    else:
                        for k in lowest:
                            atlas_lowest_factor[k] += 1.0 / len(lowest)
                for el in (rep_a.get("risk") or {}).get("elements") or []:
                    if isinstance(el, dict) and el.get("rating") in ("high", "very_high"):
                        mapped = ELEMENT_TO_FACTOR.get(str(el.get("element") or ""))
                        if mapped:
                            atlas_high_risk_elements[mapped] += 1
                all_prospect_profiles.append(
                    {
                        "licence_id": licence_id,
                        "prospect_name": pname,
                        "operator": op,
                        "area": area,
                        "decade": decade,
                        "report_year": rep_year,
                        "pg": pg,
                        "p_reservoir": factors.get("reservoir"),
                        "p_trap": factors.get("trap"),
                        "p_charge": factors.get("charge"),
                        "p_retention": factors.get("retention"),
                        "p10_p90": p10_p90,
                    }
                )

            for a in p.get("assessments") or []:
                r = a.get("risk") or {}
                pg = get_assessment_pg(a)
                factors = get_assessment_factors(a)
                if pg is not None and len(factors) == 4:
                    prod = (
                        factors["reservoir"]
                        * factors["trap"]
                        * factors["charge"]
                        * factors["retention"]
                    )
                    gap = pg - prod
                    p_play = r.get("p_play")
                    p_play_val = float(p_play) if is_valid_prob(p_play) else None
                    pg_before_dhi = r.get("pg_before_dhi")
                    dhi_val = float(pg_before_dhi) if is_valid_prob(pg_before_dhi) else None
                    pg_math_records.append(
                        {
                            "licence_id": licence_id,
                            "prospect_name": pname,
                            "operator": op,
                            "area": area,
                            "stage": str(a.get("stage") or ""),
                            "pg": pg,
                            "product": prod,
                            "gap": gap,
                            "p_reservoir": factors["reservoir"],
                            "p_trap": factors["trap"],
                            "p_charge": factors["charge"],
                            "p_retention": factors["retention"],
                            "p_play": p_play_val,
                            "pg_before_dhi": dhi_val,
                            "has_dependencies": bool(r.get("dependencies")),
                            "pg_definition": str(r.get("pg_definition") or ""),
                        }
                    )

    combined_rows = full_in_licence_rows + post_relinq_rows
    commercial_strict_rows = [
        {**r, "outcome": "discovery" if r["is_commercial"] else "dry"}
        for r in strict_in_licence_rows
    ]
    commercial_full_in_licence_rows = [
        {**r, "outcome": "discovery" if r["is_commercial"] else "dry"}
        for r in full_in_licence_rows
    ]

    cal_by_basin_in_licence = {}
    for b in ("North Sea", "Norwegian Sea", "Barents Sea"):
        cal_by_basin_in_licence[b] = compute_calibration_stats([r for r in full_in_licence_rows if r["area"] == b])

    cal_by_basin_combined = {}
    for b in ("North Sea", "Norwegian Sea", "Barents Sea"):
        cal_by_basin_combined[b] = compute_calibration_stats([r for r in combined_rows if r["area"] == b])

    cal_by_decade_in_licence = {}
    for dec in ("2000s", "2010s", "2020s"):
        cal_by_decade_in_licence[dec] = compute_calibration_stats([r for r in full_in_licence_rows if r["decade"] == dec])

    stage_evol_summary = {}
    if stage_evolution_pairs:
        diffs = [x["pg_dod"] - x["pg_application"] for x in stage_evolution_pairs]
        stage_evol_summary = {
            "n": len(stage_evolution_pairs),
            "mean_pg_application": round(statistics.mean(x["pg_application"] for x in stage_evolution_pairs), 4),
            "mean_pg_drill_or_drop": round(statistics.mean(x["pg_dod"] for x in stage_evolution_pairs), 4),
            "mean_shift_pp": round(statistics.mean(diffs) * 100.0, 2),
            "upgraded_count": sum(1 for d in diffs if d > 0.005),
            "downgraded_count": sum(1 for d in diffs if d < -0.005),
            "unchanged_count": sum(1 for d in diffs if abs(d) <= 0.005),
            "actual_discovery_rate": round(
                sum(1 for x in stage_evolution_pairs if x["outcome"] == "discovery") / len(stage_evolution_pairs), 4
            ),
        }

    dry_total = len(dry_hole_records)
    dry_with_actual = [d for d in dry_hole_records if d["actual_factors"]]
    actual_cause_counts = Counter()
    raw_cause_counts = Counter()
    for d in dry_hole_records:
        for fr in d["raw_failure_reasons"]:
            raw_cause_counts[fr] += 1
        for af in d["actual_factors"]:
            actual_cause_counts[af] += 1

    dry_both = [d for d in dry_hole_records if len(d["factors"]) == 4 and d["actual_factors"]]
    confusion: dict[str, dict[str, int]] = {
        f1: {f2: 0 for f2 in ("reservoir", "trap", "charge", "retention")}
        for f1 in ("reservoir", "trap", "charge", "retention")
    }
    hit_count = 0
    blind_spots: dict[str, dict[str, Any]] = {}
    for factor in ("reservoir", "trap", "charge", "retention"):
        killed_by_f = [d for d in dry_both if factor in d["actual_factors"]]
        if killed_by_f:
            pre_vals = [d["factors"][factor] for d in killed_by_f]
            rated_ge_70 = sum(1 for v in pre_vals if v >= 0.70)
            rated_ge_80 = sum(1 for v in pre_vals if v >= 0.80)
            not_lowest = sum(
                1
                for d in killed_by_f
                if d["factors"][factor] > min(d["factors"].values()) + 1e-9
            )
            blind_spots[factor] = {
                "n_killed_by_factor": len(killed_by_f),
                "mean_pre_drill_p": round(statistics.mean(pre_vals), 4),
                "median_pre_drill_p": round(statistics.median(pre_vals), 4),
                "rated_ge_070_count": rated_ge_70,
                "rated_ge_070_pct": round(rated_ge_70 / len(killed_by_f) * 100.0, 1),
                "rated_ge_080_count": rated_ge_80,
                "rated_ge_080_pct": round(rated_ge_80 / len(killed_by_f) * 100.0, 1),
                "not_top_fear_count": not_lowest,
                "not_top_fear_pct": round(not_lowest / len(killed_by_f) * 100.0, 1),
            }

    for d in dry_both:
        min_v = min(d["factors"].values())
        top_fears = [k for k, v in d["factors"].items() if abs(v - min_v) < 1e-9]
        if any(tf in d["actual_factors"] for tf in top_fears):
            hit_count += 1
        primary_fear = top_fears[0]
        for af in d["actual_factors"]:
            confusion[primary_fear][af] += 1

    dry_qual = [d for d in dry_hole_records if d["qual_fears"] and d["actual_factors"]]
    qual_overlap_hits = sum(1 for d in dry_qual if set(d["qual_fears"]) & set(d["actual_factors"]))
    qual_blind_spots: dict[str, dict[str, Any]] = {}
    for factor in ("reservoir", "trap", "charge", "retention"):
        killed = [d for d in dry_qual if factor in d["actual_factors"]]
        if killed:
            missed = sum(1 for d in killed if factor not in d["qual_fears"])
            qual_blind_spots[factor] = {
                "n_killed": len(killed),
                "flagged_high_risk_pre_drill": len(killed) - missed,
                "unflagged_blind_spot_count": missed,
                "unflagged_blind_spot_pct": round(missed / len(killed) * 100.0, 1),
            }

    total_lowest = sum(atlas_lowest_factor.values())
    total_actual_mentions = sum(actual_cause_counts.values())
    macro_fear_vs_reality = {}
    for factor in ("reservoir", "charge", "retention", "trap"):
        fear_pct = (atlas_lowest_factor[factor] / total_lowest * 100.0) if total_lowest else 0.0
        actual_pct = (actual_cause_counts[factor] / total_actual_mentions * 100.0) if total_actual_mentions else 0.0
        macro_fear_vs_reality[factor] = {
            "atlas_top_fear_pct": round(fear_pct, 1),
            "actual_dry_hole_cause_pct": round(actual_pct, 1),
            "reality_to_fear_ratio": round(actual_pct / fear_pct, 2) if fear_pct > 0 else None,
        }

    def summarize_group(items: list[dict[str, Any]]) -> dict[str, Any]:
        pgs = [x["pg"] for x in items if x["pg"] is not None]
        p10s = [x["p10_p90"] for x in items if x["p10_p90"] is not None]
        out: dict[str, Any] = {
            "n_with_pg": len(pgs),
            "mean_pg": round(statistics.mean(pgs), 4) if pgs else None,
            "median_pg": round(statistics.median(pgs), 4) if pgs else None,
            "n_with_p10_p90": len(p10s),
            "median_p10_p90": round(statistics.median(p10s), 2) if p10s else None,
            "mean_p10_p90": round(statistics.mean(p10s), 2) if p10s else None,
        }
        for fk in ("p_reservoir", "p_trap", "p_charge", "p_retention"):
            vals = [x[fk] for x in items if x[fk] is not None]
            out[f"mean_{fk}"] = round(statistics.mean(vals), 4) if vals else None
            out[f"n_{fk}"] = len(vals)
        return out

    basin_means = {}
    basin_profiles = {}
    for b in ("North Sea", "Norwegian Sea", "Barents Sea"):
        sub = [x for x in all_prospect_profiles if x["area"] == b]
        basin_profiles[b] = summarize_group(sub)
        basin_means[b] = basin_profiles[b]["mean_pg"] or 0.0

    decade_profiles = {}
    for dec in ("2000s", "2010s", "2020s"):
        sub = [x for x in all_prospect_profiles if x["decade"] == dec]
        decade_profiles[dec] = summarize_group(sub)

    by_op: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for x in all_prospect_profiles:
        by_op[x["operator"]].append(x)

    op_cal_in_lic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in full_in_licence_rows:
        op_cal_in_lic[r["operator"]].append(r)

    operator_profiles = {}
    for op_name, items in sorted(by_op.items(), key=lambda kv: -len(kv[1])):
        if op_name in ("Other", "Unknown") or len(items) < 20:
            continue
        prof = summarize_group(items)
        residuals = [
            x["pg"] - basin_means[x["area"]]
            for x in items
            if x["pg"] is not None and x["area"] in basin_means
        ]
        prof["basin_adjusted_pg_pp"] = round(statistics.mean(residuals) * 100.0, 2) if residuals else None
        cal_rows = op_cal_in_lic.get(op_name, [])
        if len(cal_rows) >= 5:
            prof["in_licence_drilled_n"] = len(cal_rows)
            prof["in_licence_mean_pg"] = round(statistics.mean(r["pg"] for r in cal_rows), 4)
            prof["in_licence_actual_rate"] = round(
                sum(1 for r in cal_rows if r["outcome"] == "discovery") / len(cal_rows), 4
            )
            prof["in_licence_gap_pp"] = round(
                (prof["in_licence_actual_rate"] - prof["in_licence_mean_pg"]) * 100.0, 2
            )
        operator_profiles[op_name] = prof

    n_math = len(pg_math_records)
    exact_05 = [x for x in pg_math_records if abs(x["gap"]) <= 0.005]
    gt_05 = [x for x in pg_math_records if x["gap"] > 0.005]
    lt_05 = [x for x in pg_math_records if x["gap"] < -0.005]
    gt_15 = [x for x in pg_math_records if x["gap"] > 0.015]
    lt_15 = [x for x in pg_math_records if x["gap"] < -0.015]

    lt_explained_play = [
        x for x in lt_05
        if x["p_play"] is not None and abs(x["pg"] - x["product"] * x["p_play"]) <= 0.015
    ]
    gt_with_dhi = [x for x in gt_05 if x["pg_before_dhi"] is not None]
    lt_with_dep = [x for x in lt_05 if x["has_dependencies"]]

    math_by_op = {}
    op_math_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for x in pg_math_records:
        op_math_groups[x["operator"]].append(x)
    for op_name, items in sorted(op_math_groups.items(), key=lambda kv: -len(kv[1])):
        if op_name in ("Other", "Unknown") or len(items) < 20:
            continue
        hi = sum(1 for x in items if x["gap"] > 0.005)
        lo = sum(1 for x in items if x["gap"] < -0.005)
        math_by_op[op_name] = {
            "n": len(items),
            "disagree_pct": round((hi + lo) / len(items) * 100.0, 1),
            "higher_count": hi,
            "lower_count": lo,
            "mean_gap_pp": round(statistics.mean(x["gap"] for x in items) * 100.0, 2),
        }

    top_positive_gaps = sorted(pg_math_records, key=lambda x: -x["gap"])[:8]
    top_negative_gaps = sorted(pg_math_records, key=lambda x: x["gap"])[:8]

    pg_math_summary = {
        "n_assessments_with_pg_and_4_factors": n_math,
        "exact_within_05pp_count": len(exact_05),
        "exact_within_05pp_pct": round(len(exact_05) / n_math * 100.0, 2) if n_math else 0.0,
        "disagree_gt_05pp_count": len(gt_05) + len(lt_05),
        "disagree_gt_05pp_pct": round((len(gt_05) + len(lt_05)) / n_math * 100.0, 2) if n_math else 0.0,
        "pg_higher_than_product_05pp_count": len(gt_05),
        "pg_higher_than_product_05pp_pct": round(len(gt_05) / n_math * 100.0, 2) if n_math else 0.0,
        "pg_lower_than_product_05pp_count": len(lt_05),
        "pg_lower_than_product_05pp_pct": round(len(lt_05) / n_math * 100.0, 2) if n_math else 0.0,
        "material_disagree_gt_15pp_count": len(gt_15) + len(lt_15),
        "material_disagree_gt_15pp_pct": round((len(gt_15) + len(lt_15)) / n_math * 100.0, 2) if n_math else 0.0,
        "material_pg_higher_15pp_count": len(gt_15),
        "material_pg_lower_15pp_count": len(lt_15),
        "mean_gap_all_pp": round(statistics.mean(x["gap"] for x in pg_math_records) * 100.0, 3) if n_math else 0.0,
        "mean_gap_disagree_05pp": round(
            statistics.mean(x["gap"] for x in gt_05 + lt_05) * 100.0, 2
        ) if (gt_05 or lt_05) else 0.0,
        "mean_positive_gap_pp": round(statistics.mean(x["gap"] for x in gt_05) * 100.0, 2) if gt_05 else 0.0,
        "mean_negative_gap_pp": round(statistics.mean(x["gap"] for x in lt_05) * 100.0, 2) if lt_05 else 0.0,
        "lower_explained_by_p_play_count": len(lt_explained_play),
        "lower_with_dependencies_count": len(lt_with_dep),
        "higher_with_pg_before_dhi_count": len(gt_with_dhi),
        "by_operator": math_by_op,
        "top_positive_examples": [
            {
                "licence_id": x["licence_id"],
                "prospect_name": x["prospect_name"],
                "operator": x["operator"],
                "pg": round(x["pg"], 3),
                "product": round(x["product"], 3),
                "gap_pp": round(x["gap"] * 100.0, 1),
                "pg_before_dhi": x["pg_before_dhi"],
                "pg_definition": x["pg_definition"][:80],
            }
            for x in top_positive_gaps
        ],
        "top_negative_examples": [
            {
                "licence_id": x["licence_id"],
                "prospect_name": x["prospect_name"],
                "operator": x["operator"],
                "pg": round(x["pg"], 3),
                "product": round(x["product"], 3),
                "gap_pp": round(x["gap"] * 100.0, 1),
                "p_play": x["p_play"],
                "pg_definition": x["pg_definition"][:80],
            }
            for x in top_negative_gaps
        ],
    }

    findings = {
        "corpus": {
            "deduplicated_licences": len(kept_j),
            "dropped_duplicate_licences": len(dropped),
            "total_prospects": total_prospects,
            "prospects_with_exploration_pg": len(all_prospect_profiles),
            "in_licence_drilled_total": in_licence_drilled_total,
            "in_licence_drilled_outcomes": dict(in_licence_drilled_outcomes),
            "post_relinquishment_spatial_matched_total": spatial_post_matched_total,
            "post_relinquishment_with_pg": len(post_relinq_rows),
            "post_relinquishment_tight_le50km2_with_pg": len(post_relinq_tight_rows),
        },
        "calibration": {
            "strict_in_licence_exploration": compute_calibration_stats(strict_in_licence_rows),
            "full_in_licence_exploration": compute_calibration_stats(full_in_licence_rows),
            "post_relinquishment_out_of_sample": compute_calibration_stats(post_relinq_rows),
            "post_relinquishment_tight_le50km2": compute_calibration_stats(post_relinq_tight_rows),
            "combined_exploration": compute_calibration_stats(combined_rows),
            "commercial_only_strict_in_licence": compute_calibration_stats(commercial_strict_rows),
            "commercial_only_full_in_licence": compute_calibration_stats(commercial_full_in_licence_rows),
            "by_basin_in_licence": cal_by_basin_in_licence,
            "by_basin_combined": cal_by_basin_combined,
            "by_decade_in_licence": cal_by_decade_in_licence,
            "stage_evolution_application_to_dod": stage_evol_summary,
        },
        "fear_vs_failure": {
            "total_dry_holes": dry_total,
            "dry_holes_with_identified_failure_factor": len(dry_with_actual),
            "macro_fear_vs_reality": macro_fear_vs_reality,
            "dry_holes_with_4_factors_and_actual_cause": len(dry_both),
            "top_fear_hit_rate_count": hit_count,
            "top_fear_hit_rate_pct": round(hit_count / len(dry_both) * 100.0, 1) if dry_both else 0.0,
            "dry_holes_with_qual_high_risk_and_actual_cause": len(dry_qual),
            "qual_high_risk_overlap_hits": qual_overlap_hits,
            "qual_high_risk_overlap_pct": round(qual_overlap_hits / len(dry_qual) * 100.0, 1) if dry_qual else 0.0,
            "qual_blind_spots_by_actual_cause": qual_blind_spots,
            "atlas_wide_lowest_factor_counts": {k: round(v, 1) for k, v in atlas_lowest_factor.items()},
            "atlas_wide_high_risk_element_counts": dict(atlas_high_risk_elements),
            "actual_dry_hole_factor_counts": dict(actual_cause_counts),
            "actual_dry_hole_raw_reason_counts": dict(raw_cause_counts.most_common(15)),
            "confusion_matrix_pre_fear_vs_actual_cause": confusion,
            "quant_blind_spots_by_actual_cause": blind_spots,
        },
        "fingerprints": {
            "by_basin": basin_profiles,
            "by_decade": decade_profiles,
            "by_operator": operator_profiles,
        },
        "pg_math_gap": pg_math_summary,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / "track2_findings.json"
    out_json.write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== TRACK 2 CLEAN EXPLORATION CALIBRATION ===")
    for key in (
        "strict_in_licence_exploration",
        "full_in_licence_exploration",
        "commercial_only_strict_in_licence",
        "post_relinquishment_out_of_sample",
        "post_relinquishment_tight_le50km2",
        "combined_exploration",
    ):
        c = findings["calibration"][key]
        print(
            f"  {key:35s}: n={c['n']:3d}, pred={c['mean_predicted_pg']:.3f}, "
            f"actual={c['actual_discovery_rate']:.3f} ({c['discoveries']}/{c['n']}), "
            f"gap={c['gap_pp']:+6.2f}pp, z={c['z_stat']:+5.2f}, p={c['p_value']:.5f}, brier={c['brier_score']:.4f}"
        )

    print("\n--- STRICT IN-LICENCE EXPLORATION BINS (excluding existing discoveries) ---")
    for b in findings["calibration"]["strict_in_licence_exploration"]["bins"]:
        print(" ", b)

    print("\n--- POST-RELINQUISHMENT TIGHT (<=50km2) BINS ---")
    for b in findings["calibration"]["post_relinquishment_tight_le50km2"]["bins"]:
        print(" ", b)

    print("\n--- IN-LICENCE CALIBRATION BY BASIN ---")
    for b, c in cal_by_basin_in_licence.items():
        if c.get("n"):
            print(f"  {b:15s}: n={c['n']:3d}, pred={c['mean_predicted_pg']:.3f}, actual={c['actual_discovery_rate']:.3f}, gap={c['gap_pp']:+6.2f}pp, p={c['p_value']:.4f}")

    print("\n--- MACRO FEAR VS REALITY ---")
    print(json.dumps(macro_fear_vs_reality, indent=2))
    print("\n--- QUALITATIVE BLIND SPOTS (n=52 dry holes) ---")
    print(json.dumps(qual_blind_spots, indent=2))
    print("\n--- BASIN PROFILES ---")
    print(json.dumps(basin_profiles, indent=2))
    print("\n--- DECADE PROFILES ---")
    print(json.dumps(decade_profiles, indent=2))
    print("\n--- PG MATH GAP BY OPERATOR ---")
    print(json.dumps(math_by_op, indent=2))


if __name__ == "__main__":
    main()
