import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import httpx
import polars as pl

ROOT = Path(r"C:\Users\philip\Documents\ncs-relinquished-atlas")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "analyses"))

from loader import DEFAULT_FACTPAGES_WELLS, deduplicate_records, load_raw_records
from track6_production_audit import (
    build_unit_to_period,
    build_well_penetrated_periods,
    geom_bbox,
    geom_centroid,
    haversine_km,
    norm_period,
    pip_geom,
    sample_polygon_points,
)

CACHE = ROOT / "data" / "sodir"
INV_GEO = ROOT / "reports" / "open_acreage_inventory.geojson"
INV_CSV = ROOT / "reports" / "open_acreage_inventory.csv"
OUT_JSON = ROOT / "analyses" / "track9_findings.json"


def fetch_discoveries_504() -> list[dict]:
    p = CACHE / "discoveries_504.geojson"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")).get("features") or []
    url = "https://factmaps.sodir.no/api/rest/services/FactMaps/FactMapsWGS84/MapServer/504/query"
    feats = []
    offset = 0
    with httpx.Client(timeout=60.0, follow_redirects=True) as c:
        while True:
            r = c.get(
                url,
                params={
                    "where": "1=1",
                    "outFields": "dscName,fldName,dscHcType,dscCurrentActivityStatus",
                    "outSR": "4326",
                    "f": "geojson",
                    "resultOffset": offset,
                    "resultRecordCount": 500,
                },
            )
            r.raise_for_status()
            batch = r.json().get("features") or []
            feats.extend(batch)
            if len(batch) < 500:
                break
            offset += len(batch)
    p.write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
    return feats


def main() -> None:
    disc_feats = fetch_discoveries_504()
    fld_feats = json.loads((CACHE / "fields_502.geojson").read_text(encoding="utf-8")).get("features") or []

    known_polys = []
    for f in disc_feats:
        g = f.get("geometry")
        bb = geom_bbox(g)
        if bb:
            props = f.get("properties") or {}
            known_polys.append((bb, g, f"Discovery:{props.get('dscName')}", props.get("dscName")))
    for f in fld_feats:
        g = f.get("geometry")
        bb = geom_bbox(g)
        if bb:
            props = f.get("properties") or {}
            known_polys.append((bb, g, f"Field:{props.get('fldName')}", props.get("fldName")))

    gj = json.loads(INV_GEO.read_text(encoding="utf-8"))
    feats = gj["features"]

    rj, _ = load_raw_records()
    kj, _, _ = deduplicate_records(rj, {})
    pid_periods: dict[str, set[str]] = {}
    for rec in kj.values():
        for p in rec.get("prospects") or []:
            pid = p.get("prospect_id")
            pers = set()
            for t in p.get("targets") or []:
                per = norm_period(((t.get("reservoir") or {}).get("chrono") or {}).get("period"))
                if per:
                    pers.add(per)
            if pid:
                pid_periods[pid] = pers

    wells = pl.read_parquet(DEFAULT_FACTPAGES_WELLS)
    wp = build_well_penetrated_periods(build_unit_to_period())
    dry_wcs = []
    for r in wells.filter(pl.col("wlbPurpose").str.to_uppercase() == "WILDCAT").drop_nulls(subset=["wlbEwDecDeg", "wlbNsDecDeg"]).to_dicts():
        cnt = str(r.get("wlbContent") or "").upper()
        is_disc = any(k in cnt for k in ("OIL", "GAS", "COND")) and "SHOW" not in cnt
        if not is_disc and r.get("wlbCompletionYear") and int(r["wlbCompletionYear"]) > 0:
            wn = str(r["wlbWellboreName"]).strip()
            pers = set(wp.get(wn, set()))
            tdp = norm_period(r.get("wlbAgeAtTd"))
            if tdp:
                pers.add(tdp)
            dry_wcs.append((float(r["wlbEwDecDeg"]), float(r["wlbNsDecDeg"]), wn, int(r["wlbCompletionYear"]), pers))

    items = []
    for idx, f in enumerate(feats):
        props = dict(f["properties"])
        geom = f["geometry"]
        bb = geom_bbox(geom)
        pts = sample_polygon_points(geom, grid_n=9)
        pid = props["prospect_id"]
        pers = pid_periods.get(pid, set())
        items.append({"idx": idx, "props": props, "geom": geom, "bb": bb, "pts": pts, "periods": pers})

    parent = list(range(len(items)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    overlap_pairs = []
    for i in range(len(items)):
        a = items[i]
        if not a["bb"] or not a["pts"]:
            continue
        for j in range(i + 1, len(items)):
            b = items[j]
            if not b["bb"] or not b["pts"]:
                continue
            if a["props"]["licence"] == b["props"]["licence"]:
                continue
            if a["bb"][1] < b["bb"][0] or b["bb"][1] < a["bb"][0] or a["bb"][3] < b["bb"][2] or b["bb"][3] < a["bb"][2]:
                continue
            if a["periods"] and b["periods"] and not (a["periods"] & b["periods"]):
                continue
            f12 = sum(1 for x, y in a["pts"] if pip_geom(x, y, b["geom"])) / len(a["pts"])
            f21 = sum(1 for x, y in b["pts"] if pip_geom(x, y, a["geom"])) / len(b["pts"])
            if max(f12, f21) >= 0.50:
                union(i, j)
                overlap_pairs.append((a["props"]["prospect_id"], b["props"]["prospect_id"], round(max(f12, f21), 2)))

    groups = defaultdict(list)
    for i in range(len(items)):
        groups[find(i)].append(items[i])

    dedup_items = []
    for g_list in groups.values():
        g_list.sort(
            key=lambda it: (
                int(it["props"]["relinq_year"]) if it["props"].get("relinq_year") else 0,
                float(it["props"].get("risked_mmboe") or 0.0),
            ),
            reverse=True,
        )
        winner = g_list[0]
        preds = [it["props"]["prospect_id"] for it in g_list[1:]]
        winner["props"]["predecessor_ids"] = "; ".join(preds)
        winner["props"]["times_relinquished"] = len(g_list)
        dedup_items.append(winner)

    final_items = []
    excluded_disc_overlaps = []
    flagged_partial_disc = []

    for it in dedup_items:
        props = it["props"]
        pts = it["pts"]
        pers = it["periods"]

        hit_names = Counter()
        hit_pts = 0
        for px, py in pts:
            matched_here = None
            for (minx, maxx, miny, maxy), kg, klabel, _ in known_polys:
                if minx <= px <= maxx and miny <= py <= maxy and pip_geom(px, py, kg):
                    matched_here = klabel
                    break
            if matched_here:
                hit_pts += 1
                hit_names[matched_here] += 1
        disc_ov_pct = round(100 * hit_pts / max(1, len(pts)), 1)
        top_known = hit_names.most_common(1)[0][0] if hit_names else ""
        props["sodir_disc_field_overlap_pct"] = disc_ov_pct
        props["overlapping_sodir_disc_or_field"] = top_known

        c = geom_centroid(it["geom"]) or (pts[0] if pts else None)
        best_dry_km, best_dry_well = 1e9, ""
        if c:
            for dx, dy, dwn, _, dpers in dry_wcs:
                if pers and dpers and not (pers & dpers):
                    continue
                dkm = haversine_km(c[0], c[1], dx, dy)
                if dkm < best_dry_km:
                    best_dry_km = dkm
                    best_dry_well = dwn
        props["nearest_same_play_dry_well_km"] = round(best_dry_km, 1) if best_dry_km < 1e8 else None
        props["nearest_same_play_dry_well"] = best_dry_well if best_dry_km < 1e8 else ""
        props["nearby_same_play_dry_well_5km"] = bool(best_dry_km <= 5.0)

        if disc_ov_pct >= 50.0:
            excluded_disc_overlaps.append(
                {
                    "prospect_id": props["prospect_id"],
                    "name": props["name"],
                    "licence": props["licence"],
                    "risked_mmboe": props["risked_mmboe"],
                    "overlap_pct": disc_ov_pct,
                    "overlapping": top_known,
                }
            )
            continue
        if disc_ov_pct >= 20.0:
            flagged_partial_disc.append((props["prospect_id"], props["name"], disc_ov_pct, top_known))
        final_items.append(it)

    final_items.sort(key=lambda it: float(it["props"]["risked_mmboe"]), reverse=True)
    out_rows = [it["props"] for it in final_items]
    out_feats = [{"type": "Feature", "geometry": it["geom"], "properties": it["props"]} for it in final_items]

    with INV_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    INV_GEO.write_text(json.dumps({"type": "FeatureCollection", "features": out_feats}), encoding="utf-8")

    ta = [r for r in out_rows if r["tier"] == "Tier_A"]
    tb = [r for r in out_rows if r["tier"] == "Tier_B"]
    le30 = [r for r in out_rows if r.get("dist_now_km") is not None and float(r["dist_now_km"]) <= 30.0]
    chg = [r for r in out_rows if r.get("changed_circumstances_flag")]
    host_counts = Counter(r.get("host_viability_flag", "unknown") for r in out_rows)
    known_hosts = sum(v for k, v in host_counts.items() if k != "unknown")
    dry5 = sum(1 for r in out_rows if r["nearby_same_play_dry_well_5km"])
    multi_rel = [r for r in out_rows if int(r["times_relinquished"]) > 1]

    aasta_names = {"Kelvin", "Fjellflokk Far East 1", "Svartbakkestjerne Springar", "Birkeland"}
    aasta_rows = [r for r in out_rows if r["name"] in aasta_names]

    summary = {
        "before_spatial_dedup": len(items),
        "after_spatial_dedup": len(dedup_items),
        "spatial_duplicate_pairs_found": len(overlap_pairs),
        "excluded_overlapping_sodir_disc_field_ge50pct": len(excluded_disc_overlaps),
        "excluded_disc_field_list": excluded_disc_overlaps,
        "partial_disc_field_overlaps_20_to_49pct": len(flagged_partial_disc),
        "final_unique_apa_open_count": len(out_rows),
        "final_unrisked_bboe": round(sum(float(r["unrisked_mmboe"]) for r in out_rows) / 1000.0, 2),
        "final_risked_bboe": round(sum(float(r["risked_mmboe"]) for r in out_rows) / 1000.0, 2),
        "tier_a_count": len(ta),
        "tier_a_risked_bboe": round(sum(float(r["risked_mmboe"]) for r in ta) / 1000.0, 2),
        "tier_b_count": len(tb),
        "tier_b_risked_bboe": round(sum(float(r["risked_mmboe"]) for r in tb) / 1000.0, 2),
        "within_30km_count": len(le30),
        "within_30km_risked_bboe": round(sum(float(r["risked_mmboe"]) for r in le30) / 1000.0, 2),
        "median_years_open": sorted(int(r["years_open"]) for r in out_rows if r.get("years_open") is not None)[len(out_rows) // 2],
        "pct_with_nearby_awards_since": round(100 * sum(1 for r in out_rows if int(r["nearby_awards_since"]) > 0) / len(out_rows), 1),
        "host_viability_counts": dict(host_counts),
        "host_viability_known_count": known_hosts,
        "nearby_same_play_dry_well_5km_count": dry5,
        "nearby_same_play_dry_well_5km_pct": round(100 * dry5 / len(out_rows), 1),
        "times_relinquished_gt1_count": len(multi_rel),
        "aasta_core4": {
            "count": len(aasta_rows),
            "unrisked_mmboe": round(sum(float(r["unrisked_mmboe"]) for r in aasta_rows), 1),
            "risked_mmboe": round(sum(float(r["risked_mmboe"]) for r in aasta_rows), 1),
        },
        "changed_circumstances_rows": [
            {k: r[k] for k in ("name", "licence", "stated_pg", "unrisked_mmboe", "risked_mmboe", "years_open", "nearby_awards_since", "times_relinquished", "predecessor_ids", "dist_at_relinq_km", "dist_now_km", "nearest_same_play_dry_well_km", "nearest_same_play_dry_well")}
            for r in chg
        ],
        "top_14": [
            {k: r[k] for k in ("name", "licence", "basin", "tier", "stated_pg", "unrisked_mmboe", "risked_mmboe", "years_open", "nearby_awards_since", "times_relinquished", "predecessor_ids", "nearest_host", "dist_now_km", "host_end_year", "host_viability_flag", "nearest_same_play_dry_well_km", "nearby_same_play_dry_well_5km", "sodir_disc_field_overlap_pct")}
            for r in out_rows[:14]
        ],
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "top_14"}, indent=2))
    print("\n=== TOP 14 AFTER SPATIAL DEDUP & DISCOVERY/FIELD SCREEN ===")
    for i, r in enumerate(summary["top_14"], 1):
        print(f"{i:2d}. {r['name']} ({r['licence']}) | {r['tier']} | Pg={r['stated_pg']} | {r['unrisked_mmboe']}/{r['risked_mmboe']} | Rel={r['times_relinquished']} | Dry5km={r['nearby_same_play_dry_well_5km']} ({r['nearest_same_play_dry_well_km']} km) | DiscOv={r['sodir_disc_field_overlap_pct']}% | Host={r['nearest_host']} ({r['dist_now_km']} km, {r['host_end_year']}, {r['host_viability_flag']})")


if __name__ == "__main__":
    main()
