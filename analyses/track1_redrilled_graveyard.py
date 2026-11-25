import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import polars as pl

SRC_DIR = Path(r"C:\Users\philip\Documents\ncs-relinquished-atlas\src")
OUT_DIR = Path(r"C:\Users\philip\Documents\ncs-relinquished-atlas\analyses")
sys.path.insert(0, str(SRC_DIR))

from loader import (
    DEFAULT_FACTPAGES_WELLS,
    deduplicate_records,
    load_raw_records,
    safe_canonical_volume_msmo3,
)

DISCOVERY_CONTENTS = {
    "OIL",
    "GAS",
    "OIL/GAS",
    "GAS/CONDENSATE",
    "OIL/GAS/CONDENSATE",
}
NON_DISCOVERY_CONTENTS = {
    "DRY",
    "SHOWS",
    "OIL SHOWS",
    "GAS SHOWS",
    "OIL/GAS SHOWS",
    "WATER",
    "WATER/GAS",
}
ALREADY_DISCOVERY_STATUSES = {"drilled_discovery", "discovery_marginal"}
ALREADY_DRILLED_STATUSES = {"drilled_discovery", "discovery_marginal", "drilled_dry"}


def parse_year(val: Any) -> int | None:
    if val is None:
        return None
    if isinstance(val, int) and 1960 <= val <= 2030:
        return val
    m = re.search(r"(19\d{2}|20\d{2})", str(val))
    if m:
        yr = int(m.group(1))
        if 1960 <= yr <= 2030:
            return yr
    return None


def get_report_year(rec: dict[str, Any]) -> int | None:
    lic = rec.get("licence") or {}
    doc = rec.get("document") or {}
    for candidate in (lic.get("relinquishment_date"), doc.get("date")):
        yr = parse_year(candidate)
        if yr is not None:
            return yr
    milestone_years = [
        yr
        for ms in (lic.get("milestones") or [])
        if isinstance(ms, dict)
        for yr in [parse_year(ms.get("date"))]
        if yr is not None
    ]
    if milestone_years:
        return max(milestone_years)
    return parse_year(lic.get("award_date"))


def canonical_operator(name: str | None) -> str:
    if not name:
        return "UNKNOWN"
    s = re.sub(r"\s+", " ", str(name)).strip().lower()
    if any(k in s for k in ("equinor", "statoil", "norsk hydro", "hydro olje")):
        return "Equinor (incl. Statoil/Hydro)"
    if any(k in s for k in ("aker bp", "det norske", "bp norge", "marathon oil", "pertra")):
        return "Aker BP (incl. Det norske/BP Norge)"
    if any(k in s for k in ("lundin",)):
        return "Lundin"
    if any(k in s for k in ("vår energi", "var energi", "eni norge", "norsk agip", "point resources", "neptune energy", "engie", "gdf suez", "exxonmobil", "esso")):
        return "Vår Energi (incl. Eni/Point/Neptune/ExxonMobil)"
    if any(k in s for k in ("harbour energy", "wintershall", "dea norge", "dea e&p", "rwe dea", "edison")):
        return "Harbour / Wintershall Dea"
    if any(k in s for k in ("conocophillips", "phillips petroleum")):
        return "ConocoPhillips"
    if any(k in s for k in ("shell",)):
        return "Shell"
    if any(k in s for k in ("totalenergies", "total e&p", "total norge", "maersk oil", "elf")):
        return "TotalEnergies (incl. Maersk/Total)"
    if any(k in s for k in ("omv",)):
        return "OMV"
    if any(k in s for k in ("dno", "faroe petroleum")):
        return "DNO (incl. Faroe)"
    if any(k in s for k in ("orlen", "pgnig", "kufpec", "ineos", "dong")):
        if "orlen" in s or "pgnig" in s:
            return "ORLEN / PGNiG"
        if "ineos" in s or "dong" in s:
            return "INEOS / DONG"
        return "KUFPEC"
    if any(k in s for k in ("sval energi", "spirit energy", "centrica", "bayerngas", "tullow")):
        if "sval" in s or "spirit" in s or "centrica" in s or "bayerngas" in s:
            return "Sval / Spirit / Centrica"
        return "Tullow"
    if any(k in s for k in ("wellesley",)):
        return "Wellesley"
    if any(k in s for k in ("repsol", "talisman")):
        return "Repsol (incl. Talisman)"
    if any(k in s for k in ("okt", "okea",)):
        return "OKEA"
    if any(k in s for k in ("pandion",)):
        return "Pandion"
    if any(k in s for k in ("capricorn", "cairn")):
        return "Capricorn / Cairn"
    if any(k in s for k in ("chevron",)):
        return "Chevron"
    if any(k in s for k in ("suncor",)):
        return "Suncor"
    if any(k in s for k in ("vng",)):
        return "VNG"
    if any(k in s for k in ("e.on", "eon")):
        return "E.ON"
    if any(k in s for k in ("bg norge",)):
        return "BG Norge"
    if any(k in s for k in ("premier oil",)):
        return "Premier Oil"
    if any(k in s for k in ("lundin",)):
        return "Lundin"
    if any(k in s for k in ("mol norge",)):
        return "MOL Norge"
    if any(k in s for k in ("chrysaor",)):
        return "Chrysaor"
    if any(k in s for k in ("petoro",)):
        return "Petoro"
    if any(k in s for k in ("concedo",)):
        return "Concedo"
    if any(k in s for k in ("source energy",)):
        return "Source Energy"
    if any(k in s for k in ("idemat", "idemitsu")):
        return "Idemitsu"
    if any(k in s for k in ("norske aec", "norske shell")):
        return "Shell"
    if any(k in s for k in ("lotus", "lotos")):
        return "LOTOS"
    return str(name).strip()


def same_operator_with_lundin(op1: str | None, op2: str | None) -> bool:
    c1 = canonical_operator(op1)
    c2 = canonical_operator(op2)
    if c1 == "UNKNOWN" or c2 == "UNKNOWN":
        return False
    if c1 == c2:
        return True
    aker_group = {"Aker BP (incl. Det norske/BP Norge)", "Lundin"}
    if c1 in aker_group and c2 in aker_group:
        return True
    return False


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    n = len(ring)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i
    return inside


def point_in_polygon_coords(lon: float, lat: float, poly_coords: list[list[list[float]]]) -> bool:
    if not poly_coords or not point_in_ring(lon, lat, poly_coords[0]):
        return False
    for hole in poly_coords[1:]:
        if point_in_ring(lon, lat, hole):
            return False
    return True


def geometry_bbox(geom: dict[str, Any]) -> tuple[float, float, float, float] | None:
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if not coords:
        return None
    xs: list[float] = []
    ys: list[float] = []
    if gtype == "Polygon":
        for pt in coords[0]:
            xs.append(pt[0])
            ys.append(pt[1])
    elif gtype == "MultiPolygon":
        for poly in coords:
            if poly:
                for pt in poly[0]:
                    xs.append(pt[0])
                    ys.append(pt[1])
    else:
        return None
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def point_in_geometry(lon: float, lat: float, geom: dict[str, Any]) -> bool:
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if gtype == "Polygon":
        return point_in_polygon_coords(lon, lat, coords)
    if gtype == "MultiPolygon":
        return any(point_in_polygon_coords(lon, lat, poly) for poly in coords)
    return False


def stage_priority(stage: str | None) -> int:
    s = (stage or "").lower()
    order = {
        "final": 5,
        "relinquishment": 5,
        "post_well": 4,
        "drill_or_drop": 3,
        "intermediate": 2,
        "award": 1,
        "application": 0,
    }
    return order.get(s, 2)


def extract_prospect_pg_and_volume(prospect: dict[str, Any]) -> dict[str, Any]:
    assessments = prospect.get("assessments") or []
    ranked = sorted(
        enumerate(assessments),
        key=lambda iv: (stage_priority(iv[1].get("stage")), iv[0]),
        reverse=True,
    )
    pg_val: float | None = None
    pg_stage: str | None = None
    pg_elements: dict[str, float] = {}
    for _, a in ranked:
        risk = a.get("risk") or {}
        if isinstance(risk, dict):
            pg = risk.get("pg")
            if isinstance(pg, (int, float)) and not isinstance(pg, bool) and 0.0 <= pg <= 1.0:
                pg_val = float(pg)
                pg_stage = a.get("stage")
                for k in ("p_reservoir", "p_trap", "p_charge", "p_retention"):
                    v = risk.get(k)
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        pg_elements[k] = float(v)
                break
            elif isinstance(pg, (int, float)) and not isinstance(pg, bool) and 1.0 < pg <= 100.0:
                pg_val = float(pg) / 100.0
                pg_stage = a.get("stage")
                break

    vol_mean_msmo3: float | None = None
    vol_p90_msmo3: float | None = None
    vol_p10_msmo3: float | None = None
    vol_phase: str | None = None
    vol_stage: str | None = None
    for _, a in ranked:
        vols = a.get("volumes") or []
        best_v = None
        for v in vols:
            if not isinstance(v, dict):
                continue
            if v.get("basis") not in (None, "recoverable", "unknown"):
                continue
            if v.get("risking") == "risked":
                continue
            m = safe_canonical_volume_msmo3(v, "mean")
            if m is None:
                m = safe_canonical_volume_msmo3(v, "p50")
            if m is None:
                m = safe_canonical_volume_msmo3(v, "single_value")
            if m is not None and m > 0:
                is_total = (v.get("phase") or "").lower() in ("total", "oe", "oil_equivalent", "combined", "oil_and_gas")
                if best_v is None or (is_total and not best_v[0]) or (is_total == best_v[0] and m > best_v[1]):
                    best_v = (is_total, m, v)
        if best_v is not None:
            _, m, v = best_v
            vol_mean_msmo3 = round(m, 3)
            p90 = safe_canonical_volume_msmo3(v, "p90")
            p10 = safe_canonical_volume_msmo3(v, "p10")
            vol_p90_msmo3 = round(p90, 3) if p90 is not None else None
            vol_p10_msmo3 = round(p10, 3) if p10 is not None else None
            vol_phase = v.get("phase")
            vol_stage = a.get("stage")
            break

    return {
        "pg": pg_val,
        "pg_stage": pg_stage,
        "pg_elements": pg_elements,
        "mean_msmo3": vol_mean_msmo3,
        "mean_mmboe": round(vol_mean_msmo3 * 6.2898, 2) if vol_mean_msmo3 is not None else None,
        "p90_msmo3": vol_p90_msmo3,
        "p10_msmo3": vol_p10_msmo3,
        "vol_phase": vol_phase,
        "vol_stage": vol_stage,
    }


def extract_risk_elements(prospect: dict[str, Any]) -> list[str]:
    elems: list[str] = []
    for kr in (prospect.get("key_risks") or []):
        if isinstance(kr, dict) and kr.get("element"):
            elems.append(str(kr["element"]).strip().lower())
    return sorted(set(elems))


def extract_reasons_not_drilled(prospect: dict[str, Any]) -> list[str]:
    conc = prospect.get("conclusion") or {}
    if isinstance(conc, dict):
        return sorted(set(str(r).strip().lower() for r in (conc.get("reasons_not_drilled") or []) if r))
    return []


def two_proportion_z_test(k1: int, n1: int, k2: int, n2: int) -> dict[str, float | None]:
    if n1 == 0 or n2 == 0:
        return {"z": None, "p_value": None}
    p1 = k1 / n1
    p2 = k2 / n2
    p_pool = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n1 + 1.0 / n2))
    if se == 0.0:
        return {"z": 0.0, "p_value": 1.0}
    z = (p1 - p2) / se
    p_val = math.erfc(abs(z) / math.sqrt(2.0))
    return {"z": round(z, 3), "p_value": round(p_val, 5)}


def binomial_two_sided_p(k: int, n: int, p0: float) -> float | None:
    if n == 0 or p0 <= 0.0 or p0 >= 1.0:
        return None
    se = math.sqrt(p0 * (1.0 - p0) / n)
    if se == 0.0:
        return None
    z = ((k / n) - p0) / se
    return round(math.erfc(abs(z) / math.sqrt(2.0)), 6)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_json, raw_geo = load_raw_records()
    kept_json, kept_geo, dropped_stems = deduplicate_records(raw_json, raw_geo)

    df_wells = pl.read_parquet(DEFAULT_FACTPAGES_WELLS)
    wells: list[dict[str, Any]] = []
    for row in df_wells.to_dicts():
        lat = row.get("wlbNsDecDeg")
        lon = row.get("wlbEwDecDeg")
        yr = row.get("wlbCompletionYear")
        status = (row.get("wlbStatus") or "").strip().upper()
        if lat is None or lon is None or yr is None or yr <= 0:
            continue
        if status == "WILL NEVER BE DRILLED":
            continue
        content = (row.get("wlbContent") or "").strip().upper()
        is_disc_content = content in DISCOVERY_CONTENTS
        is_non_disc_content = content in NON_DISCOVERY_CONTENTS
        has_known_outcome = is_disc_content or is_non_disc_content
        wells.append(
            {
                "wellbore_name": row.get("wlbWellboreName"),
                "completion_year": int(yr),
                "operator": row.get("wlbDrillingOperator"),
                "operator_canonical": canonical_operator(row.get("wlbDrillingOperator")),
                "licence": row.get("wlbProductionLicence"),
                "purpose": (row.get("wlbPurpose") or "").strip().upper(),
                "status": status,
                "content": content or None,
                "discovery": row.get("wlbDiscovery"),
                "discovery_wellbore": (row.get("wlbDiscoveryWellbore") or "").strip().upper() == "YES",
                "field": row.get("wlbField"),
                "main_area": row.get("wlbMainArea"),
                "hc_fm1": row.get("wlbFormationWithHc1"),
                "hc_age1": row.get("wlbAgeWithHc1"),
                "lat": float(lat),
                "lon": float(lon),
                "is_discovery": is_disc_content,
                "has_known_outcome": has_known_outcome,
            }
        )

    internal_qc_post_relinq: list[dict[str, Any]] = []
    prospect_index: dict[tuple[str, str], dict[str, Any]] = {}
    all_prospect_records: list[dict[str, Any]] = []

    for stem, rec in kept_json.items():
        report_year = get_report_year(rec)
        lic = rec.get("licence") or {}
        lic_id = lic.get("licence_id")
        lic_area = lic.get("area")
        lic_op = lic.get("operator")
        lic_op_canon = canonical_operator(lic_op)
        lic_relinq_reason = lic.get("relinquishment_reason")

        for p in (rec.get("prospects") or []):
            pid = p.get("prospect_id")
            if not pid:
                continue
            pg_vol = extract_prospect_pg_and_volume(p)
            conc = p.get("conclusion") or {}
            conc_text = conc.get("text") if isinstance(conc, dict) else (str(conc) if conc else None)
            kr_list = [
                {
                    "element": kr.get("element"),
                    "severity": kr.get("severity"),
                    "reason": kr.get("reason"),
                }
                for kr in (p.get("key_risks") or [])
                if isinstance(kr, dict)
            ]
            p_info = {
                "stem": stem,
                "licence_id": lic_id,
                "area": lic_area,
                "operator": lic_op,
                "operator_canonical": lic_op_canon,
                "report_year": report_year,
                "relinquishment_reason": lic_relinq_reason,
                "prospect_id": pid,
                "name": p.get("name"),
                "classification": p.get("classification"),
                "status_at_report": p.get("status_at_report"),
                "pg": pg_vol["pg"],
                "pg_stage": pg_vol["pg_stage"],
                "pg_elements": pg_vol["pg_elements"],
                "mean_msmo3": pg_vol["mean_msmo3"],
                "mean_mmboe": pg_vol["mean_mmboe"],
                "p90_msmo3": pg_vol["p90_msmo3"],
                "p10_msmo3": pg_vol["p10_msmo3"],
                "vol_phase": pg_vol["vol_phase"],
                "risk_elements": extract_risk_elements(p),
                "reasons_not_drilled": extract_reasons_not_drilled(p),
                "key_risks": kr_list,
                "conclusion_text": conc_text,
            }
            prospect_index[(stem, pid)] = p_info
            all_prospect_records.append(p_info)

            for q in (p.get("qc_flags") or []):
                qs = str(q)
                ql = qs.lower()
                if "sodir wellbore data" in ql and (
                    "lies inside" in ql or "lie inside" in ql or "drilled after" in ql or "later well" in ql
                ):
                    internal_qc_post_relinq.append(
                        {
                            "stem": stem,
                            "licence_id": lic_id,
                            "report_year": report_year,
                            "prospect_id": pid,
                            "name": p.get("name"),
                            "status_at_report": p.get("status_at_report"),
                            "qc_flag": qs,
                        }
                    )

    polygon_features: list[dict[str, Any]] = []
    unmatched_geo_features = 0
    prospects_with_polygons: set[tuple[str, str]] = set()

    for stem, fc in kept_geo.items():
        for feat in (fc.get("features") or []):
            props = feat.get("properties") or {}
            layer = props.get("layer")
            if layer not in ("prospect", "lead"):
                continue
            geom = feat.get("geometry") or {}
            gtype = geom.get("type")
            if gtype not in ("Polygon", "MultiPolygon"):
                continue
            bbox = geometry_bbox(geom)
            if bbox is None:
                continue
            rec_ref = props.get("record_ref") or {}
            pid = rec_ref.get("prospect_id") if isinstance(rec_ref, dict) else None
            p_info = prospect_index.get((stem, pid)) if pid else None
            if p_info is None:
                unmatched_geo_features += 1
                continue
            prospects_with_polygons.add((stem, pid))
            polygon_features.append(
                {
                    "stem": stem,
                    "prospect_id": pid,
                    "feature_id": props.get("feature_id"),
                    "layer": layer,
                    "stage": props.get("stage"),
                    "is_primary": bool(props.get("is_primary")),
                    "area_km2": props.get("area_km2_geometry"),
                    "bbox": bbox,
                    "geometry": geom,
                    "prospect": p_info,
                }
            )

    prospect_well_matches: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    raw_feature_well_hits = 0

    for feat in polygon_features:
        p_info = feat["prospect"]
        rep_yr = p_info["report_year"]
        if rep_yr is None:
            continue
        min_lon, min_lat, max_lon, max_lat = feat["bbox"]
        key = (feat["stem"], feat["prospect_id"])
        for w in wells:
            if w["completion_year"] <= rep_yr:
                continue
            lon = w["lon"]
            lat = w["lat"]
            if lon < min_lon or lon > max_lon or lat < min_lat or lat > max_lat:
                continue
            if point_in_geometry(lon, lat, feat["geometry"]):
                raw_feature_well_hits += 1
                wname = w["wellbore_name"]
                existing = prospect_well_matches[key].get(wname)
                if existing is None or (feat["is_primary"] and not existing["feature_is_primary"]):
                    prospect_well_matches[key][wname] = {
                        "well": w,
                        "feature_id": feat["feature_id"],
                        "feature_layer": feat["layer"],
                        "feature_stage": feat["stage"],
                        "feature_is_primary": feat["is_primary"],
                        "feature_area_km2": feat["area_km2"],
                    }

    def summarize_cohort(
        cohort_keys: list[tuple[str, str]],
        wildcat_only: bool,
        known_outcome_only: bool = True,
    ) -> dict[str, Any]:
        prospect_rows: list[dict[str, Any]] = []
        well_hits: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for key in cohort_keys:
            p_info = prospect_index[key]
            matched_wells = list(prospect_well_matches[key].values())
            if wildcat_only:
                matched_wells = [m for m in matched_wells if m["well"]["purpose"] == "WILDCAT"]
            if known_outcome_only:
                matched_wells = [m for m in matched_wells if m["well"]["has_known_outcome"]]
            if not matched_wells:
                continue
            matched_wells.sort(key=lambda m: (m["well"]["completion_year"], m["well"]["wellbore_name"]))
            any_disc = any(m["well"]["is_discovery"] for m in matched_wells)
            disc_wells = [m["well"] for m in matched_wells if m["well"]["is_discovery"]]
            first_well = matched_wells[0]["well"]
            first_disc = disc_wells[0] if disc_wells else None
            any_field = any(m["well"]["field"] for m in matched_wells if m["well"]["is_discovery"])
            fields = sorted({m["well"]["field"] for m in matched_wells if m["well"]["is_discovery"] and m["well"]["field"]})
            discoveries = sorted({m["well"]["discovery"] for m in matched_wells if m["well"]["is_discovery"] and m["well"]["discovery"]})
            same_op_first = same_operator_with_lundin(p_info["operator"], first_well["operator"])
            same_op_strict_first = canonical_operator(p_info["operator"]) == first_well["operator_canonical"]
            if first_disc is not None:
                same_op_rep = same_operator_with_lundin(p_info["operator"], first_disc["operator"])
                same_op_strict_rep = canonical_operator(p_info["operator"]) == first_disc["operator_canonical"]
            else:
                same_op_rep = same_op_first
                same_op_strict_rep = same_op_strict_first

            row = {
                "key": f"{key[0]}::{key[1]}",
                "prospect": p_info,
                "matched_wells": [m["well"] for m in matched_wells],
                "feature_area_km2": matched_wells[0]["feature_area_km2"],
                "feature_layer": matched_wells[0]["feature_layer"],
                "is_discovery": any_disc,
                "became_field": any_field,
                "fields": fields,
                "discoveries": discoveries,
                "first_well": first_well,
                "first_discovery_well": first_disc,
                "same_operator_lineage": same_op_rep,
                "same_operator_canonical": same_op_strict_rep,
                "years_after_relinquishment": (first_disc or first_well)["completion_year"] - p_info["report_year"],
            }
            prospect_rows.append(row)
            for m in matched_wells:
                well_hits[m["well"]["wellbore_name"]].append(row)

        n_pros = len(prospect_rows)
        n_disc = sum(1 for r in prospect_rows if r["is_discovery"])
        n_field = sum(1 for r in prospect_rows if r["became_field"])
        disc_rate = round(n_disc / n_pros, 4) if n_pros else None

        pg_rows = [r for r in prospect_rows if r["prospect"]["pg"] is not None]
        n_pg = len(pg_rows)
        n_pg_disc = sum(1 for r in pg_rows if r["is_discovery"])
        mean_pg = round(sum(r["prospect"]["pg"] for r in pg_rows) / n_pg, 4) if n_pg else None
        sorted_pgs = sorted(r["prospect"]["pg"] for r in pg_rows)
        median_pg = (
            round(
                (sorted_pgs[n_pg // 2] + sorted_pgs[(n_pg - 1) // 2]) / 2.0,
                4,
            )
            if n_pg
            else None
        )
        pg_disc_rate = round(n_pg_disc / n_pg, 4) if n_pg else None
        cal_ratio = round(pg_disc_rate / mean_pg, 3) if (pg_disc_rate is not None and mean_pg) else None
        cal_p = binomial_two_sided_p(n_pg_disc, n_pg, mean_pg) if (n_pg and mean_pg) else None

        disc_pgs = [r["prospect"]["pg"] for r in pg_rows if r["is_discovery"]]
        dry_pgs = [r["prospect"]["pg"] for r in pg_rows if not r["is_discovery"]]

        pg_buckets = []
        for label, lo, hi in [("<10%", 0.0, 0.10), ("10-20%", 0.10, 0.20), ("20-30%", 0.20, 0.30), ("30-50%", 0.30, 0.50), (">=50%", 0.50, 1.01)]:
            sub = [r for r in pg_rows if lo <= r["prospect"]["pg"] < hi]
            if sub:
                sd = sum(1 for r in sub if r["is_discovery"])
                mp = sum(r["prospect"]["pg"] for r in sub) / len(sub)
                pg_buckets.append(
                    {
                        "bucket": label,
                        "n": len(sub),
                        "discoveries": sd,
                        "actual_rate": round(sd / len(sub), 4),
                        "mean_stated_pg": round(mp, 4),
                    }
                )

        unique_wells = list(well_hits.keys())
        unique_well_objs = [
            next(w for w in well_hits[wn][0]["matched_wells"] if w["wellbore_name"] == wn)
            for wn in unique_wells
        ]
        n_unique_wells = len(unique_well_objs)
        n_unique_wells_disc = sum(1 for w in unique_well_objs if w["is_discovery"])
        unique_discoveries = sorted(
            {w["discovery"] for w in unique_well_objs if w["is_discovery"] and w["discovery"]}
        )
        unique_fields = sorted(
            {w["field"] for w in unique_well_objs if w["is_discovery"] and w["field"]}
        )

        same_lin = [r for r in prospect_rows if r["same_operator_lineage"]]
        diff_lin = [r for r in prospect_rows if not r["same_operator_lineage"]]
        same_can = [r for r in prospect_rows if r["same_operator_canonical"]]
        diff_can = [r for r in prospect_rows if not r["same_operator_canonical"]]

        well_same_lin = 0
        well_same_lin_disc = 0
        well_diff_lin = 0
        well_diff_lin_disc = 0
        for wn, rows_for_w in well_hits.items():
            w_obj = next(w for w in rows_for_w[0]["matched_wells"] if w["wellbore_name"] == wn)
            any_same = any(
                same_operator_with_lundin(r["prospect"]["operator"], w_obj["operator"])
                for r in rows_for_w
            )
            if any_same:
                well_same_lin += 1
                if w_obj["is_discovery"]:
                    well_same_lin_disc += 1
            else:
                well_diff_lin += 1
                if w_obj["is_discovery"]:
                    well_diff_lin_disc += 1

        def op_stats(sub: list[dict[str, Any]]) -> dict[str, Any]:
            n = len(sub)
            d = sum(1 for r in sub if r["is_discovery"])
            f = sum(1 for r in sub if r["became_field"])
            pgs = [r["prospect"]["pg"] for r in sub if r["prospect"]["pg"] is not None]
            return {
                "n_prospects": n,
                "discoveries": d,
                "discovery_rate": round(d / n, 4) if n else None,
                "became_field": f,
                "mean_stated_pg": round(sum(pgs) / len(pgs), 4) if pgs else None,
            }

        by_layer = {}
        for lyr in ("prospect", "lead"):
            sub = [r for r in prospect_rows if r["feature_layer"] == lyr]
            by_layer[lyr] = op_stats(sub)

        return {
            "n_prospects_redrilled": n_pros,
            "n_prospects_discovered": n_disc,
            "prospect_discovery_rate": disc_rate,
            "n_prospects_became_field": n_field,
            "n_unique_wells": n_unique_wells,
            "n_unique_wells_discovery": n_unique_wells_disc,
            "unique_well_discovery_rate": round(n_unique_wells_disc / n_unique_wells, 4) if n_unique_wells else None,
            "n_unique_named_discoveries": len(unique_discoveries),
            "unique_named_discoveries": unique_discoveries,
            "n_unique_producing_fields": len(unique_fields),
            "unique_producing_fields": unique_fields,
            "pg_calibration": {
                "n_with_pg": n_pg,
                "n_discovered_with_pg": n_pg_disc,
                "actual_discovery_rate_with_pg": pg_disc_rate,
                "mean_stated_pg": mean_pg,
                "median_stated_pg": median_pg,
                "calibration_ratio_actual_over_stated": cal_ratio,
                "binomial_two_sided_p": cal_p,
                "mean_pg_of_discoveries": round(sum(disc_pgs) / len(disc_pgs), 4) if disc_pgs else None,
                "mean_pg_of_dry_holes": round(sum(dry_pgs) / len(dry_pgs), 4) if dry_pgs else None,
                "by_pg_bucket": pg_buckets,
            },
            "operator_comparison": {
                "lineage_normalized": {
                    "same_operator": op_stats(same_lin),
                    "different_operator": op_stats(diff_lin),
                    "z_test": two_proportion_z_test(
                        sum(1 for r in diff_lin if r["is_discovery"]),
                        len(diff_lin),
                        sum(1 for r in same_lin if r["is_discovery"]),
                        len(same_lin),
                    ),
                },
                "canonical_only": {
                    "same_operator": op_stats(same_can),
                    "different_operator": op_stats(diff_can),
                    "z_test": two_proportion_z_test(
                        sum(1 for r in diff_can if r["is_discovery"]),
                        len(diff_can),
                        sum(1 for r in same_can if r["is_discovery"]),
                        len(same_can),
                    ),
                },
                "unique_well_level_lineage": {
                    "same_operator": {
                        "n_wells": well_same_lin,
                        "discoveries": well_same_lin_disc,
                        "discovery_rate": round(well_same_lin_disc / well_same_lin, 4) if well_same_lin else None,
                    },
                    "different_operator": {
                        "n_wells": well_diff_lin,
                        "discoveries": well_diff_lin_disc,
                        "discovery_rate": round(well_diff_lin_disc / well_diff_lin, 4) if well_diff_lin else None,
                    },
                    "z_test": two_proportion_z_test(
                        well_diff_lin_disc,
                        well_diff_lin,
                        well_same_lin_disc,
                        well_same_lin,
                    ),
                },
            },
            "by_feature_layer": by_layer,
            "rows": prospect_rows,
        }

    all_matched_keys = list(prospect_well_matches.keys())
    undrilled_keys = [
        k for k in all_matched_keys if prospect_index[k]["status_at_report"] not in ALREADY_DRILLED_STATUSES
    ]
    non_disc_keys = [
        k for k in all_matched_keys if prospect_index[k]["status_at_report"] not in ALREADY_DISCOVERY_STATUSES
    ]
    drilled_dry_keys = [
        k for k in all_matched_keys if prospect_index[k]["status_at_report"] == "drilled_dry"
    ]

    summary_undrilled_wildcat = summarize_cohort(undrilled_keys, wildcat_only=True)
    summary_undrilled_all = summarize_cohort(undrilled_keys, wildcat_only=False)
    summary_non_disc_wildcat = summarize_cohort(non_disc_keys, wildcat_only=True)
    summary_drilled_dry_wildcat = summarize_cohort(drilled_dry_keys, wildcat_only=True)
    summary_all_all = summarize_cohort(all_matched_keys, wildcat_only=False)

    def risk_breakdown(rows: list[dict[str, Any]]) -> dict[str, Any]:
        disc_rows = [r for r in rows if r["is_discovery"]]
        dry_rows = [r for r in rows if not r["is_discovery"]]
        all_undrilled_atlas = [
            p for p in all_prospect_records if p["status_at_report"] not in ALREADY_DRILLED_STATUSES
        ]

        disc_risks = Counter(e for r in disc_rows for e in r["prospect"]["risk_elements"])
        dry_risks = Counter(e for r in dry_rows for e in r["prospect"]["risk_elements"])
        atlas_risks = Counter(e for p in all_undrilled_atlas for e in p["risk_elements"])

        disc_reasons = Counter(e for r in disc_rows for e in r["prospect"]["reasons_not_drilled"])
        dry_reasons = Counter(e for r in dry_rows for e in r["prospect"]["reasons_not_drilled"])
        atlas_reasons = Counter(e for p in all_undrilled_atlas for e in p["reasons_not_drilled"])

        n_d = len(disc_rows)
        n_f = len(dry_rows)
        n_a = len(all_undrilled_atlas)

        risk_table = []
        for elem, cnt_d in disc_risks.most_common(15):
            cnt_f = dry_risks[elem]
            cnt_a = atlas_risks[elem]
            tot_redrilled = cnt_d + cnt_f
            risk_table.append(
                {
                    "risk_element": elem,
                    "discovered_count": cnt_d,
                    "discovered_pct": round(cnt_d / n_d, 4) if n_d else 0.0,
                    "dry_count": cnt_f,
                    "dry_pct": round(cnt_f / n_f, 4) if n_f else 0.0,
                    "discovery_rate_when_cited": round(cnt_d / tot_redrilled, 4) if tot_redrilled else None,
                    "atlas_baseline_pct": round(cnt_a / n_a, 4) if n_a else 0.0,
                }
            )

        reason_table = []
        for rsn, cnt_d in disc_reasons.most_common(15):
            cnt_f = dry_reasons[rsn]
            cnt_a = atlas_reasons[rsn]
            tot_redrilled = cnt_d + cnt_f
            reason_table.append(
                {
                    "reason_not_drilled": rsn,
                    "discovered_count": cnt_d,
                    "discovered_pct": round(cnt_d / n_d, 4) if n_d else 0.0,
                    "dry_count": cnt_f,
                    "dry_pct": round(cnt_f / n_f, 4) if n_f else 0.0,
                    "discovery_rate_when_cited": round(cnt_d / tot_redrilled, 4) if tot_redrilled else None,
                    "atlas_baseline_pct": round(cnt_a / n_a, 4) if n_a else 0.0,
                }
            )

        return {
            "n_discovered": n_d,
            "n_dry": n_f,
            "n_atlas_undrilled": n_a,
            "key_risk_elements": risk_table,
            "reasons_not_drilled": reason_table,
        }

    risk_analysis = risk_breakdown(summary_undrilled_wildcat["rows"])

    disc_candidates = [
        r for r in summary_undrilled_wildcat["rows"] if r["is_discovery"]
    ]
    by_discovery_best: dict[str, dict[str, Any]] = {}
    for r in disc_candidates:
        w = r["first_discovery_well"]
        dkey = w["discovery"] or w["wellbore_name"]
        area_km2 = r["feature_area_km2"] or 9999.0
        is_tight = 1 if area_km2 <= 150.0 else 0
        score = (
            1 if w["field"] else 0,
            1 if w["discovery_wellbore"] else 0,
            is_tight,
            1 if r["feature_layer"] == "prospect" else 0,
            -area_km2,
            r["prospect"]["mean_msmo3"] or 0.0,
        )
        prev = by_discovery_best.get(dkey)
        if prev is None or score > prev["score"]:
            by_discovery_best[dkey] = {"score": score, "row": r}

    ranked_got_away = sorted(
        [v["row"] for v in by_discovery_best.values()],
        key=lambda r: (
            1 if r["became_field"] else 0,
            1 if r["first_discovery_well"]["discovery_wellbore"] else 0,
            r["prospect"]["mean_msmo3"] or 0.0,
            len(r["matched_wells"]),
        ),
        reverse=True,
    )

    def format_case(r: dict[str, Any]) -> dict[str, Any]:
        p = r["prospect"]
        w = r["first_discovery_well"]
        return {
            "prospect_name": p["name"],
            "prospect_id": p["prospect_id"],
            "classification": p["classification"],
            "feature_layer": r["feature_layer"],
            "feature_area_km2": r["feature_area_km2"],
            "status_at_report": p["status_at_report"],
            "relinquishing_licence": p["licence_id"],
            "relinquishing_operator": p["operator"],
            "relinquishing_operator_canonical": p["operator_canonical"],
            "relinquishment_year": p["report_year"],
            "area": p["area"],
            "pre_relinquishment_pg": p["pg"],
            "pre_relinquishment_mean_msmo3": p["mean_msmo3"],
            "pre_relinquishment_mean_mmboe": p["mean_mmboe"],
            "reasons_not_drilled": p["reasons_not_drilled"],
            "risk_elements": p["risk_elements"],
            "key_risks": p["key_risks"][:3],
            "conclusion_text": p["conclusion_text"],
            "later_discovery_well": w["wellbore_name"],
            "later_operator": w["operator"],
            "later_operator_canonical": w["operator_canonical"],
            "later_licence": w["licence"],
            "later_year": w["completion_year"],
            "years_after_relinquishment": r["years_after_relinquishment"],
            "same_operator_lineage": r["same_operator_lineage"],
            "discovery_name": w["discovery"],
            "discovery_wellbore_flag": w["discovery_wellbore"],
            "content": w["content"],
            "field": w["field"],
            "hc_formation": w["hc_fm1"],
            "hc_age": w["hc_age1"],
            "all_later_wildcat_wells": [
                {
                    "wellbore": mw["wellbore_name"],
                    "year": mw["completion_year"],
                    "operator": mw["operator"],
                    "content": mw["content"],
                    "discovery": mw["discovery"],
                    "field": mw["field"],
                }
                for mw in r["matched_wells"]
            ],
        }

    top_25_got_away = [format_case(r) for r in ranked_got_away[:25]]
    drilled_dry_resurrections = [
        format_case(r)
        for r in summary_drilled_dry_wildcat["rows"]
        if r["is_discovery"]
    ]

    output = {
        "dataset_summary": {
            "raw_reports": len(raw_json),
            "deduplicated_reports": len(kept_json),
            "dropped_duplicate_reports": len(dropped_stems),
            "total_prospects_in_atlas": len(all_prospect_records),
            "prospects_with_polygon_geometry": len(prospects_with_polygons),
            "polygon_features_checked": len(polygon_features),
            "unmatched_polygon_features": unmatched_geo_features,
            "sodir_completed_exploration_wells": len(wells),
            "raw_feature_well_post_relinq_hits": raw_feature_well_hits,
            "internal_qc_flag_sodir_well_mentions": len(internal_qc_post_relinq),
        },
        "cohorts": {
            "primary_undrilled_wildcat": {k: v for k, v in summary_undrilled_wildcat.items() if k != "rows"},
            "undrilled_all_exploration_wells": {k: v for k, v in summary_undrilled_all.items() if k != "rows"},
            "non_discovery_incl_drilled_dry_wildcat": {k: v for k, v in summary_non_disc_wildcat.items() if k != "rows"},
            "previously_drilled_dry_wildcat": {k: v for k, v in summary_drilled_dry_wildcat.items() if k != "rows"},
            "all_prospects_all_exploration_wells": {k: v for k, v in summary_all_all.items() if k != "rows"},
        },
        "risk_factor_analysis_undrilled_wildcat": risk_analysis,
        "top_25_ones_that_got_away": top_25_got_away,
        "drilled_dry_then_discovered_resurrections": drilled_dry_resurrections,
    }

    out_json = OUT_DIR / "track1_findings.json"
    out_json.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== DATASET SUMMARY ===")
    print(json.dumps(output["dataset_summary"], indent=2))
    print("\n=== PRIMARY COHORT: UNDRILLED RELINQUISHED PROSPECTS/LEADS -> LATER WILDCAT WELLS ===")
    print(json.dumps(output["cohorts"]["primary_undrilled_wildcat"], indent=2))
    print("\n=== UNDRILLED -> ALL EXPLORATION WELLS (WILDCAT + APPRAISAL) ===")
    p_all = output["cohorts"]["undrilled_all_exploration_wells"]
    print(json.dumps({k: v for k, v in p_all.items() if k not in ("unique_named_discoveries", "unique_producing_fields")}, indent=2))
    print("\n=== PREVIOUSLY DRILLED DRY -> LATER WILDCAT WELLS ===")
    print(json.dumps({k: v for k, v in output["cohorts"]["previously_drilled_dry_wildcat"].items() if k not in ("unique_named_discoveries", "unique_producing_fields")}, indent=2))
    print("\n=== RISK FACTORS ON DISCOVERIES VS DRY HOLES ===")
    print(json.dumps(risk_analysis["key_risk_elements"][:10], indent=2))
    print("\n=== REASONS NOT DRILLED ON DISCOVERIES VS DRY HOLES ===")
    print(json.dumps(risk_analysis["reasons_not_drilled"][:10], indent=2))
    print("\n=== TOP 20 ONES THAT GOT AWAY ===")
    for i, c in enumerate(top_25_got_away[:20], 1):
        print(
            f"{i:2d}. {c['prospect_name']} ({c['relinquishing_licence']}, {c['relinquishing_operator']}, {c['relinquishment_year']}) "
            f"[layer={c['feature_layer']}, area={c['feature_area_km2']} km2, Pg={c['pre_relinquishment_pg']}, Vol={c['pre_relinquishment_mean_msmo3']} MSm3/{c['pre_relinquishment_mean_mmboe']} MMboe] "
            f"-> {c['later_discovery_well']} ({c['later_operator']}, {c['later_year']}) | {c['content']} | Disc={c['discovery_name']} | Field={c['field']} | DiscWell={c['discovery_wellbore_flag']}"
        )
    print("\n=== DRILLED DRY -> LATER DISCOVERED ===")
    for i, c in enumerate(drilled_dry_resurrections, 1):
        print(
            f"{i:2d}. {c['prospect_name']} ({c['relinquishing_licence']}, {c['relinquishing_operator']}, {c['relinquishment_year']}) "
            f"-> {c['later_discovery_well']} ({c['later_operator']}, {c['later_year']}) | {c['content']} | Disc={c['discovery_name']} | Field={c['field']}"
        )


if __name__ == "__main__":
    main()
