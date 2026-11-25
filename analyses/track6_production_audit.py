import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

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
FT_PATH = Path(r"C:\Users\philip\Documents\wellbore-completion\data\factpages\wellbore_formation_top.parquet")
OUT_JSON = ROOT / "analyses" / "track6_findings.json"


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


def sample_polygon_points(geom: dict, grid_n: int = 7) -> list[tuple[float, float]]:
    if not geom or not geom.get("coordinates"):
        return []
    gt = geom.get("type")
    if gt == "Point":
        c = geom["coordinates"]
        return [(float(c[0]), float(c[1]))]
    bb = geom_bbox(geom)
    if not bb:
        return []
    minx, maxx, miny, maxy = bb
    pts = []
    if maxx > minx and maxy > miny:
        for ix in range(grid_n):
            px = minx + (ix + 0.5) * (maxx - minx) / grid_n
            for iy in range(grid_n):
                py = miny + (iy + 0.5) * (maxy - miny) / grid_n
                if pip_geom(px, py, geom):
                    pts.append((px, py))
    if not pts:
        c = geom_centroid(geom)
        if c:
            pts.append(c)
    return pts


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def norm_period(text: str | None) -> str | None:
    if not text:
        return None
    t = str(text).lower()
    for p in ("paleogene", "neogene", "tertiary", "cretaceous", "jurassic", "triassic", "permian", "carboniferous", "devonian", "basement", "pre-devonian"):
        if p in t:
            return "paleogene" if p in ("paleogene", "tertiary", "neogene") else p
    if any(k in t for k in ("paleocene", "eocene", "oligocene", "miocene", "pliocene", "danian")):
        return "paleogene"
    return None


def build_unit_to_period() -> dict[str, str]:
    strat = pl.read_parquet(CACHE / "strat_litho_overview.parquet")
    mapping: dict[str, str] = {}
    for r in strat.iter_rows(named=True):
        nm = str(r.get("lsuName") or "").strip().upper()
        desc = str(r.get("lsuDescription") or "")
        per = norm_period(desc[:600])
        if nm and per:
            mapping[nm] = per
    return mapping


def build_well_penetrated_periods(unit_to_period: dict[str, str]) -> dict[str, set[str]]:
    ft = pl.read_parquet(FT_PATH)
    well_periods: dict[str, set[str]] = defaultdict(set)
    for r in ft.select(["wlbName", "lsuName", "lsuNameParent"]).iter_rows(named=True):
        wn = r.get("wlbName")
        if not wn:
            continue
        for col in ("lsuName", "lsuNameParent"):
            u = str(r.get(col) or "").strip().upper()
            if u in unit_to_period:
                well_periods[wn].add(unit_to_period[u])
    return well_periods


def build_prospect_feature_maps(kept_json: dict, kept_geo: dict) -> tuple[dict[tuple[str, str], dict], dict[str, list[dict]]]:
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


def run_parent_well_redrill_audit(
    kept_json: dict,
    kept_geo: dict,
    wells_df: pl.DataFrame,
    feat_to_prospect: dict[tuple[str, str], dict],
    well_periods: dict[str, set[str]],
) -> tuple[dict, set[str]]:
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

    parent_shelf: dict[str, dict] = {}
    for row in wc.select(["wlbWell", "wlbWellboreName", "wlbMainArea", "wlbCompletionYear", "is_disc"]).iter_rows(named=True):
        pw = str(row["wlbWell"] or row["wlbWellboreName"]).strip()
        yr = int(row["wlbCompletionYear"])
        area = str(row["wlbMainArea"] or "UNKNOWN").strip().upper()
        disc = bool(row["is_disc"])
        if pw not in parent_shelf:
            parent_shelf[pw] = {"year": yr, "area": area, "is_disc": disc}
        else:
            parent_shelf[pw]["is_disc"] = parent_shelf[pw]["is_disc"] or disc
            parent_shelf[pw]["year"] = min(parent_shelf[pw]["year"], yr)

    wildcats = wc.drop_nulls(subset=["wlbEwDecDeg", "wlbNsDecDeg"]).to_dicts()
    parent_hits: dict[str, list[dict]] = defaultdict(list)
    redrilled_pids: set[str] = set()

    for stem, rec in kept_json.items():
        rdate = str((rec.get("document") or {}).get("date") or "")
        if len(rdate) < 4 or not rdate[:4].isdigit():
            continue
        ryear = int(rdate[:4])
        gj = kept_geo.get(stem) or {}
        for feat in gj.get("features") or []:
            props = feat.get("properties") or {}
            geom = feat.get("geometry")
            if props.get("layer") not in ("prospect", "lead") or not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
                continue
            fid = str(props.get("feature_id") or feat.get("id") or "")
            pobj = feat_to_prospect.get((stem, fid)) or {}
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
                    wname = str(w["wlbWellboreName"]).strip()
                    pw = str(w.get("wlbWell") or wname).strip()
                    pid = pobj.get("prospect_id")
                    if pid:
                        redrilled_pids.add(pid)
                    w_pers = well_periods.get(wname, set())
                    blind_strat_match = bool(p_periods & w_pers) if (p_periods and w_pers) else None
                    is_deviated = bool(re.search(r"\s+[A-Z]\d*$|T\d+$", wname))
                    parent_hits[pw].append(
                        {
                            "parent_well": pw,
                            "well": wname,
                            "year": int(w["wlbCompletionYear"]),
                            "area": str(w.get("wlbMainArea") or "UNKNOWN").strip().upper(),
                            "is_disc": bool(w["is_disc"]),
                            "is_deviated": is_deviated,
                            "blind_strat_match": blind_strat_match,
                            "area_km2": props.get("area_km2_geometry"),
                        }
                    )

    redrill_parent_ids = set(parent_hits.keys())
    by_area_yr: dict[tuple[str, int], list[bool]] = defaultdict(list)
    by_yr: dict[int, list[bool]] = defaultdict(list)
    for pw, info in parent_shelf.items():
        if pw in redrill_parent_ids:
            continue
        by_area_yr[(info["area"], info["year"])].append(info["is_disc"])
        by_yr[info["year"]].append(info["is_disc"])

    collapsed = []
    for pw, hits in parent_hits.items():
        any_disc = any(h["is_disc"] for h in hits)
        all_vert = all(not h["is_deviated"] for h in hits)
        any_strat = any(h["blind_strat_match"] is True for h in hits)
        known_strat = any(h["blind_strat_match"] is not None for h in hits)
        min_area = min((h["area_km2"] for h in hits if isinstance(h["area_km2"], (int, float))), default=None)
        collapsed.append(
            {
                "parent_well": pw,
                "year": min(h["year"] for h in hits),
                "area": hits[0]["area"],
                "is_disc": any_disc,
                "vertical_only": all_vert,
                "blind_strat_match": True if any_strat else (False if known_strat else None),
                "min_area_km2": min_area,
            }
        )

    def summarize(sub: list[dict]) -> dict:
        n = len(sub)
        d = sum(1 for x in sub if x["is_disc"])
        exp_by = 0.0
        used_basin = 0
        for x in sub:
            pool = by_area_yr.get((x["area"], x["year"]))
            if pool and len(pool) >= 2:
                exp_by += sum(pool) / len(pool)
                used_basin += 1
            else:
                pool2 = by_yr.get(x["year"], [])
                if pool2:
                    exp_by += sum(pool2) / len(pool2)
        base_rate = (exp_by / n) if n else 0.0
        obs_rate = (d / n) if n else 0.0
        se = math.sqrt(base_rate * (1 - base_rate) / n) if (n and 0 < base_rate < 1) else 1.0
        z = (obs_rate - base_rate) / se if se > 0 else 0.0
        return {
            "n_parent_wells": n,
            "discoveries": d,
            "observed_rate_pct": round(obs_rate * 100, 1),
            "basin_year_leaveout_baseline_pct": round(base_rate * 100, 1),
            "diff_vs_baseline_pp": round((obs_rate - base_rate) * 100, 1),
            "z_vs_baseline": round(z, 2),
        }

    return (
        {
            "all_unique_parent_wells": summarize(collapsed),
            "vertical_only_parent_wells": summarize([w for w in collapsed if w["vertical_only"]]),
            "outcome_blind_strat_matched": summarize([w for w in collapsed if w["blind_strat_match"] is True]),
            "outcome_blind_strat_unmatched": summarize([w for w in collapsed if w["blind_strat_match"] is False]),
            "tight_le50km2_parent_wells": summarize([w for w in collapsed if w["min_area_km2"] is not None and w["min_area_km2"] <= 50.0]),
            "vertical_tight_blind_strat_matched": summarize([w for w in collapsed if w["vertical_only"] and w["blind_strat_match"] is True and w["min_area_km2"] is not None and w["min_area_km2"] <= 50.0]),
        },
        redrilled_pids,
    )


def run_upgraded_open_acreage_inventory(
    kept_json: dict,
    pid_to_features: dict[str, list[dict]],
    redrilled_pids: set[str],
) -> dict:
    active_feats = json.loads((CACHE / "active_licences_616.geojson").read_text(encoding="utf-8")).get("features") or []
    lic_df = pl.read_parquet(CACHE / "licence.parquet")
    strat_map = {
        str(r["prlName"]).strip(): str(r.get("prlStratigraphical") or "").strip().upper()
        for r in lic_df.select(["prlName", "prlStratigraphical"]).iter_rows(named=True)
        if r.get("prlName")
    }
    active_polys = []
    for f in active_feats:
        g = f.get("geometry")
        bb = geom_bbox(g)
        if bb:
            props = f.get("properties") or {}
            prl = str(props.get("prlName") or "").strip()
            active_polys.append((bb, g, prl, props.get("cmpLongName"), strat_map.get(prl, "NO") == "YES"))

    apa_feats = json.loads((CACHE / "apa_gross_603.geojson").read_text(encoding="utf-8")).get("features") or []
    apa_polys = [(geom_bbox(f.get("geometry")), f.get("geometry")) for f in apa_feats if geom_bbox(f.get("geometry"))]

    fac_df = pl.read_parquet(CACHE / "facility_fixed.parquet")
    hosts = []
    for r in fac_df.iter_rows(named=True):
        if str(r.get("fclPhase") or "").upper() != "IN SERVICE":
            continue
        if str(r.get("fclSurface") or "").upper() != "Y":
            continue
        try:
            lat = float(r["fclNsDeg"]) + float(r["fclNsMin"]) / 60.0 + float(r["fclNsSec"]) / 3600.0
            lon = float(r["fclEwDeg"]) + float(r["fclEwMin"]) / 60.0 + float(r["fclEwSec"]) / 3600.0
            if str(r.get("fclEwCode") or "").upper() == "W":
                lon = -lon
            hosts.append((lon, lat, str(r.get("fclName") or ""), str(r.get("fclBelongsToName") or "")))
        except (TypeError, ValueError):
            continue

    comm_nt_tags = {"volume_too_small", "commercial", "economics", "infrastructure", "partner_disagreement", "licence_expiry", "outside_licence", "portfolio_prioritization", "gas_market", "rig_availability"}
    geo_tags = {"seal_risk", "trap_risk", "charge_risk", "migration_risk", "reservoir_risk", "source_risk", "timing_risk", "retention_risk", "high_risk"}

    rows = []
    for rec in kept_json.values():
        lic_id = (rec.get("licence") or {}).get("licence_id")
        basin = (rec.get("licence") or {}).get("area") or "Unknown"
        op = (rec.get("document") or {}).get("author_company")
        rdate = str((rec.get("document") or {}).get("date") or "")[:4]
        doc_url = (rec.get("document") or {}).get("source_url")
        for p in rec.get("prospects") or []:
            pid = p.get("prospect_id")
            if not pid or pid in redrilled_pids:
                continue
            status = str(p.get("status_at_report") or "").lower()
            if any(k in status for k in ("drilled", "discovery", "dry")):
                continue
            ass = p.get("assessments") or []
            if not ass:
                continue
            fin = ass[-1]
            if str(fin.get("stage") or "").lower() in ("application", "award", "apa_application", "pre_award"):
                continue
            pg = (fin.get("risk") or {}).get("pg")
            if not isinstance(pg, (int, float)) or pg < 0.20 or pg >= 0.99:
                continue
            vols = [v for v in (fin.get("volumes") or []) if v.get("basis") == "recoverable"]
            oe = [v for v in vols if v.get("phase") in ("oil_equivalent", "total_hc")] or vols
            best_v, best_obj = None, None
            for v in oe:
                mv = safe_canonical_volume_msmo3(v, "mean")
                if mv is not None and mv > 0 and (best_v is None or mv > best_v):
                    best_v = mv
                    best_obj = v
            if best_v is None:
                continue

            feats = pid_to_features.get(pid) or []
            poly_feat = next((f for f in feats if (f.get("geometry") or {}).get("type") in ("Polygon", "MultiPolygon")), feats[0] if feats else None)
            if not poly_feat:
                continue
            geom = poly_feat.get("geometry")
            pts = sample_polygon_points(geom, grid_n=7)
            if not pts:
                continue

            open_pts = 0
            apa_pts = 0
            hit_lics = {}
            for px, py in pts:
                in_active = False
                for (minx, maxx, miny, maxy), g, prl, aop, is_strat in active_polys:
                    if minx <= px <= maxx and miny <= py <= maxy and pip_geom(px, py, g):
                        in_active = True
                        hit_lics[prl] = (aop, is_strat)
                        break
                if not in_active:
                    open_pts += 1
                for (minx, maxx, miny, maxy), g in apa_polys:
                    if minx <= px <= maxx and miny <= py <= maxy and pip_geom(px, py, g):
                        apa_pts += 1
                        break

            open_frac = open_pts / len(pts)
            in_apa = (apa_pts / len(pts)) >= 0.5
            cx, cy = geom_centroid(geom) or pts[0]
            near_km, near_fac = None, None
            if hosts:
                best_d = 1e9
                for hlon, hlat, hname, hfld in hosts:
                    d = haversine_km(cx, cy, hlon, hlat)
                    if d < best_d:
                        best_d = d
                        near_fac = f"{hname} ({hfld})" if hfld else hname
                near_km = round(best_d, 1)

            concl = p.get("conclusion") or {}
            reasons = set(str(x).lower() for x in (concl.get("reasons_not_drilled") or []))
            has_comm_nt = bool(reasons & comm_nt_tags)
            has_geo = bool(reasons & geo_tags)
            tier = "Tier_A_Comm_NonTech" if (has_comm_nt and not has_geo) or (has_comm_nt and pg >= 0.25) else "Tier_B_Geo_Risk_or_Other"

            dist_obj = (best_obj or {}).get("distribution") or {}
            rows.append(
                {
                    "prospect_id": pid,
                    "name": p.get("name"),
                    "licence": lic_id,
                    "relinq_year": rdate,
                    "operator": op,
                    "basin": basin,
                    "tier": tier,
                    "pg": round(pg, 3),
                    "mean_msmo3": round(best_v, 2),
                    "risked_msmo3": round(pg * best_v, 2),
                    "risked_mmboe": round(pg * best_v * 6.2898, 1),
                    "unrisked_mmboe": round(best_v * 6.2898, 1),
                    "open_fraction_pct": round(open_frac * 100, 1),
                    "in_apa_area": in_apa,
                    "active_overlaps": [{"licence": k, "operator": v[0], "depth_limited": v[1]} for k, v in hit_lics.items()],
                    "nearest_host_km": near_km,
                    "nearest_host": near_fac,
                    "phase": (best_obj or {}).get("phase"),
                    "raw_unit": dist_obj.get("unit"),
                    "original_text": dist_obj.get("original_text"),
                    "source_page": (dist_obj.get("source") or {}).get("page"),
                    "conclusion_summary": concl.get("summary") or p.get("summary"),
                    "reasons_not_drilled": sorted(reasons),
                    "doc_url": doc_url,
                }
            )

    dedup_rows = []
    seen_name_loc = set()
    for r in sorted(rows, key=lambda x: x["risked_msmo3"], reverse=True):
        key = (str(r["name"] or "").strip().lower(), r["basin"])
        if key in seen_name_loc:
            continue
        seen_name_loc.add(key)
        dedup_rows.append(r)

    def summarize_set(sub: list[dict]) -> dict:
        return {
            "count": len(sub),
            "unrisked_bboe": round(sum(x["unrisked_mmboe"] for x in sub) / 1000.0, 2),
            "risked_msmo3": round(sum(x["risked_msmo3"] for x in sub), 1),
            "risked_bboe": round(sum(x["risked_mmboe"] for x in sub) / 1000.0, 2),
        }

    mostly_open = [r for r in dedup_rows if r["open_fraction_pct"] >= 50.0]
    apa_open = [r for r in mostly_open if r["in_apa_area"]]
    non_apa_open = [r for r in mostly_open if not r["in_apa_area"]]
    tier_a_apa_open = [r for r in apa_open if r["tier"] == "Tier_A_Comm_NonTech"]
    near_infra_apa_open = [r for r in apa_open if r["nearest_host_km"] is not None and r["nearest_host_km"] <= 30.0]

    return {
        "n_in_service_surface_hosts": len(hosts),
        "all_georef_undrilled_pg20_excl_redrilled": summarize_set(dedup_rows),
        "mostly_open_ge50pct": summarize_set(mostly_open),
        "apa_eligible_open": summarize_set(apa_open),
        "non_apa_open_numbered_rounds_only": summarize_set(non_apa_open),
        "tier_a_comm_nontech_apa_open": summarize_set(tier_a_apa_open),
        "tieback_ready_le30km_apa_open": summarize_set(near_infra_apa_open),
        "re_licensed_with_depth_limited_flag": sum(
            1 for r in dedup_rows if r["open_fraction_pct"] < 50.0 and any(o["depth_limited"] for o in r["active_overlaps"])
        ),
        "top_15_apa_open_for_manual_audit": apa_open[:15],
        "top_15_tieback_le30km_apa_open": near_infra_apa_open[:15],
    }


def main() -> None:
    raw_json, raw_geo = load_raw_records()
    kept_json, kept_geo, _ = deduplicate_records(raw_json, raw_geo)
    wells_df = pl.read_parquet(DEFAULT_FACTPAGES_WELLS)
    unit_to_period = build_unit_to_period()
    well_periods = build_well_penetrated_periods(unit_to_period)
    feat_to_prospect, pid_to_features = build_prospect_feature_maps(kept_json, kept_geo)

    redrill_res, redrilled_pids = run_parent_well_redrill_audit(
        kept_json, kept_geo, wells_df, feat_to_prospect, well_periods
    )
    inv_res = run_upgraded_open_acreage_inventory(kept_json, pid_to_features, redrilled_pids)

    out = {
        "outcome_blind_parent_well_redrills": redrill_res,
        "upgraded_open_acreage_inventory": inv_res,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("=== 1. OUTCOME-BLIND PARENT-WELL REDRILLS VS BASIN+YEAR LEAVE-OUT BASELINE ===")
    print(json.dumps(redrill_res, indent=2))
    print("\n=== 2. UPGRADED OPEN-ACREAGE + APA + POLYGON-FRACTION + TIEBACK INVENTORY ===")
    print(json.dumps({k: v for k, v in inv_res.items() if not k.startswith("top_15")}, indent=2))
    print("\n=== 3. TOP 15 APA-ELIGIBLE OPEN ACREAGE PROSPECTS (FOR MANUAL SOURCE AUDIT) ===")
    for i, r in enumerate(inv_res["top_15_apa_open_for_manual_audit"], 1):
        print(f"{i:2d}. {r['name']} ({r['licence']}, {r['basin']}, {r['relinq_year']}) | {r['tier']} | Pg={r['pg']} | Unr={r['unrisked_mmboe']} / Risked={r['risked_mmboe']} MMboe | Open={r['open_fraction_pct']}% | Host={r['nearest_host_km']} km ({r['nearest_host']}) | p.{r['source_page']} | unit={r['raw_unit']} | quote={str(r['original_text'])[:110]}")
        print(f"    concl={str(r['conclusion_summary'])[:180]}")


if __name__ == "__main__":
    main()
