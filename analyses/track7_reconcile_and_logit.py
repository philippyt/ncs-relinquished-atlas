import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl
import statsmodels.api as sm

ROOT = Path(r"C:\Users\philip\Documents\ncs-relinquished-atlas")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "analyses"))

from loader import DEFAULT_FACTPAGES_WELLS, deduplicate_records, load_raw_records
from track6_production_audit import (
    build_prospect_feature_maps,
    geom_bbox,
    haversine_km,
    pip_geom,
)


def main() -> None:
    raw_json, raw_geo = load_raw_records()
    kept_json, kept_geo, _ = deduplicate_records(raw_json, raw_geo)
    wells_df = pl.read_parquet(DEFAULT_FACTPAGES_WELLS)
    feat_to_prospect, _ = build_prospect_feature_maps(kept_json, kept_geo)

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
    for row in wc.select(
        ["wlbWell", "wlbWellboreName", "wlbMainArea", "wlbCompletionYear", "is_disc", "wlbEwDecDeg", "wlbNsDecDeg"]
    ).iter_rows(named=True):
        pw = str(row["wlbWell"] or row["wlbWellboreName"]).strip()
        yr = int(row["wlbCompletionYear"])
        area = str(row["wlbMainArea"] or "UNKNOWN").strip().upper()
        disc = bool(row["is_disc"])
        lon, lat = row["wlbEwDecDeg"], row["wlbNsDecDeg"]
        if pw not in parent_shelf:
            parent_shelf[pw] = {"year": yr, "area": area, "is_disc": disc, "lon": lon, "lat": lat}
        else:
            parent_shelf[pw]["is_disc"] = parent_shelf[pw]["is_disc"] or disc
            parent_shelf[pw]["year"] = min(parent_shelf[pw]["year"], yr)
            if parent_shelf[pw]["lon"] is None and lon is not None:
                parent_shelf[pw]["lon"] = lon
                parent_shelf[pw]["lat"] = lat

    prior_discs = [
        (info["year"], float(info["lon"]), float(info["lat"]))
        for info in parent_shelf.values()
        if info["is_disc"] and info["lon"] is not None and info["lat"] is not None
    ]

    for pw, info in parent_shelf.items():
        if info["lon"] is None or info["lat"] is None:
            info["dist_km"] = None
            continue
        best = 1e9
        for dy, dlon, dlat in prior_discs:
            if dy < info["year"]:
                d = haversine_km(float(info["lon"]), float(info["lat"]), dlon, dlat)
                if d < best:
                    best = d
        info["dist_km"] = round(best, 2) if best < 1e8 else None

    wildcats = wc.drop_nulls(subset=["wlbEwDecDeg", "wlbNsDecDeg"]).to_dicts()
    redrill_pws: set[str] = set()
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
            for w in wildcats:
                if int(w["wlbCompletionYear"]) <= ryear:
                    continue
                wx, wy = float(w["wlbEwDecDeg"]), float(w["wlbNsDecDeg"])
                if not (minx <= wx <= maxx and miny <= wy <= maxy):
                    continue
                if pip_geom(wx, wy, geom):
                    pw = str(w.get("wlbWell") or w["wlbWellboreName"]).strip()
                    redrill_pws.add(pw)

    missing_dist = [pw for pw in redrill_pws if parent_shelf[pw]["dist_km"] is None]
    print(f"Total redrill parent wells: {len(redrill_pws)}, missing dist_km: {len(missing_dist)}", [(pw, parent_shelf[pw]) for pw in missing_dist])

    def bin_label(d: float, cut1: float = 15.0, cut2: float = 40.0) -> str:
        if d <= cut1:
            return f"near_le{int(cut1)}km"
        if d <= cut2:
            return f"mid_{int(cut1)}_{int(cut2)}km"
        return f"frontier_gt{int(cut2)}km"

    valid_pws = [pw for pw in redrill_pws if parent_shelf[pw]["dist_km"] is not None]
    min_rd_year = min(parent_shelf[pw]["year"] for pw in valid_pws)
    print(f"Valid redrill parent wells with prior-disc dist: {len(valid_pws)}, min year: {min_rd_year}")

    def eval_bins(cut1: float, cut2: float = 40.0) -> dict:
        by_am5: dict[tuple[str, str, int], list[bool]] = defaultdict(list)
        by_m5: dict[tuple[str, int], list[bool]] = defaultdict(list)
        by_m: dict[str, list[bool]] = defaultdict(list)
        for pw, info in parent_shelf.items():
            if pw in redrill_pws or info["dist_km"] is None:
                continue
            bl = bin_label(info["dist_km"], cut1, cut2)
            yr5 = (info["year"] // 5) * 5
            by_am5[(info["area"], bl, yr5)].append(info["is_disc"])
            by_m5[(bl, yr5)].append(info["is_disc"])
            by_m[bl].append(info["is_disc"])

        per_well = []
        for pw in valid_pws:
            info = parent_shelf[pw]
            bl = bin_label(info["dist_km"], cut1, cut2)
            yr5 = (info["year"] // 5) * 5
            pool = by_am5.get((info["area"], bl, yr5))
            if not pool or len(pool) < 3:
                pool = by_m5.get((bl, yr5))
            if not pool:
                pool = by_m.get(bl)
            base_p = sum(pool) / len(pool)
            per_well.append((bl, info["is_disc"], base_p))

        res = {}
        for key in ("ALL", f"near_le{int(cut1)}km", f"mid_{int(cut1)}_{int(cut2)}km", f"frontier_gt{int(cut2)}km"):
            sub = per_well if key == "ALL" else [x for x in per_well if x[0] == key]
            n = len(sub)
            d = sum(1 for x in sub if x[1])
            obs = d / n if n else 0.0
            base = sum(x[2] for x in sub) / n if n else 0.0
            se = math.sqrt(base * (1 - base) / n) if (n and 0 < base < 1) else 1.0
            z = (obs - base) / se if se > 0 else 0.0
            res[key] = {"n": n, "disc": d, "obs_pct": round(obs * 100, 1), "base_pct": round(base * 100, 1), "diff_pp": round((obs - base) * 100, 1), "z": round(z, 2)}
        return res

    sens = {f"cut_{c}km": eval_bins(float(c), 40.0) for c in (10, 15, 20, 30)}
    print("\n=== RECONCILED MATURITY BINS & CUTOFF SENSITIVITY (10, 15, 20, 30 km) ===")
    for k, v in sens.items():
        print(k, json.dumps(v))

    rows_reg = []
    for pw, info in parent_shelf.items():
        if info["dist_km"] is None or info["year"] < min_rd_year:
            continue
        if info["area"] not in ("NORTH SEA", "NORWEGIAN SEA", "BARENTS SEA"):
            continue
        rows_reg.append(
            {
                "y": 1.0 if info["is_disc"] else 0.0,
                "is_redrill": 1.0 if pw in redrill_pws else 0.0,
                "log_dist": math.log1p(info["dist_km"]),
                "area": info["area"],
                "yr5": (info["year"] // 5) * 5,
            }
        )

    df_reg = pl.DataFrame(rows_reg)
    areas = sorted(df_reg["area"].unique().to_list())[1:]
    yr5s = sorted(df_reg["yr5"].unique().to_list())[1:]

    def make_X(with_interaction: bool) -> tuple[np.ndarray, list[str]]:
        cols = [np.ones(df_reg.height), df_reg["is_redrill"].to_numpy(), df_reg["log_dist"].to_numpy()]
        names = ["intercept", "is_redrill", "log1p_dist_km"]
        if with_interaction:
            cols.append(df_reg["is_redrill"].to_numpy() * df_reg["log_dist"].to_numpy())
            names.append("is_redrill_x_log_dist")
        for a in areas:
            cols.append((df_reg["area"] == a).cast(pl.Float64).to_numpy())
            names.append(f"area_{a}")
        for y5 in yr5s:
            cols.append((df_reg["yr5"] == y5).cast(pl.Float64).to_numpy())
            names.append(f"yr5_{y5}")
        return np.column_stack(cols), names

    y = df_reg["y"].to_numpy()
    X1, n1 = make_X(False)
    m1 = sm.Logit(y, X1).fit(disp=False)
    X2, n2 = make_X(True)
    m2 = sm.Logit(y, X2).fit(disp=False)

    print(f"\n=== LOGISTIC REGRESSION (n={df_reg.height} wildcat parent wells, year >= {min_rd_year}, redrills={int(df_reg['is_redrill'].sum())}) ===")
    print("Model 1 (main effects):")
    for nm, coef, se, p in zip(n1, m1.params, m1.bse, m1.pvalues):
        if nm in ("intercept", "is_redrill", "log1p_dist_km"):
            print(f"  {nm:24s} coef={coef:+.3f} (OR={math.exp(coef):.2f}), SE={se:.3f}, p={p:.4f}")
    print("Model 2 (with is_redrill x log1p_dist_km interaction):")
    for nm, coef, se, p in zip(n2, m2.params, m2.bse, m2.pvalues):
        if nm in ("intercept", "is_redrill", "log1p_dist_km", "is_redrill_x_log_dist"):
            print(f"  {nm:24s} coef={coef:+.3f} (OR={math.exp(coef):.2f}), SE={se:.3f}, p={p:.4f}")

    out = {
        "n_redrill_total": len(redrill_pws),
        "n_missing_dist": len(missing_dist),
        "n_valid_reconciled": len(valid_pws),
        "cutoff_sensitivity": sens,
        "logit_n_wells": df_reg.height,
        "logit_min_year": min_rd_year,
        "logit_main": {nm: {"coef": round(float(c), 4), "or": round(math.exp(float(c)), 3), "se": round(float(s), 4), "p": round(float(p), 4)} for nm, c, s, p in zip(n1, m1.params, m1.bse, m1.pvalues) if nm in ("is_redrill", "log1p_dist_km")},
        "logit_interaction": {nm: {"coef": round(float(c), 4), "or": round(math.exp(float(c)), 3), "se": round(float(s), 4), "p": round(float(p), 4)} for nm, c, s, p in zip(n2, m2.params, m2.bse, m2.pvalues) if nm in ("is_redrill", "log1p_dist_km", "is_redrill_x_log_dist")},
    }
    (ROOT / "analyses" / "track7_reconcile_and_logit.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
