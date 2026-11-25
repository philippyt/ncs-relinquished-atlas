import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import httpx
import polars as pl

ROOT = Path(r"C:\Users\philip\Documents\ncs-relinquished-atlas")
sys.path.insert(0, str(ROOT / "src"))

from loader import (
    DEFAULT_FACTPAGES_WELLS,
    deduplicate_records,
    load_raw_records,
    safe_canonical_volume_msmo3,
)

CACHE = ROOT / "data" / "sodir"
CACHE.mkdir(parents=True, exist_ok=True)
OUT_JSON = ROOT / "analyses" / "track5_findings.json"
OUT_MD = ROOT / "analyses" / "track5_findings.md"


def pip_ring(px: float, py: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def pip_geom(px: float, py: float, geom: dict) -> bool:
    if not geom or not geom.get("coordinates"):
        return False
    gt = geom.get("type")
    cs = geom["coordinates"]
    if gt == "Polygon":
        return pip_ring(px, py, cs[0]) and not any(pip_ring(px, py, h) for h in cs[1:])
    if gt == "MultiPolygon":
        return any(pip_ring(px, py, p[0]) and not any(pip_ring(px, py, h) for h in p[1:]) for p in cs)
    return False


def geom_bbox(geom: dict) -> tuple[float, float, float, float] | None:
    if not geom or not geom.get("coordinates"):
        return None
    gt = geom.get("type")
    cs = geom["coordinates"]
    if gt == "Polygon":
        pts = cs[0]
    elif gt == "MultiPolygon":
        pts = [pt for p in cs for pt in p[0]]
    elif gt == "Point":
        pts = [cs]
    else:
        return None
    xs = [p[0] for p in pts if len(p) >= 2]
    ys = [p[1] for p in pts if len(p) >= 2]
    if not xs:
        return None
    return min(xs), max(xs), min(ys), max(ys)


def geom_centroid(geom: dict) -> tuple[float, float] | None:
    if not geom or not geom.get("coordinates"):
        return None
    gt = geom.get("type")
    cs = geom["coordinates"]
    if gt == "Point":
        return float(cs[0]), float(cs[1])
    if gt == "Polygon":
        pts = cs[0]
    elif gt == "MultiPolygon":
        pts = max((p[0] for p in cs if p), key=len, default=[])
    else:
        return None
    xs = [p[0] for p in pts if len(p) >= 2]
    ys = [p[1] for p in pts if len(p) >= 2]
    if not xs:
        return None
    return sum(xs) / len(xs), sum(ys) / len(ys)


def norm_period(text: str | None) -> str | None:
    if not text:
        return None
    t = str(text).lower()
    for p in ("paleogene", "neogene", "tertiary", "cretaceous", "jurassic", "triassic", "permian", "carboniferous", "devonian", "basement", "pre-devonian"):
        if p in t:
            return "paleogene" if p in ("paleogene", "tertiary", "neogene") else p
    if "paleocene" in t or "eocene" in t or "oligocene" in t or "miocene" in t:
        return "paleogene"
    return None


def fetch_active_licences_geojson() -> list[dict]:
    path = CACHE / "active_licences_616.geojson"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")).get("features") or []
    url = "https://factmaps.sodir.no/api/rest/services/FactMaps/FactMapsWGS84/MapServer/616/query"
    features = []
    offset = 0
    with httpx.Client(timeout=60.0, follow_redirects=True) as c:
        while True:
            r = c.get(
                url,
                params={
                    "where": "1=1",
                    "outFields": "prlName,cmpLongName,prlMainArea,prlStatus",
                    "outSR": "4326",
                    "f": "geojson",
                    "resultOffset": offset,
                    "resultRecordCount": 500,
                },
            )
            r.raise_for_status()
            js = r.json()
            batch = js.get("features") or []
            features.extend(batch)
            if len(batch) < 500:
                break
            offset += len(batch)
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    return features


def build_prospect_feature_maps(
    kept_json: dict, kept_geo: dict
) -> tuple[dict[tuple[str, str], dict], dict[str, list[dict]]]:
    feat_to_prospect: dict[tuple[str, str], dict] = {}
    pid_to_features: dict[str, list[dict]] = defaultdict(list)
    for stem, rec in kept_json.items():
        by_name: dict[str, dict] = {}
        by_fid: dict[str, dict] = {}
        for p in rec.get("prospects") or []:
            nm = str(p.get("name") or "").strip().lower()
            if nm:
                by_name[nm] = p
            lf = (p.get("_derived") or {}).get("linked_features")
            if isinstance(lf, dict):
                for fid in lf.get("feature_ids") or lf.get("values") or []:
                    by_fid[str(fid)] = p
            elif isinstance(lf, list):
                for fid in lf:
                    by_fid[str(fid)] = p
        gj = kept_geo.get(stem) or {}
        for feat in gj.get("features") or []:
            props = feat.get("properties") or {}
            if props.get("layer") not in ("prospect", "lead"):
                continue
            fid = str(props.get("feature_id") or feat.get("id") or "")
            pnm = str(props.get("prospect_name") or props.get("label") or "").strip().lower()
            pobj = by_fid.get(fid) or by_name.get(pnm)
            if pobj is None and props.get("prospect_uid"):
                tail = str(props["prospect_uid"]).split(":")[-1].lower().replace("_", " ")
                pobj = by_name.get(tail)
            if pobj is not None:
                feat_to_prospect[(stem, fid)] = pobj
                pid = pobj.get("prospect_id")
                if pid:
                    pid_to_features[pid].append(feat)
    return feat_to_prospect, pid_to_features


def run_test1_unique_well_vs_shelf(
    kept_json: dict,
    kept_geo: dict,
    wells_df: pl.DataFrame,
    feat_to_prospect: dict[tuple[str, str], dict],
) -> dict:
    wc = (
        wells_df.filter(pl.col("wlbPurpose").str.to_uppercase() == "WILDCAT")
        .filter(pl.col("wlbCompletionYear").is_not_null())
        .with_columns(
            (
                pl.col("wlbContent").fill_null("").str.to_uppercase().str.contains("OIL|GAS|COND")
                & ~pl.col("wlbContent").fill_null("").str.to_uppercase().str.contains("SHOW")
            ).alias("is_disc")
        )
    )
    shelf_by_year = {}
    for row in wc.group_by("wlbCompletionYear").agg([pl.len().alias("n"), pl.col("is_disc").sum().alias("d")]).iter_rows(named=True):
        shelf_by_year[int(row["wlbCompletionYear"])] = (int(row["d"]), int(row["n"]))

    wildcats = wc.drop_nulls(subset=["wlbEwDecDeg", "wlbNsDecDeg"]).to_dicts()
    well_hits: dict[str, list[dict]] = defaultdict(list)

    for stem, rec in kept_json.items():
        rdate = str((rec.get("document") or {}).get("date") or "")
        if len(rdate) < 4 or not rdate[:4].isdigit():
            continue
        ryear = int(rdate[:4])
        pmap = {p.get("prospect_id"): p for p in (rec.get("prospects") or [])}
        gj = kept_geo.get(stem) or {}
        for feat in gj.get("features") or []:
            props = feat.get("properties") or {}
            geom = feat.get("geometry")
            if props.get("layer") not in ("prospect", "lead") or not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
                continue
            fid = str(props.get("feature_id") or feat.get("id") or "")
            pobj = feat_to_prospect.get((stem, fid)) or {}
            pid = pobj.get("prospect_id") or props.get("prospect_uid")
            status = str(pobj.get("status_at_report") or "").lower()
            if any(k in status for k in ("drilled", "discovery", "dry")):
                continue
            bb = geom_bbox(geom)
            if not bb:
                continue
            minx, maxx, miny, maxy = bb
            p_periods = set()
            for t in pobj.get("targets") or []:
                per = norm_period(((t.get("reservoir") or {}).get("chrono") or {}).get("period"))
                if per:
                    p_periods.add(per)
            for w in wildcats:
                if int(w["wlbCompletionYear"]) <= ryear:
                    continue
                wx, wy = float(w["wlbEwDecDeg"]), float(w["wlbNsDecDeg"])
                if not (minx <= wx <= maxx and miny <= wy <= maxy):
                    continue
                if pip_geom(wx, wy, geom):
                    w_ages = set()
                    for col in ("wlbAgeWithHc1", "wlbAgeWithHc2", "wlbAgeWithHc3", "wlbAgeAtTd"):
                        ap = norm_period(w.get(col))
                        if ap:
                            w_ages.add(ap)
                    strat_match = bool(p_periods & w_ages) if (p_periods and w_ages) else None
                    wname = str(w["wlbWellboreName"])
                    is_deviated = bool(re.search(r"\s+[A-Z]\d*$|T\d+$", wname.strip()))
                    well_hits[wname].append(
                        {
                            "well": wname,
                            "year": int(w["wlbCompletionYear"]),
                            "is_disc": bool(w["is_disc"]),
                            "is_deviated": is_deviated,
                            "strat_match": strat_match,
                            "area_km2": props.get("area_km2_geometry"),
                            "prospect_id": pid,
                            "field": w.get("wlbField"),
                            "discovery": w.get("wlbDiscovery"),
                        }
                    )

    unique_wells = []
    for wname, hits in well_hits.items():
        any_strat = any(h["strat_match"] is True for h in hits)
        known_strat = any(h["strat_match"] is not None for h in hits)
        min_area = min((h["area_km2"] for h in hits if isinstance(h["area_km2"], (int, float))), default=None)
        unique_wells.append(
            {
                "well": wname,
                "year": hits[0]["year"],
                "is_disc": hits[0]["is_disc"],
                "is_deviated": hits[0]["is_deviated"],
                "strat_match": True if any_strat else (False if known_strat else None),
                "min_area_km2": min_area,
                "n_overlapping_polygons": len(hits),
                "field": hits[0]["field"],
                "discovery": hits[0]["discovery"],
            }
        )

    def summarize(sub: list[dict]) -> dict:
        n = len(sub)
        d = sum(1 for x in sub if x["is_disc"])
        exp_shelf = 0.0
        for x in sub:
            sd, sn = shelf_by_year.get(x["year"], (0, 0))
            if sn > 0:
                exp_shelf += sd / sn
        shelf_rate = (exp_shelf / n) if n else 0.0
        obs_rate = (d / n) if n else 0.0
        se = math.sqrt(shelf_rate * (1 - shelf_rate) / n) if n else 1.0
        z = (obs_rate - shelf_rate) / se if se > 0 else 0.0
        return {
            "n_unique_wells": n,
            "discoveries": d,
            "observed_rate_pct": round(obs_rate * 100, 1),
            "year_matched_shelf_baseline_pct": round(shelf_rate * 100, 1),
            "diff_vs_shelf_pp": round((obs_rate - shelf_rate) * 100, 1),
            "z_vs_shelf": round(z, 2),
        }

    return {
        "all_unique_redrill_wildcats": summarize(unique_wells),
        "vertical_only_wildcats": summarize([w for w in unique_wells if not w["is_deviated"]]),
        "deviated_or_sidetrack_wildcats": summarize([w for w in unique_wells if w["is_deviated"]]),
        "stratigraphic_age_matched_wildcats": summarize([w for w in unique_wells if w["strat_match"] is True]),
        "tight_polygon_le50km2_unique_wells": summarize([w for w in unique_wells if w["min_area_km2"] is not None and w["min_area_km2"] <= 50.0]),
        "vertical_and_tight_and_strat_matched": summarize([w for w in unique_wells if not w["is_deviated"] and w["strat_match"] is True and w["min_area_km2"] is not None and w["min_area_km2"] <= 50.0]),
        "polygon_overlap_inflation": {
            "total_polygon_hits": sum(w["n_overlapping_polygons"] for w in unique_wells),
            "unique_wells": len(unique_wells),
            "wells_with_gt1_polygon": sum(1 for w in unique_wells if w["n_overlapping_polygons"] > 1),
        },
    }


def run_test2_p90_p10_coverage(
    kept_json: dict,
    kept_geo: dict,
    wells_df: pl.DataFrame,
    feat_to_prospect: dict[tuple[str, str], dict],
) -> dict:
    disc_df = pl.read_parquet(CACHE / "discovery.parquet")
    disc_res = pl.read_parquet(CACHE / "discovery_reserves.parquet")
    fld_res = pl.read_parquet(CACHE / "field_reserves.parquet")

    latest_fld = (
        fld_res.sort("fldVersion", descending=True)
        .unique(subset=["fldName"], keep="first")
        .select(["fldName", "fldRecoverableOE"])
    )
    fld_oe = {r["fldName"]: float(r["fldRecoverableOE"]) for r in latest_fld.drop_nulls().iter_rows(named=True)}
    dsc_oe = {r["dscName"]: float(r["dscRecoverableOe"]) for r in disc_res.select(["dscName", "dscRecoverableOe"]).drop_nulls().iter_rows(named=True)}

    well_to_actual_oe: dict[str, tuple[float, str, str]] = {}
    for r in disc_df.iter_rows(named=True):
        wn = r.get("wlbName")
        dn = r.get("dscName")
        fn = r.get("fldName")
        if not wn:
            continue
        if dn in dsc_oe and dsc_oe[dn] > 0:
            well_to_actual_oe[wn] = (dsc_oe[dn], "discovery_reserves", dn)
        elif fn in fld_oe and fld_oe[fn] > 0:
            well_to_actual_oe[wn] = (fld_oe[fn], "field_reserves", f"{dn} ({fn})")

    wells_coords = wells_df.select(["wlbWellboreName", "wlbEwDecDeg", "wlbNsDecDeg", "wlbCompletionYear", "wlbPurpose", "wlbDiscovery"]).drop_nulls(subset=["wlbEwDecDeg", "wlbNsDecDeg"]).to_dicts()
    disc_wells_with_vol = [w for w in wells_coords if w["wlbWellboreName"] in well_to_actual_oe]

    def extract_p90_p10_mean(pobj: dict) -> tuple[float | None, float | None, float | None, str | None]:
        for a in pobj.get("assessments") or []:
            stage = str(a.get("stage") or "").lower()
            if "post" in stage:
                continue
            vols = a.get("volumes") or []
            oe_vols = [v for v in vols if v.get("phase") in ("oil_equivalent", "total_hc") and v.get("basis") == "recoverable"]
            if not oe_vols:
                oe_vols = [v for v in vols if v.get("basis") == "recoverable"]
            for v in oe_vols:
                p90 = safe_canonical_volume_msmo3(v, "p90")
                p10 = safe_canonical_volume_msmo3(v, "p10")
                mean = safe_canonical_volume_msmo3(v, "mean")
                if p90 is not None and p10 is not None and p10 > p90 > 0:
                    return p90, p10, mean, stage
        return None, None, None, None

    matched_cases = []
    seen_wells = set()
    for stem, rec in kept_json.items():
        pmap = {p.get("prospect_id"): p for p in (rec.get("prospects") or [])}
        gj = kept_geo.get(stem) or {}
        for feat in gj.get("features") or []:
            props = feat.get("properties") or {}
            geom = feat.get("geometry")
            if props.get("layer") not in ("prospect", "lead") or not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
                continue
            area = props.get("area_km2_geometry")
            if isinstance(area, (int, float)) and area > 100.0:
                continue
            fid = str(props.get("feature_id") or feat.get("id") or "")
            pobj = feat_to_prospect.get((stem, fid)) or {}
            pid = pobj.get("prospect_id") or props.get("prospect_uid")
            p90, p10, mean, stage = extract_p90_p10_mean(pobj)
            if p90 is None or p10 is None:
                continue
            bb = geom_bbox(geom)
            if not bb:
                continue
            minx, maxx, miny, maxy = bb
            for w in disc_wells_with_vol:
                wn = w["wlbWellboreName"]
                if wn in seen_wells:
                    continue
                wx, wy = float(w["wlbEwDecDeg"]), float(w["wlbNsDecDeg"])
                if not (minx <= wx <= maxx and miny <= wy <= maxy):
                    continue
                if pip_geom(wx, wy, geom):
                    act_oe, src_tbl, dname = well_to_actual_oe[wn]
                    seen_wells.add(wn)
                    loc = "below_p90" if act_oe < p90 else ("above_p10" if act_oe > p10 else "inside_p90_p10")
                    matched_cases.append(
                        {
                            "well": wn,
                            "discovery": dname,
                            "source_table": src_tbl,
                            "prospect_id": pid,
                            "prospect_name": pobj.get("name"),
                            "stage": stage,
                            "p90_msmo3": round(p90, 3),
                            "mean_msmo3": round(mean, 3) if mean else None,
                            "p10_msmo3": round(p10, 3),
                            "p10_p90_ratio": round(p10 / p90, 2),
                            "actual_sodir_oe_msmo3": round(act_oe, 3),
                            "position": loc,
                            "actual_to_mean_ratio": round(act_oe / mean, 2) if mean else None,
                        }
                    )

    def summarize_cov(cases: list[dict]) -> dict:
        n = len(cases)
        if n == 0:
            return {"n": 0}
        below = sum(1 for c in cases if c["position"] == "below_p90")
        inside = sum(1 for c in cases if c["position"] == "inside_p90_p10")
        above = sum(1 for c in cases if c["position"] == "above_p10")
        outside = below + above
        ratios = sorted(c["p10_p90_ratio"] for c in cases)
        med_ratio = ratios[n // 2]
        m_ratios = sorted(c["actual_to_mean_ratio"] for c in cases if c["actual_to_mean_ratio"] is not None)
        med_act_mean = m_ratios[len(m_ratios) // 2] if m_ratios else None
        return {
            "n": n,
            "inside_p90_p10_count": inside,
            "inside_p90_p10_pct": round(100 * inside / n, 1),
            "outside_p90_p10_count": outside,
            "outside_p90_p10_pct": round(100 * outside / n, 1),
            "expected_outside_pct": 20.0,
            "below_p90_count": below,
            "below_p90_pct": round(100 * below / n, 1),
            "above_p10_count": above,
            "above_p10_pct": round(100 * above / n, 1),
            "median_p10_p90_ratio": med_ratio,
            "median_actual_to_pre_drill_mean": med_act_mean,
        }

    disc_only = [c for c in matched_cases if c["source_table"] == "discovery_reserves"]
    return {
        "all_matched_discoveries": summarize_cov(matched_cases),
        "standalone_discovery_reserves_only": summarize_cov(disc_only),
        "cases": sorted(matched_cases, key=lambda x: x["actual_sodir_oe_msmo3"], reverse=True),
    }


def run_test3_open_acreage_screen(
    kept_json: dict,
    kept_geo: dict,
    active_lic_feats: list[dict],
    pid_to_features: dict[str, list[dict]],
) -> dict:
    t3 = json.loads((ROOT / "analyses" / "track3_findings.json").read_text(encoding="utf-8"))
    active_polys = []
    for f in active_lic_feats:
        g = f.get("geometry")
        bb = geom_bbox(g)
        if bb:
            props = f.get("properties") or {}
            active_polys.append((bb, g, props.get("prlName"), props.get("cmpLongName")))

    prospect_centroids: dict[str, tuple[float, float]] = {}
    for pid, feats in pid_to_features.items():
        for feat in feats:
            c = geom_centroid(feat.get("geometry"))
            if c:
                prospect_centroids[pid] = c
                break

    t3_top = t3["track3_part3_untested_prize"]["top_15_post_award_comm_nt_pg20"]
    checked_top = []
    for row in t3_top:
        pid = row.get("prospect_id")
        pt = prospect_centroids.get(pid)
        active_hit = None
        if pt:
            px, py = pt
            for (minx, maxx, miny, maxy), g, prl, op in active_polys:
                if minx <= px <= maxx and miny <= py <= maxy and pip_geom(px, py, g):
                    active_hit = {"active_licence": prl, "active_operator": op}
                    break
        checked_top.append(
            {
                "prospect_id": pid,
                "name": row.get("name"),
                "basin": row.get("basin"),
                "pg": row.get("pg"),
                "risked_mmboe": row.get("risked_mmboe"),
                "unrisked_mmboe": row.get("unrisked_mmboe"),
                "has_geometry": pt is not None,
                "acreage_status": "RE_LICENSED" if active_hit else ("OPEN_ACREAGE" if pt else "NO_GEOMETRY"),
                "active_licence": active_hit["active_licence"] if active_hit else None,
                "active_operator": active_hit["active_operator"] if active_hit else None,
            }
        )

    open_n, relic_n, nogeo_n = 0, 0, 0
    open_risked_msmo3, relic_risked_msmo3 = 0.0, 0.0
    all_open_pg20 = []

    for rec in kept_json.values():
        basin = (rec.get("licence") or {}).get("area") or "Unknown"
        lic_id = (rec.get("licence") or {}).get("licence_id")
        op = (rec.get("document") or {}).get("author_company")
        rdate = str((rec.get("document") or {}).get("date") or "")[:4]
        for p in rec.get("prospects") or []:
            status = str(p.get("status_at_report") or "").lower()
            if any(k in status for k in ("drilled", "discovery", "dry")):
                continue
            ass = p.get("assessments") or []
            if not ass:
                continue
            fin = ass[-1]
            pg = (fin.get("risk") or {}).get("pg")
            if not isinstance(pg, (int, float)) or pg < 0.20 or pg >= 0.99:
                continue
            vols = [v for v in (fin.get("volumes") or []) if v.get("basis") == "recoverable"]
            oe = [v for v in vols if v.get("phase") in ("oil_equivalent", "total_hc")] or vols
            mvals = [safe_canonical_volume_msmo3(v, "mean") for v in oe]
            mvals = [x for x in mvals if x is not None and x > 0]
            if not mvals:
                continue
            mean_v = max(mvals)
            risked_v = pg * mean_v
            pid = p.get("prospect_id")
            pt = prospect_centroids.get(pid)
            if not pt:
                nogeo_n += 1
                continue
            px, py = pt
            hit = None
            for (minx, maxx, miny, maxy), g, prl, aop in active_polys:
                if minx <= px <= maxx and miny <= py <= maxy and pip_geom(px, py, g):
                    hit = (prl, aop)
                    break
            if hit:
                relic_n += 1
                relic_risked_msmo3 += risked_v
            else:
                open_n += 1
                open_risked_msmo3 += risked_v
                all_open_pg20.append(
                    {
                        "prospect_id": pid,
                        "name": p.get("name"),
                        "licence": lic_id,
                        "relinq_year": rdate,
                        "operator": op,
                        "basin": basin,
                        "pg": round(pg, 3),
                        "mean_msmo3": round(mean_v, 2),
                        "risked_msmo3": round(risked_v, 2),
                        "risked_mmboe": round(risked_v * 6.2898, 1),
                        "lon": round(px, 4),
                        "lat": round(py, 4),
                    }
                )

    all_open_pg20.sort(key=lambda x: x["risked_msmo3"], reverse=True)
    return {
        "n_active_sodir_licences_loaded": len(active_polys),
        "all_undrilled_pg_ge_020_screen": {
            "open_acreage_count": open_n,
            "open_acreage_risked_msmo3": round(open_risked_msmo3, 1),
            "open_acreage_risked_bboe": round(open_risked_msmo3 * 6.2898 / 1000.0, 2),
            "re_licensed_count": relic_n,
            "re_licensed_risked_msmo3": round(relic_risked_msmo3, 1),
            "re_licensed_risked_bboe": round(relic_risked_msmo3 * 6.2898 / 1000.0, 2),
            "no_geometry_count": nogeo_n,
            "open_share_of_georeferenced_pct": round(100 * open_n / max(1, open_n + relic_n), 1),
        },
        "top_15_track3_prize_status": checked_top,
        "top_15_open_acreage_undrilled_pg20": all_open_pg20[:15],
    }


def main() -> None:
    raw_json, raw_geo = load_raw_records()
    kept_json, kept_geo, _ = deduplicate_records(raw_json, raw_geo)
    wells_df = pl.read_parquet(DEFAULT_FACTPAGES_WELLS)
    active_lics = fetch_active_licences_geojson()

    feat_to_prospect, pid_to_features = build_prospect_feature_maps(kept_json, kept_geo)

    t1_up = run_test1_unique_well_vs_shelf(kept_json, kept_geo, wells_df, feat_to_prospect)
    t2_up = run_test2_p90_p10_coverage(kept_json, kept_geo, wells_df, feat_to_prospect)
    t3_up = run_test3_open_acreage_screen(kept_json, kept_geo, active_lics, pid_to_features)

    out = {
        "test1_unique_well_vs_shelf_baseline": t1_up,
        "test2_p90_p10_volume_coverage": t2_up,
        "test3_current_open_acreage_screen": t3_up,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("=== TEST 1: UNIQUE WELL REDRILLS VS YEAR-MATCHED SHELF BASELINE ===")
    print(json.dumps(t1_up, indent=2))
    print("\n=== TEST 2: P90-P10 VOLUME COVERAGE VS SODIR ACTUALS ===")
    print(json.dumps({k: v for k, v in t2_up.items() if k != "cases"}, indent=2))
    print("Top 8 matched P90-P10 cases:")
    for c in t2_up["cases"][:8]:
        print(" ", c)
    print("\n=== TEST 3: CURRENT ACTIVE LICENCE / OPEN ACREAGE SCREEN ===")
    print(json.dumps({k: v for k, v in t3_up.items() if k != "top_15_open_acreage_undrilled_pg20"}, indent=2))
    print("\nTop 10 OPEN ACREAGE undrilled Pg>=0.20 prospects:")
    for c in t3_up["top_15_open_acreage_undrilled_pg20"][:10]:
        print(" ", c)


if __name__ == "__main__":
    main()
