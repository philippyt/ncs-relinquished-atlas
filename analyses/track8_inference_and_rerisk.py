import csv
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
import statsmodels.api as sm
import statsmodels.formula.api as smf

ROOT = Path(r"C:\Users\philip\Documents\ncs-relinquished-atlas")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "analyses"))

from loader import (
    DEFAULT_FACTPAGES_WELLS,
    deduplicate_records,
    load_raw_records,
    safe_canonical_volume_msmo3,
)
from track6_production_audit import (
    build_prospect_feature_maps,
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
OUT_JSON = ROOT / "analyses" / "track8_findings.json"
OUT_CSV = ROOT / "reports" / "open_acreage_inventory.csv"
OUT_GEOJSON = ROOT / "reports" / "open_acreage_inventory.geojson"

HOST_END_YEARS = {
    "AASTA HANSTEEN": ("2039", "Equinor Irpa tie-back extension"),
    "ULA": ("2028", "Aker BP cessation plan"),
    "TAMBAR": ("2028", "Aker BP cessation plan via Ula"),
    "BALDER": ("2045+", "Var Energi Balder X / Jotun FPSO"),
    "RINGHORNE": ("2045+", "Var Energi Balder X / Ringhorne"),
    "EKOFISK": ("2048", "Greater Ekofisk licence extension"),
    "MELKØYA LANDANLEGG": ("2050+", "Equinor Snohvit Future"),
    "SNØHVIT": ("2050+", "Equinor Snohvit Future"),
    "JOHAN CASTBERG": ("2055", "Equinor 30-year baseline from 2025"),
    "TROLL": ("2050+", "Equinor Troll Phase 3"),
    "JOHAN SVERDRUP": ("2070", "Equinor 50-year design life from 2019"),
    "OSEBERG": ("2040+", "Equinor Oseberg future"),
}

GAS_REINJECTION_ONLY = {
    "GOLIAT",
    "JOHAN CASTBERG",
    "EDVARD GRIEG",
    "IVAR AASEN",
    "YME",
    "BALDER",
    "RINGHORNE",
    "ALVHEIM",
    "DRAUGEN",
}


def norm_operator(name: str | None) -> str:
    if not name:
        return "UNKNOWN"
    t = str(name).upper()
    if any(k in t for k in ("EQUINOR", "STATOIL")):
        return "EQUINOR"
    if any(k in t for k in ("AKER BP", "DET NORSKE", "LUNDIN", "BP NORGE")):
        return "AKER_BP"
    if any(k in t for k in ("VÅR ENERGI", "VAR ENERGI", "ENI NORGE", "POINT RESOURCES", "NEPTUNE", "ENGIE", "GDF SUEZ")):
        return "VAR_ENERGI"
    if any(k in t for k in ("HARBOUR", "WINTERSHALL", "DEA NORGE")):
        return "HARBOUR_WINTERSHALL"
    if "CONOCOPHILLIPS" in t:
        return "CONOCOPHILLIPS"
    if "SHELL" in t:
        return "SHELL"
    if "TOTAL" in t or "MAERSK" in t:
        return "TOTALENERGIES"
    if "DNO" in t or "FAROE" in t:
        return "DNO"
    if "OMV" in t:
        return "OMV"
    if "OKEA" in t:
        return "OKEA"
    if "ORLEN" in t or "PGNIG" in t:
        return "ORLEN"
    if "WELLESLEY" in t:
        return "WELLESLEY"
    if "SPIRIT" in t or "CENTRICA" in t or "BAYERNGAS" in t:
        return "SPIRIT"
    if "REPSOL" in t or "TALISMAN" in t:
        return "REPSOL"
    return re.sub(r"\s+(AS|ASA|NORGE|PETROLEUM|ENERGY|NORWAY)\b", "", t).strip()


def parse_year(s: str | None) -> int | None:
    if not s:
        return None
    m = re.search(r"(19|20)\d{2}", str(s))
    return int(m.group(0)) if m else None


def wild_cluster_bootstrap_lpm(
    y: np.ndarray,
    X: np.ndarray,
    clusters: np.ndarray,
    target_idx: int,
    n_draws: int = 9999,
    seed: int = 42,
) -> float:
    n, k = X.shape
    ols_full = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": clusters})
    t_obs = float(abs(ols_full.tvalues[target_idx]))

    X_r = np.delete(X, target_idx, axis=1)
    ols_r = sm.OLS(y, X_r).fit()
    y_hat_r = ols_r.fittedvalues
    e_r = ols_r.resid

    uniq_c, inv_c = np.unique(clusters, return_inverse=True)
    g = len(uniq_c)
    xtx_inv = np.linalg.pinv(X.T @ X)
    rng = np.random.default_rng(seed)

    exceed = 0
    batch = 500
    for start in range(0, n_draws, batch):
        b = min(batch, n_draws - start)
        weights = rng.choice([-1.0, 1.0], size=(b, g))
        w_obs = weights[:, inv_c]
        y_star = y_hat_r[None, :] + w_obs * e_r[None, :]
        betas = (y_star @ X) @ xtx_inv.T
        resids = y_star - betas @ X.T
        for j in range(b):
            rj = resids[j]
            meat = np.zeros((k, k))
            for ci in range(g):
                mask = inv_c == ci
                s_c = X[mask].T @ rj[mask]
                meat += np.outer(s_c, s_c)
            scale = (g / max(1, g - 1)) * ((n - 1) / max(1, n - k))
            vcov = scale * (xtx_inv @ meat @ xtx_inv)
            se_j = math.sqrt(max(1e-18, vcov[target_idx, target_idx]))
            t_j = abs(betas[j, target_idx] / se_j)
            if t_j >= t_obs:
                exceed += 1
    return round((exceed + 1) / (n_draws + 1), 4)


def fit_logit_with_se_variants(
    df: pl.DataFrame,
    outcome_col: str,
    terms: list[str],
    cluster_lic: np.ndarray,
    cluster_quad: np.ndarray,
) -> dict:
    y = df[outcome_col].to_numpy().astype(float)
    areas = sorted(df["area"].unique().to_list())[1:]
    yr5s = sorted(df["yr5"].unique().to_list())[1:]

    cols = [np.ones(df.height)]
    names = ["intercept"]
    for t in terms:
        if t == "is_redrill_x_log_dist":
            cols.append((df["is_redrill"] * df["log_dist"]).to_numpy())
        elif t == "is_redrill_x_incumbent":
            cols.append((df["is_redrill"] * df["incumbent"]).to_numpy())
        else:
            cols.append(df[t].to_numpy().astype(float))
        names.append(t)
    for a in areas:
        cols.append((df["area"] == a).cast(pl.Float64).to_numpy())
        names.append(f"area_{a}")
    for y5 in yr5s:
        cols.append((df["yr5"] == y5).cast(pl.Float64).to_numpy())
        names.append(f"yr5_{y5}")

    X = np.column_stack(cols)
    n_lic_clusters = len(set(cluster_lic.tolist()))
    n_quad_clusters = len(set(cluster_quad.tolist()))

    try:
        m_naive = sm.Logit(y, X).fit(disp=False, maxiter=200)
        m_lic = sm.Logit(y, X).fit(disp=False, maxiter=200, cov_type="cluster", cov_kwds={"groups": cluster_lic})
        m_quad = sm.Logit(y, X).fit(disp=False, maxiter=200, cov_type="cluster", cov_kwds={"groups": cluster_quad})
    except Exception as exc:
        return {"error": str(exc), "n": int(df.height), "events": int(y.sum())}

    coefs = {}
    for idx, nm in enumerate(names):
        if nm in terms:
            p_n = float(m_naive.pvalues[idx])
            p_l = float(m_lic.pvalues[idx])
            p_q = float(m_quad.pvalues[idx])
            wcb_q = None
            if n_quad_clusters < 50:
                wcb_q = wild_cluster_bootstrap_lpm(y, X, cluster_quad, idx, n_draws=9999, seed=42)
            p_list = [p_n, p_l, p_q] + ([wcb_q] if wcb_q is not None else [])
            coefs[nm] = {
                "coef": round(float(m_naive.params[idx]), 4),
                "or": round(math.exp(float(m_naive.params[idx])), 3),
                "se_naive": round(float(m_naive.bse[idx]), 4),
                "p_naive": round(p_n, 4),
                "se_cluster_licence": round(float(m_lic.bse[idx]), 4),
                "p_cluster_licence": round(p_l, 4),
                "se_cluster_quadrant": round(float(m_quad.bse[idx]), 4),
                "p_cluster_quadrant": round(p_q, 4),
                "p_wcb_quadrant_lpm": wcb_q,
                "p_most_conservative": round(max(p_list), 4),
            }
    return {
        "n": int(df.height),
        "events": int(y.sum()),
        "n_licence_clusters": n_lic_clusters,
        "n_quadrant_clusters": n_quad_clusters,
        "coefficients": coefs,
    }


def load_sodir_helpers() -> dict:
    disc_df = pl.read_parquet(CACHE / "discovery.parquet")
    disc_res = pl.read_parquet(CACHE / "discovery_reserves.parquet")
    fld_df = pl.read_parquet(CACHE / "field.parquet")
    fld_res = pl.read_parquet(CACHE / "field_reserves.parquet")
    lic_df = pl.read_parquet(CACHE / "licence.parquet")
    lic_lh = pl.read_parquet(CACHE / "licence_licensee_hst.parquet")
    lic_oh = pl.read_parquet(CACHE / "licence_oper_hst.parquet")
    fac_df = pl.read_parquet(CACHE / "facility_fixed.parquet")
    return {
        "disc": disc_df,
        "disc_res": disc_res,
        "field": fld_df,
        "field_res": fld_res,
        "licence": lic_df,
        "lic_lh": lic_lh,
        "lic_oh": lic_oh,
        "fac": fac_df,
    }


def build_incumbent_lookup(sodir: dict) -> dict[str, list[tuple[str, int, int]]]:
    lic_members: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for df, name_col, dfrom, dto in [
        (sodir["lic_lh"], "cmpLongName", "prlLicenseeDateValidFrom", "prlLicenseeDateValidTo"),
        (sodir["lic_oh"], "cmpLongName", "prlOperDateValidFrom", "prlOperDateValidTo"),
    ]:
        for r in df.iter_rows(named=True):
            prl = str(r.get("prlName") or "").strip()
            op = norm_operator(r.get(name_col))
            y0 = parse_year(r.get(dfrom)) or 1965
            y1 = parse_year(r.get(dto)) or 2099
            if prl and op != "UNKNOWN":
                lic_members[prl].append((op, y0, y1))
    return lic_members


def run_steps_1_2_3_and_5(
    kept_json: dict,
    kept_geo: dict,
    wells_df: pl.DataFrame,
    sodir: dict,
    feat_to_prospect: dict,
    well_periods: dict,
) -> tuple[dict, dict, set[str]]:
    disc_df = sodir["disc"]
    disc_res = sodir["disc_res"]
    fld_res = sodir["field_res"]

    latest_fld = (
        fld_res.sort("fldVersion", descending=True)
        .unique(subset=["fldName"], keep="first")
        .select(["fldName", "fldRecoverableOE"])
    )
    fld_oe = {r["fldName"]: float(r["fldRecoverableOE"]) for r in latest_fld.drop_nulls().iter_rows(named=True)}
    dsc_oe = {r["dscName"]: float(r["dscRecoverableOe"]) for r in disc_res.select(["dscName", "dscRecoverableOe"]).drop_nulls().iter_rows(named=True)}

    commercial_statuses = {
        "PRODUCING",
        "APPROVED FOR PRODUCTION",
        "PLANNING PHASE",
        "DEVELOPMENT LIKELY",
        "PRODUCTION IS LIKELY, BUT UNCLARIFIED",
        "INCLUDED IN OTHER DISCOVERY",
    }

    well_disc_meta: dict[str, dict] = {}
    for r in disc_df.iter_rows(named=True):
        wn = r.get("wlbName")
        dn = r.get("dscName")
        fn = r.get("fldName")
        st = str(r.get("dscCurrentActivityStatus") or "").strip().upper()
        if not wn:
            continue
        oe = dsc_oe.get(dn)
        if oe is None and fn in fld_oe:
            oe = fld_oe[fn]
        is_comm = bool(fn) or (st in commercial_statuses)
        well_disc_meta[wn] = {"oe": oe, "is_commercial": is_comm, "status": st, "field": fn, "discovery": dn}

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
    for row in wc.to_dicts():
        pw = str(row["wlbWell"] or row["wlbWellboreName"]).strip()
        yr = int(row["wlbCompletionYear"])
        eyr = int(row["wlbEntryYear"]) if row.get("wlbEntryYear") and int(row["wlbEntryYear"]) > 0 else yr
        area = str(row["wlbMainArea"] or "UNKNOWN").strip().upper()
        disc = bool(row["is_disc"])
        lon, lat = row["wlbEwDecDeg"], row["wlbNsDecDeg"]
        wname = str(row["wlbWellboreName"]).strip()
        dmeta = well_disc_meta.get(wname, {})
        oe = dmeta.get("oe")
        is_comm = bool(dmeta.get("is_commercial")) or bool(row.get("wlbField"))
        op = norm_operator(row.get("wlbDrillingOperator"))
        prl = str(row.get("wlbProductionLicence") or "").strip()
        hc_ages = set()
        for col in ("wlbAgeWithHc1", "wlbAgeWithHc2", "wlbAgeWithHc3"):
            p_age = norm_period(row.get(col))
            if p_age:
                hc_ages.add(p_age)
        ft_pers = set(well_periods.get(wname, set()))

        if pw not in parent_shelf:
            parent_shelf[pw] = {
                "year": yr,
                "entry_year": eyr,
                "area": area,
                "is_disc": disc,
                "oe": oe,
                "is_comm": is_comm,
                "lon": lon,
                "lat": lat,
                "operator": op,
                "licence": prl,
                "hc_ages": hc_ages,
                "ft_pers": ft_pers,
            }
        else:
            parent_shelf[pw]["is_disc"] = parent_shelf[pw]["is_disc"] or disc
            parent_shelf[pw]["is_comm"] = parent_shelf[pw]["is_comm"] or is_comm
            if oe is not None and (parent_shelf[pw]["oe"] is None or oe > parent_shelf[pw]["oe"]):
                parent_shelf[pw]["oe"] = oe
            parent_shelf[pw]["year"] = min(parent_shelf[pw]["year"], yr) if (yr > 0 and parent_shelf[pw]["year"] > 0) else max(parent_shelf[pw]["year"], yr)
            parent_shelf[pw]["hc_ages"] |= hc_ages
            parent_shelf[pw]["ft_pers"] |= ft_pers

    lic_members = build_incumbent_lookup(sodir)
    prior_discs = [
        (info["year"], float(info["lon"]), float(info["lat"]), info["licence"])
        for info in parent_shelf.values()
        if info["is_disc"] and info["year"] > 0 and info["lon"] is not None and info["lat"] is not None
    ]

    for pw, info in parent_shelf.items():
        if info["lon"] is None or info["lat"] is None or info["year"] <= 0:
            info["dist_km"] = None
            info["incumbent"] = 0
            continue
        best_d, best_lic = 1e9, ""
        for dy, dlon, dlat, dlic in prior_discs:
            if dy < info["year"]:
                d = haversine_km(float(info["lon"]), float(info["lat"]), dlon, dlat)
                if d < best_d:
                    best_d, best_lic = d, dlic
        info["dist_km"] = round(best_d, 2) if best_d < 1e8 else None
        spud_y = info["entry_year"] if info["entry_year"] > 0 else info["year"]
        inc = 0
        if best_lic and best_lic in lic_members:
            for mop, y0, y1 in lic_members[best_lic]:
                if mop == info["operator"] and y0 <= spud_y <= y1:
                    inc = 1
                    break
        info["incumbent"] = inc

    wildcats = wc.drop_nulls(subset=["wlbEwDecDeg", "wlbNsDecDeg"]).to_dicts()
    redrill_pws: set[str] = set()
    redrill_lic_cluster: dict[str, tuple[int, str]] = {}
    redrill_pg_matches: dict[str, list[dict]] = defaultdict(list)
    redrilled_pids: set[str] = set()

    for stem, rec in kept_json.items():
        rdate = str((rec.get("document") or {}).get("date") or "")
        if len(rdate) < 4 or not rdate[:4].isdigit():
            continue
        ryear = int(rdate[:4])
        rlic = str((rec.get("licence") or {}).get("licence_id") or stem)
        for feat in (kept_geo.get(stem) or {}).get("features") or []:
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
            ass = pobj.get("assessments") or []
            pg_val = None
            for a in reversed(ass):
                pv = (a.get("risk") or {}).get("pg")
                if isinstance(pv, (int, float)) and 0 < pv < 0.99:
                    pg_val = float(pv)
                    break
            for w in wildcats:
                if int(w["wlbCompletionYear"]) <= ryear:
                    continue
                wx, wy = float(w["wlbEwDecDeg"]), float(w["wlbNsDecDeg"])
                if minx <= wx <= maxx and miny <= wy <= maxy and pip_geom(wx, wy, geom):
                    pw = str(w.get("wlbWell") or w["wlbWellboreName"]).strip()
                    redrill_pws.add(pw)
                    pid = pobj.get("prospect_id")
                    if pid:
                        redrilled_pids.add(pid)
                    if pw not in redrill_lic_cluster or ryear > redrill_lic_cluster[pw][0]:
                        redrill_lic_cluster[pw] = (ryear, rlic)
                    if pg_val is not None:
                        redrill_pg_matches[pw].append({"pg": pg_val, "periods": p_periods})

    rows = []
    for pw, info in parent_shelf.items():
        if info["dist_km"] is None or info["year"] < 2013 or info["area"] not in ("NORTH SEA", "NORWEGIAN SEA", "BARENTS SEA"):
            continue
        quad = pw.split("/")[0].strip()
        lic_cl = redrill_lic_cluster[pw][1] if pw in redrill_lic_cluster else f"NONREDRILL_{pw}"
        oe = info["oe"] or 0.0
        rows.append(
            {
                "pw": pw,
                "year": info["year"],
                "area": info["area"],
                "yr5": (info["year"] // 5) * 5,
                "quad": quad,
                "lic_cluster": lic_cl,
                "is_redrill": 1.0 if pw in redrill_pws else 0.0,
                "log_dist": math.log1p(info["dist_km"]),
                "dist_km": info["dist_km"],
                "incumbent": float(info["incumbent"]),
                "y_tech": 1.0 if info["is_disc"] else 0.0,
                "y_mat3": 1.0 if (info["is_disc"] and oe >= 3.0) else 0.0,
                "y_mat1": 1.0 if (info["is_disc"] and oe >= 1.0) else 0.0,
                "y_mat5": 1.0 if (info["is_disc"] and oe >= 5.0) else 0.0,
                "y_comm": 1.0 if (info["is_disc"] and info["is_comm"]) else 0.0,
            }
        )

    df_all = pl.DataFrame(rows)
    df_comm = df_all.filter(pl.col("year") <= 2021)

    step123 = {}
    for label, sub_df, ycol in [
        ("technical_2013plus", df_all, "y_tech"),
        ("material_3msmo3_2013plus", df_all, "y_mat3"),
        ("material_1msmo3_2013plus", df_all, "y_mat1"),
        ("material_5msmo3_2013plus", df_all, "y_mat5"),
        ("commercial_2013_2021", df_comm, "y_comm"),
    ]:
        cl_l = sub_df["lic_cluster"].to_numpy()
        cl_q = sub_df["quad"].to_numpy()
        step123[label] = {
            "model1_main": fit_logit_with_se_variants(sub_df, ycol, ["is_redrill", "log_dist"], cl_l, cl_q),
            "model2_interaction": fit_logit_with_se_variants(sub_df, ycol, ["is_redrill", "log_dist", "is_redrill_x_log_dist"], cl_l, cl_q),
        }
        if label in ("technical_2013plus", "material_3msmo3_2013plus", "commercial_2013_2021"):
            step123[label]["model3_incumbent"] = fit_logit_with_se_variants(
                sub_df,
                ycol,
                ["is_redrill", "log_dist", "is_redrill_x_log_dist", "incumbent", "is_redrill_x_incumbent"],
                cl_l,
                cl_q,
            )

    step123["incumbent_summary"] = {
        "redrill_incumbent_rate": round(float(df_all.filter(pl.col("is_redrill") == 1)["incumbent"].mean()), 3),
        "non_redrill_incumbent_rate": round(float(df_all.filter(pl.col("is_redrill") == 0)["incumbent"].mean()), 3),
        "near_field_redrill_incumbent_rate": round(float(df_all.filter((pl.col("is_redrill") == 1) & (pl.col("dist_km") <= 15))["incumbent"].mean()), 3),
        "near_field_non_redrill_incumbent_rate": round(float(df_all.filter((pl.col("is_redrill") == 0) & (pl.col("dist_km") <= 15))["incumbent"].mean()), 3),
    }

    cal_pairs = []
    for pw in redrill_pws:
        info = parent_shelf.get(pw)
        if not info or info["year"] <= 0 or info["dist_km"] is None:
            continue
        cands = redrill_pg_matches.get(pw) or []
        if not cands:
            continue
        ft_pers = info["ft_pers"]
        matched = [c for c in cands if c["periods"] and (c["periods"] & ft_pers)]
        chosen = matched if matched else cands
        mean_pg = sum(c["pg"] for c in chosen) / len(chosen)
        target_pers = set().union(*(c["periods"] for c in chosen))
        if target_pers:
            hit_tech = 1.0 if (info["is_disc"] and bool(info["hc_ages"] & target_pers)) else 0.0
        else:
            hit_tech = 1.0 if info["is_disc"] else 0.0
        oe_val = info["oe"] or 0.0
        hit_mat1 = 1.0 if (hit_tech == 1.0 and oe_val >= 1.0) else 0.0
        hit_mat3 = 1.0 if (hit_tech == 1.0 and oe_val >= 3.0) else 0.0
        cal_pairs.append({"pw": pw, "dist_km": info["dist_km"], "pg": mean_pg, "hit_tech": hit_tech, "hit_mat1": hit_mat1, "hit_mat3": hit_mat3})

    rng = np.random.default_rng(42)

    def boot_ratio(sub: list[dict], key: str = "hit_mat3") -> dict:
        n = len(sub)
        if n == 0:
            return {"n": 0}
        pgs = np.array([x["pg"] for x in sub])
        hits = np.array([x[key] for x in sub])
        ratio = float(hits.mean() / pgs.mean())
        idx = rng.integers(0, n, size=(9999, n))
        b_ratios = hits[idx].mean(axis=1) / pgs[idx].mean(axis=1)
        lo, hi = float(np.percentile(b_ratios, 2.5)), float(np.percentile(b_ratios, 97.5))
        return {
            "n": n,
            "mean_stated_pg": round(float(pgs.mean()), 4),
            "observed_hit_rate": round(float(hits.mean()), 4),
            "obs_over_stated_ratio": round(ratio, 3),
            "ci95": [round(lo, 3), round(hi, 3)],
            "ci_excludes_1": bool(lo > 1.0 or hi < 1.0),
        }

    step5 = {
        "technical_target_hit": {
            "near_field_le15km": boot_ratio([x for x in cal_pairs if x["dist_km"] <= 15.0], "hit_tech"),
            "far_field_gt15km": boot_ratio([x for x in cal_pairs if x["dist_km"] > 15.0], "hit_tech"),
        },
        "material_1msmo3_target_hit": {
            "all": boot_ratio(cal_pairs, "hit_mat1"),
            "near_field_le15km": boot_ratio([x for x in cal_pairs if x["dist_km"] <= 15.0], "hit_mat1"),
            "far_field_gt15km": boot_ratio([x for x in cal_pairs if x["dist_km"] > 15.0], "hit_mat1"),
        },
        "material_3msmo3_target_hit": {
            "all": boot_ratio(cal_pairs, "hit_mat3"),
            "near_field_le15km": boot_ratio([x for x in cal_pairs if x["dist_km"] <= 15.0], "hit_mat3"),
            "far_field_gt15km": boot_ratio([x for x in cal_pairs if x["dist_km"] > 15.0], "hit_mat3"),
        },
    }
    return step123, step5, redrilled_pids


def run_step4_dry_hole_reconciliation(kept_json: dict, wells_df: pl.DataFrame) -> dict:
    well_year_map = {}
    well_area_map = {}
    for r in wells_df.select(["wlbWellboreName", "wlbCompletionYear", "wlbMainArea"]).iter_rows(named=True):
        if r["wlbWellboreName"] and r["wlbCompletionYear"]:
            well_year_map[str(r["wlbWellboreName"]).strip()] = int(r["wlbCompletionYear"])
            well_area_map[str(r["wlbWellboreName"]).strip()] = str(r["wlbMainArea"] or "").strip().upper()

    def map_to_sodir_3(text: str) -> set[str]:
        t = text.lower()
        cats = set()
        good_res = any(k in t for k in ("excellent reservoir", "good reservoir", "reservoir was of excellent", "reservoir was of good", "proved sand", "encountered good", "good quality sand"))
        bad_res = any(k in t for k in ("no reservoir", "reservoir absent", "no sand", "sand absent", "lacking reservoir", "poor reservoir", "poorer reservoir", "tight", "absent across", "no reservoir development", "reservoir sandstone was not", "not reservoir quality", "shale-out", "pinch-out", "porosity", "permeability"))
        if bad_res or ("reservoir" in t and not good_res and any(k in t for k in ("fail", "lack", "poor", "absent", "thin", "not"))):
            cats.add("Reservoir")
        if any(k in t for k in ("charge", "source", "migration", "maturity", "kitchen", "shadow", "timing")):
            cats.add("Charge")
        if any(k in t for k in ("trap", "seal", "retention", "breach", "leak", "fault seal", "top seal", "topseal", "lateral seal", "closure", "spilled", "tilting", "uplift", "residual", "paleo-column", "paleo column", "paleocolumn", "underfilled", "gas expansion")):
            cats.add("Trap")
        return cats

    dry_records = []
    for stem, rec in kept_json.items():
        basin = str((rec.get("licence") or {}).get("area") or "Unknown")
        rdate = parse_year((rec.get("document") or {}).get("date"))
        doc_url = (rec.get("document") or {}).get("source_url")
        for p in rec.get("prospects") or []:
            st = str(p.get("status_at_report") or "").lower()
            if "dry" not in st:
                continue
            w_years = []
            for ev in p.get("history_events") or []:
                wn = str(ev.get("well") or ev.get("well_name") or "").strip()
                if wn in well_year_map:
                    w_years.append(well_year_map[wn])
                ey = parse_year(ev.get("date"))
                if ey:
                    w_years.append(ey)
            concl = p.get("conclusion") or {}
            blob = " ".join(
                [
                    str(concl.get("text") or ""),
                    str(concl.get("summary") or ""),
                ]
            ).strip()
            cats = map_to_sodir_3(blob)
            if not cats:
                continue
            yr = min(w_years) if w_years else rdate
            dry_records.append(
                {
                    "prospect_id": p.get("prospect_id"),
                    "name": p.get("name"),
                    "basin": basin,
                    "year": yr,
                    "categories": sorted(cats),
                    "source_page": (concl.get("source") or {}).get("page") or (p.get("summary_source") or {}).get("page"),
                    "doc_url": doc_url,
                    "text_snippet": blob[:280],
                }
            )

    win = [r for r in dry_records if r["year"] is not None and 2007 <= r["year"] <= 2019]

    def agg_weights(sub: list[dict]) -> dict:
        w = Counter()
        for r in sub:
            share = 1.0 / len(r["categories"])
            for c in r["categories"]:
                w[c] += share
        tot = sum(w.values()) or 1.0
        return {
            "n_dry_holes": len(sub),
            "Charge_pct": round(100 * w["Charge"] / tot, 1),
            "Trap_pct": round(100 * w["Trap"] / tot, 1),
            "Reservoir_pct": round(100 * w["Reservoir"] / tot, 1),
        }

    by_basin = {}
    for b in ("North Sea", "Norwegian Sea", "Barents Sea"):
        by_basin[b] = agg_weights([r for r in win if r["basin"] == b])

    rng_oos = random.Random(123)
    sample_20_oos = rng_oos.sample(win, min(20, len(win)))
    return {
        "window_2007_2019_all": agg_weights(win),
        "window_2007_2019_by_basin": by_basin,
        "sodir_rr2020_factbox34_north_sea": {"Charge_pct": 47.0, "Trap_pct": 29.0, "Reservoir_pct": 24.0, "source": "SODIR Resource Report 2020, Fact box 3.4 (targets)"},
        "audit_sample_20_oos_seed123": sample_20_oos,
    }


def run_steps_6_7_8_inventory(
    kept_json: dict,
    pid_to_features: dict,
    redrilled_pids: set[str],
    sodir: dict,
    wells_df: pl.DataFrame,
    step5_cal: dict,
) -> dict:
    fac_df = sodir["fac"]
    fld_df = sodir["field"]
    disc_df = sodir["disc"]
    disc_res = sodir["disc_res"]
    fld_res = sodir["field_res"]
    lic_df = sodir["licence"]

    all_hosts = []
    for r in fac_df.iter_rows(named=True):
        if str(r.get("fclSurface") or "").upper() != "Y":
            continue
        try:
            lat = float(r["fclNsDeg"]) + float(r["fclNsMin"]) / 60.0 + float(r["fclNsSec"]) / 3600.0
            lon = float(r["fclEwDeg"]) + float(r["fclEwMin"]) / 60.0 + float(r["fclEwSec"]) / 3600.0
            if str(r.get("fclEwCode") or "").upper() == "W":
                lon = -lon
        except (TypeError, ValueError):
            continue
        phase = str(r.get("fclPhase") or "").upper()
        fname = str(r.get("fclName") or "")
        ffld = str(r.get("fclBelongsToName") or "")
        sy = parse_year(r.get("fclStartupDate"))
        gas_ok = ffld.upper() not in GAS_REINJECTION_ONLY and "GOLIAT" not in fname.upper() and "CASTBERG" not in fname.upper()
        all_hosts.append({"lon": lon, "lat": lat, "name": fname, "field": ffld, "phase": phase, "startup_year": sy, "gas_ok": gas_ok})

    in_service_hosts = [h for h in all_hosts if h["phase"] == "IN SERVICE"]

    approved_hosts = list(in_service_hosts)
    latest_fld = fld_res.sort("fldVersion", descending=True).unique(subset=["fldName"], keep="first")
    fld_oe_map = {r["fldName"]: float(r["fldRecoverableOE"]) for r in latest_fld.select(["fldName", "fldRecoverableOE"]).drop_nulls().iter_rows(named=True)}
    dsc_oe_map = {r["dscName"]: float(r["dscRecoverableOe"]) for r in disc_res.select(["dscName", "dscRecoverableOe"]).drop_nulls().iter_rows(named=True)}
    wcoord = {
        r["wlbWellboreName"]: (float(r["wlbEwDecDeg"]), float(r["wlbNsDecDeg"]))
        for r in wells_df.select(["wlbWellboreName", "wlbEwDecDeg", "wlbNsDecDeg"]).drop_nulls().iter_rows(named=True)
    }
    pdo_rows = []
    for r in disc_df.iter_rows(named=True):
        st = str(r.get("dscCurrentActivityStatus") or "").upper()
        yr = r.get("dscDiscoveryYear")
        if not yr or int(yr) < 2010:
            continue
        if not (st in ("PRODUCING", "APPROVED FOR PRODUCTION") or r.get("fldName")):
            continue
        wn = r.get("wlbName")
        if wn not in wcoord:
            continue
        oe = dsc_oe_map.get(r.get("dscName"))
        if oe is None and r.get("fldName") in fld_oe_map:
            oe = fld_oe_map[r["fldName"]]
        if not oe or oe <= 0:
            continue
        hc = str(r.get("dscHcType") or "").upper()
        fluid = "gas" if ("GAS" in hc and "OIL" not in hc) else "oil"
        lon, lat = wcoord[wn]
        fld_self = str(r.get("fldName") or "").upper()
        pool = [h for h in in_service_hosts if (h["gas_ok"] if fluid == "gas" else True) and h["field"].upper() != fld_self]
        if not pool:
            continue
        dkm = min(haversine_km(lon, lat, h["lon"], h["lat"]) for h in pool)
        if dkm < 2.0:
            continue
        pdo_rows.append({"fluid": fluid, "is_gas": 1.0 if fluid == "gas" else 0.0, "oe_msmo3": oe, "log_oe": math.log(oe), "dist_km": dkm})

    df_p = pd.DataFrame(pdo_rows)
    qr = smf.quantreg("log_oe ~ dist_km + is_gas", df_p).fit(q=0.10)
    raw_slope = float(qr.params["dist_km"])
    envelopes = {
        "method": "pooled_tieback_only_quantreg_tau010",
        "n_tiebacks": len(pdo_rows),
        "n_oil": sum(1 for x in pdo_rows if x["fluid"] == "oil"),
        "n_gas": sum(1 for x in pdo_rows if x["fluid"] == "gas"),
        "intercept": round(float(qr.params["Intercept"]), 4),
        "raw_slope_dist_km": round(raw_slope, 5),
        "gas_offset": round(float(qr.params["is_gas"]), 4),
        "monotone_slope_used": round(max(0.0, raw_slope), 5),
        "uninformative_negative_slope": bool(raw_slope <= 0.0),
    }

    def envelope_threshold(fluid: str, dist_km: float | None) -> float:
        slope_use = max(0.0, raw_slope)
        gas_off = float(qr.params["is_gas"]) if fluid == "gas" else 0.0
        d = min(dist_km or 0.0, 250.0)
        return math.exp(float(qr.params["Intercept"]) + slope_use * d + gas_off)

    active_feats = json.loads((CACHE / "active_licences_616.geojson").read_text(encoding="utf-8")).get("features") or []
    lic_grant_year = {}
    for r in lic_df.select(["prlName", "prlDateGranted", "prlLicensingActivityName"]).iter_rows(named=True):
        if r.get("prlName"):
            lic_grant_year[str(r["prlName"]).strip()] = (parse_year(r.get("prlDateGranted")), str(r.get("prlLicensingActivityName") or ""))

    apa2025_count = sum(1 for _, (_, act) in lic_grant_year.items() if "2025" in act and ("TFO" in act.upper() or "APA" in act.upper()))

    active_polys = []
    active_centroids_with_yr = []
    for f in active_feats:
        g = f.get("geometry")
        bb = geom_bbox(g)
        if bb:
            props = f.get("properties") or {}
            prl = str(props.get("prlName") or "").strip()
            gy, _ = lic_grant_year.get(prl, (None, ""))
            active_polys.append((bb, g, prl, props.get("cmpLongName")))
            c = geom_centroid(g)
            if c and gy:
                active_centroids_with_yr.append((c[0], c[1], gy, prl))

    apa_feats = json.loads((CACHE / "apa_gross_603.geojson").read_text(encoding="utf-8")).get("features") or []
    apa_polys = [(geom_bbox(f.get("geometry")), f.get("geometry")) for f in apa_feats if geom_bbox(f.get("geometry"))]

    comm_nt_tags = {"volume_too_small", "commercial", "economics", "infrastructure", "partner_disagreement", "licence_expiry", "outside_licence", "portfolio_prioritization", "gas_market", "rig_availability"}
    geo_tags = {"seal_risk", "trap_risk", "charge_risk", "migration_risk", "reservoir_risk", "source_risk", "timing_risk", "retention_risk", "high_risk"}

    nf_cal = step5_cal["material_3msmo3_target_hit"]["near_field_le15km"]
    ff_cal = step5_cal["material_3msmo3_target_hit"]["far_field_gt15km"]
    nf_mult = nf_cal["obs_over_stated_ratio"] if nf_cal.get("ci_excludes_1") else 1.0
    ff_mult = ff_cal["obs_over_stated_ratio"] if ff_cal.get("ci_excludes_1") else 1.0

    inv_rows = []
    inv_features = []
    seen_name_basin = set()
    candidates = []

    for rec in kept_json.values():
        lic_id = (rec.get("licence") or {}).get("licence_id")
        basin = (rec.get("licence") or {}).get("area") or "Unknown"
        op = (rec.get("document") or {}).get("author_company")
        ryear = parse_year((rec.get("document") or {}).get("date"))
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
                    best_v, best_obj = mv, v
            if best_v is None:
                continue
            feats = pid_to_features.get(pid) or []
            poly_feat = next((f for f in feats if (f.get("geometry") or {}).get("type") in ("Polygon", "MultiPolygon")), feats[0] if feats else None)
            if not poly_feat:
                continue
            candidates.append((pg * best_v, pid, p, lic_id, basin, op, ryear, doc_url, pg, best_v, best_obj, poly_feat))

    candidates.sort(key=lambda x: x[0], reverse=True)

    for _, pid, p, lic_id, basin, op, ryear, doc_url, pg, best_v, best_obj, poly_feat in candidates:
        key = (str(p.get("name") or "").strip().lower(), basin)
        if key in seen_name_basin:
            continue
        seen_name_basin.add(key)
        geom = poly_feat.get("geometry")
        pts = sample_polygon_points(geom, grid_n=7)
        if not pts:
            continue
        open_pts_no, apa_pts, no_pts = 0, 0, 0
        for px, py in pts:
            in_apa_pt = any(minx <= px <= maxx and miny <= py <= maxy and pip_geom(px, py, g) for (minx, maxx, miny, maxy), g in apa_polys)
            in_act = any(minx <= px <= maxx and miny <= py <= maxy and pip_geom(px, py, g) for (minx, maxx, miny, maxy), g, _, _ in active_polys)
            if in_apa_pt:
                apa_pts += 1
            if in_apa_pt or in_act:
                no_pts += 1
                if not in_act:
                    open_pts_no += 1
        no_share = no_pts / len(pts)
        open_frac = (open_pts_no / no_pts) if no_pts > 0 else 0.0
        in_apa = (apa_pts / len(pts)) >= 0.5
        if open_frac < 0.5 or not in_apa:
            continue

        cx, cy = geom_centroid(geom) or pts[0]
        dist_obj = (best_obj or {}).get("distribution") or {}
        phase_str = str((best_obj or {}).get("phase") or "").lower()
        is_gas = "gas" in phase_str or ("gas" in str(dist_obj.get("original_text") or "").lower() and "oil" not in phase_str)
        fluid = "gas" if is_gas else "oil"

        now_pool = [h for h in approved_hosts if (h["gas_ok"] if is_gas else True)]
        best_now = min(now_pool, key=lambda h: haversine_km(cx, cy, h["lon"], h["lat"])) if now_pool else None
        dist_now = round(haversine_km(cx, cy, best_now["lon"], best_now["lat"]), 1) if best_now else None
        host_name = f"{best_now['name']} ({best_now['field']})" if (best_now and best_now["field"]) else (best_now["name"] if best_now else None)
        host_fld_key = str(best_now["field"] if best_now else "").upper()
        host_end, host_end_src = HOST_END_YEARS.get(host_fld_key, ("unknown", ""))

        rel_pool = [h for h in all_hosts if (h["gas_ok"] if is_gas else True) and h["startup_year"] is not None and (ryear is None or h["startup_year"] <= ryear)]
        best_rel = min(rel_pool, key=lambda h: haversine_km(cx, cy, h["lon"], h["lat"])) if rel_pool else None
        dist_rel = round(haversine_km(cx, cy, best_rel["lon"], best_rel["lat"]), 1) if best_rel else None

        concl = p.get("conclusion") or {}
        reasons = set(str(x).lower() for x in (concl.get("reasons_not_drilled") or []))
        concl_txt = f"{concl.get('text') or ''} {concl.get('summary') or ''} {p.get('summary') or ''}"
        has_comm_nt = bool(reasons & comm_nt_tags)
        has_geo = bool(reasons & geo_tags)
        tier = "Tier_A" if (has_comm_nt and not has_geo) else "Tier_B"

        infra_cited = bool(reasons & {"infrastructure", "infrastructure_distance", "dependency_on_infrastructure", "gas_market"}) or any(
            k in concl_txt.lower() for k in ("infrastructure", "tie-back", "tieback", "host", "distance", "capacity", "ullage", "pipeline")
        )
        changed_circ = bool(
            infra_cited
            and dist_rel is not None
            and dist_now is not None
            and dist_now <= 50.0
            and ((dist_rel - dist_now >= 20.0) or (dist_rel > 50.0 and dist_now <= 50.0))
        )

        thresh = envelope_threshold(fluid, dist_now)
        below_econ = bool(best_v < thresh)

        years_open = (2026 - ryear) if ryear else None
        apa_rounds = max(0, (2025 if apa2025_count > 0 else 2024) - ryear) if ryear else None
        nearby_awards = sum(1 for lx, ly, gy, _ in active_centroids_with_yr if ryear and gy > ryear and haversine_km(cx, cy, lx, ly) <= 20.0)

        rerisked_pg = round(min(0.95, pg * (nf_mult if (dist_now is not None and dist_now <= 15.0) else ff_mult)), 3)

        row_dict = {
            "prospect_id": pid,
            "name": p.get("name"),
            "licence": lic_id,
            "relinq_year": ryear,
            "operator": op,
            "basin": basin,
            "tier": tier,
            "fluid": fluid,
            "stated_pg": round(pg, 3),
            "re_risked_pg": rerisked_pg,
            "unrisked_msmo3": round(best_v, 2),
            "unrisked_mmboe": round(best_v * 6.2898, 1),
            "risked_mmboe": round(pg * best_v * 6.2898, 1),
            "re_risked_mmboe": round(rerisked_pg * best_v * 6.2898, 1),
            "no_area_pct": round(no_share * 100, 1),
            "open_pct": round(open_frac * 100, 1),
            "nearest_host": host_name,
            "dist_now_km": dist_now,
            "dist_at_relinq_km": dist_rel,
            "host_end_year": host_end,
            "host_end_source": host_end_src,
            "economic_envelope_msmo3": round(thresh, 2),
            "economic_flag": "below_p10_envelope" if below_econ else "above_envelope",
            "changed_circumstances_flag": changed_circ,
            "new_host_startup_year": best_now["startup_year"] if (changed_circ and best_now) else None,
            "years_open": years_open,
            "apa_rounds_since": apa_rounds,
            "nearby_awards_since": nearby_awards,
            "reasons_not_drilled": "; ".join(sorted(reasons)),
            "conclusion_snippet": concl_txt[:220].replace("\n", " "),
        }
        inv_rows.append(row_dict)
        inv_features.append({"type": "Feature", "geometry": geom, "properties": row_dict})

    if inv_rows:
        with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(inv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(inv_rows)
        OUT_GEOJSON.write_text(json.dumps({"type": "FeatureCollection", "features": inv_features}), encoding="utf-8")

    below_rows = [r for r in inv_rows if r["economic_flag"] == "below_p10_envelope"]
    changed_rows = [r for r in inv_rows if r["changed_circumstances_flag"]]
    tier_a_rows = [r for r in inv_rows if r["tier"] == "Tier_A"]
    rng = random.Random(42)
    tier_a_audit_30 = rng.sample(tier_a_rows, min(30, len(tier_a_rows)))

    return {
        "snapshot_date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "apa_2025_awards_in_snapshot": apa2025_count,
        "total_apa_open_prospects": len(inv_rows),
        "step6_economic_screen": {
            "pdo_since_2010_count": len(pdo_rows),
            "envelopes": envelopes,
            "flagged_below_envelope_count": len(below_rows),
            "flagged_risked_mmboe_removed": round(sum(r["risked_mmboe"] for r in below_rows), 1),
            "remaining_above_envelope_count": len(inv_rows) - len(below_rows),
            "remaining_risked_bboe": round(sum(r["risked_mmboe"] for r in inv_rows if r["economic_flag"] == "above_envelope") / 1000.0, 2),
        },
        "step7_changed_circumstances": {
            "flagged_count": len(changed_rows),
            "flagged_prospects": changed_rows[:15],
        },
        "step8_inventory_stats": {
            "median_years_open": sorted(r["years_open"] for r in inv_rows if r["years_open"] is not None)[len(inv_rows) // 2],
            "pct_with_nearby_awards_since": round(100 * sum(1 for r in inv_rows if r["nearby_awards_since"] > 0) / max(1, len(inv_rows)), 1),
            "top_14_for_table": inv_rows[:14],
            "tier_a_audit_30_seed42": tier_a_audit_30,
        },
    }


def main() -> None:
    raw_json, raw_geo = load_raw_records()
    kept_json, kept_geo, _ = deduplicate_records(raw_json, raw_geo)
    wells_df = pl.read_parquet(DEFAULT_FACTPAGES_WELLS)
    sodir = load_sodir_helpers()
    unit_to_period = build_unit_to_period()
    well_periods = build_well_penetrated_periods(unit_to_period)
    feat_to_prospect, pid_to_features = build_prospect_feature_maps(kept_json, kept_geo)

    step123, step5, redrilled_pids = run_steps_1_2_3_and_5(
        kept_json, kept_geo, wells_df, sodir, feat_to_prospect, well_periods
    )
    step4 = run_step4_dry_hole_reconciliation(kept_json, wells_df)
    step678 = run_steps_6_7_8_inventory(
        kept_json, pid_to_features, redrilled_pids, sodir, wells_df, step5
    )

    out = {
        "steps_1_2_3_regressions": step123,
        "step_4_dry_hole_reconciliation": step4,
        "step_5_rerisk_calibration": step5,
        "steps_6_7_8_inventory": step678,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("=== STEPS 1-3: CLUSTER-ROBUST & INCUMBENT REGRESSIONS ===")
    for k, v in step123.items():
        if k == "incumbent_summary":
            print("incumbent_summary:", v)
            continue
        print(f"\n[{k}]")
        for mk, mv in v.items():
            print(f"  {mk}: n={mv.get('n')}, events={mv.get('events')}, lic_cl={mv.get('n_licence_clusters')}, quad_cl={mv.get('n_quadrant_clusters')}")
            for ck, cv in (mv.get("coefficients") or {}).items():
                print(f"    {ck:24s} coef={cv['coef']:+.3f} OR={cv['or']} | p_naive={cv['p_naive']} p_lic={cv['p_cluster_licence']} p_quad={cv['p_cluster_quadrant']} p_wcb={cv['p_wcb_quadrant_lpm']} -> MAX_P={cv['p_most_conservative']}")

    print("\n=== STEP 4: DRY-HOLE RECONCILIATION (2007-2019) ===")
    print(json.dumps({k: v for k, v in step4.items() if not k.startswith("audit_sample")}, indent=2))

    print("\n=== STEP 5: REDRILL RE-RISKING CALIBRATION ===")
    print(json.dumps(step5, indent=2))

    print("\n=== STEPS 6-8: ECONOMIC SCREEN, CHANGED CIRCUMSTANCES & INVENTORY ===")
    print(json.dumps({k: v for k, v in step678.items() if k != "step8_inventory_stats"}, indent=2))
    print("step8 summary:", {k: v for k, v in step678["step8_inventory_stats"].items() if k not in ("top_14_for_table", "tier_a_audit_30_seed42")})


if __name__ == "__main__":
    main()
