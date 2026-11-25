import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl

ROOT = Path(r"C:\Users\philip\Documents\ncs-relinquished-atlas")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "analyses"))

from loader import (
    DEFAULT_FACTPAGES_WELLS,
    deduplicate_records,
    load_raw_records,
    safe_canonical_volume_msmo3,
)

FIG_DIR = ROOT / "reports" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "#fbfcfd",
        "axes.edgecolor": "#cbd5e1",
        "axes.linewidth": 0.9,
        "axes.grid": True,
        "grid.color": "#e2e8f0",
        "grid.linestyle": "--",
        "grid.linewidth": 0.6,
        "font.family": "DejaVu Sans",
        "font.size": 9.5,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.labelsize": 9.5,
    }
)


def save_both(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIG_DIR / f"{stem}.png", dpi=220)
    fig.savefig(FIG_DIR / f"{stem}.svg")
    plt.close(fig)


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    return max(0.0, center - half), min(1.0, center + half)


def polygon_centroid(geom: dict) -> tuple[float, float] | None:
    if not geom or not geom.get("coordinates"):
        return None
    gtype = geom.get("type")
    coords = geom["coordinates"]
    pts = []
    if gtype == "Point":
        pts = [coords]
    elif gtype == "Polygon":
        pts = coords[0]
    elif gtype == "MultiPolygon":
        pts = max((p[0] for p in coords if p), key=len, default=[])
    if not pts:
        return None
    xs = [p[0] for p in pts if len(p) >= 2]
    ys = [p[1] for p in pts if len(p) >= 2]
    if not xs:
        return None
    return float(np.mean(xs)), float(np.mean(ys))


def build_fig1(t1: dict, t2: dict, kept_geo: dict) -> None:
    fig, (ax_map, ax_cal) = plt.subplots(1, 2, figsize=(12.2, 5.2), dpi=220)

    all_lons, all_lats = [], []
    for gj in kept_geo.values():
        for feat in gj.get("features") or []:
            props = feat.get("properties") or {}
            if props.get("layer") in ("prospect", "lead"):
                c = polygon_centroid(feat.get("geometry"))
                if c:
                    all_lons.append(c[0])
                    all_lats.append(c[1])

    ax_map.scatter(
        all_lons,
        all_lats,
        s=5,
        color="#cbd5e1",
        alpha=0.55,
        linewidths=0,
        label=f"Relinquished polygons (n={len(all_lons):,})",
        zorder=1,
    )

    wells_df = pl.read_parquet(DEFAULT_FACTPAGES_WELLS)
    well_coords = {}
    for row in wells_df.select(
        ["wlbWellboreName", "wlbEwDecDeg", "wlbNsDecDeg", "wlbField"]
    ).iter_rows(named=True):
        if row["wlbEwDecDeg"] is not None and row["wlbNsDecDeg"] is not None:
            well_coords[row["wlbWellboreName"]] = (
                float(row["wlbEwDecDeg"]),
                float(row["wlbNsDecDeg"]),
                row["wlbField"],
            )

    top_hits = t1.get("top_25_ones_that_got_away") or []
    wells_full = wells_df.select(
        ["wlbWellboreName", "wlbEwDecDeg", "wlbNsDecDeg", "wlbField", "wlbCompletionYear", "wlbPurpose", "wlbContent", "wlbDiscovery"]
    ).drop_nulls(subset=["wlbEwDecDeg", "wlbNsDecDeg", "wlbCompletionYear"])

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
        gt = geom.get("type")
        cs = geom.get("coordinates")
        if gt == "Polygon":
            return pip_ring(px, py, cs[0]) and not any(pip_ring(px, py, h) for h in cs[1:])
        if gt == "MultiPolygon":
            return any(pip_ring(px, py, p[0]) and not any(pip_ring(px, py, h) for h in p[1:]) for p in cs)
        return False

    wildcats = [
        r for r in wells_full.iter_rows(named=True)
        if str(r.get("wlbPurpose") or "").upper() == "WILDCAT"
    ]
    disc_wells = {}
    dry_wells = {}
    field_stars = {}
    for stem, gj in kept_geo.items():
        rdate = str(((gj.get("metadata") or {}).get("source") or {}).get("collection", {}).get("metadata", {}).get("sources", [{}])[0].get("report_date") or "")
        if len(rdate) < 4 or not rdate[:4].isdigit():
            continue
        ryear = int(rdate[:4])
        for feat in gj.get("features") or []:
            props = feat.get("properties") or {}
            geom = feat.get("geometry")
            if props.get("layer") not in ("prospect", "lead") or not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
                continue
            cs = geom["coordinates"]
            pts = cs[0] if geom["type"] == "Polygon" else [pt for p in cs for pt in p[0]]
            xs = [pt[0] for pt in pts]
            ys = [pt[1] for pt in pts]
            minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
            for w in wildcats:
                if w["wlbCompletionYear"] <= ryear:
                    continue
                wx, wy = float(w["wlbEwDecDeg"]), float(w["wlbNsDecDeg"])
                if not (minx <= wx <= maxx and miny <= wy <= maxy):
                    continue
                if pip_geom(wx, wy, geom):
                    wn = w["wlbWellboreName"]
                    cnt = str(w.get("wlbContent") or "").upper()
                    is_disc = any(k in cnt for k in ("OIL", "GAS", "COND")) and "SHOW" not in cnt
                    if is_disc:
                        disc_wells[wn] = (wx, wy)
                        if w.get("wlbField") in ("BERLING", "BESTLA", "DUVA", "DVALIN"):
                            field_stars[w["wlbField"]] = (wx, wy)
                    else:
                        if wn not in disc_wells:
                            dry_wells[wn] = (wx, wy)

    disc_lon = [v[0] for v in disc_wells.values()]
    disc_lat = [v[1] for v in disc_wells.values()]
    dry_lon = [v[0] for v in dry_wells.values()]
    dry_lat = [v[1] for v in dry_wells.values()]

    if dry_lon:
        ax_map.scatter(
            dry_lon,
            dry_lat,
            s=28,
            color="#dc2626",
            alpha=0.8,
            edgecolors="white",
            linewidths=0.4,
            label=f"Post-relinq. dry wildcats (n={len(dry_lon)})",
            zorder=3,
        )
    if disc_lon:
        ax_map.scatter(
            disc_lon,
            disc_lat,
            s=36,
            color="#16a34a",
            alpha=0.9,
            edgecolors="white",
            linewidths=0.5,
            label=f"Post-relinq. discoveries (n={len(disc_lon)})",
            zorder=4,
        )

    star_offsets = {
        "BERLING": (1.4, -0.3),
        "BESTLA": (1.4, -0.4),
        "DUVA": (1.4, 0.5),
        "DVALIN": (1.4, 0.6),
    }
    for fld, (lon, lat) in sorted(field_stars.items()):
        ax_map.scatter(
            [lon],
            [lat],
            s=140,
            marker="*",
            color="#f59e0b",
            edgecolors="#1e293b",
            linewidths=0.8,
            zorder=6,
        )
        dx, dy = star_offsets.get(fld, (1.2, 0.4))
        ax_map.annotate(
            fld,
            xy=(lon, lat),
            xytext=(lon + dx, lat + dy),
            fontsize=8.2,
            fontweight="bold",
            color="#0f172a",
            arrowprops={"arrowstyle": "-", "color": "#475569", "lw": 0.7},
            zorder=7,
        )

    ax_map.set_xlim(0.5, 34.5)
    ax_map.set_ylim(56.0, 74.5)
    ax_map.set_xlabel("Longitude (deg E)")
    ax_map.set_ylabel("Latitude (deg N)")
    ax_map.set_title("A. Spatial Point-in-Polygon Join (Relinquished -> SODIR)")
    ax_map.legend(loc="lower right", fontsize=8, frameon=True, facecolor="white")

    cal_strict = t2["calibration"]["strict_in_licence_exploration"]
    bins = cal_strict.get("bins") or []
    px, py, yerr_lo, yerr_hi = [], [], [], []
    for b in bins:
        n = b.get("n", 0)
        k = b.get("discoveries", 0)
        mp = b.get("mean_pg", b.get("mean_pred_pg"))
        if n > 0 and mp is not None:
            pred = mp * 100.0 if mp <= 1.0 else mp
            act = (k / n) * 100.0
            lo, hi = wilson_ci(k, n)
            px.append(pred)
            py.append(act)
            yerr_lo.append(act - lo * 100.0)
            yerr_hi.append(hi * 100.0 - act)

    ax_cal.plot([0, 75], [0, 75], linestyle="--", color="#64748b", lw=1.2, label="Perfect calibration")
    ax_cal.errorbar(
        px,
        py,
        yerr=[yerr_lo, yerr_hi],
        fmt="-o",
        color="#dc2626",
        ecolor="#fca5a5",
        elinewidth=1.4,
        capsize=3,
        lw=2.0,
        markersize=6,
        label="In-licence wells (n=138, 18.1% vs 27.0% Pg)",
        zorder=4,
    )

    res_all = t2["calibration"]["post_relinquishment_out_of_sample"]
    res_tight = t2["calibration"]["post_relinquishment_tight_le50km2"]
    for obj, col, lbl, mk in [
        (res_all, "#16a34a", "Redrilled post-relinq. all (n=92, 47.8%)", "s"),
        (res_tight, "#0284c7", "Redrilled tight <=50 km2 (n=76, 52.6%)", "D"),
    ]:
        n = obj["n"]
        k = obj["discoveries"]
        mp = obj.get("mean_predicted_pg", obj.get("mean_pg"))
        pred = mp * 100.0 if mp <= 1.0 else mp
        act = (k / n) * 100.0
        lo, hi = wilson_ci(k, n)
        ax_cal.errorbar(
            [pred],
            [act],
            yerr=[[act - lo * 100.0], [hi * 100.0 - act]],
            fmt=mk,
            color=col,
            ecolor=col,
            elinewidth=1.4,
            capsize=3,
            markersize=7.5,
            label=lbl,
            zorder=5,
        )

    ax_cal.set_xlim(0, 75)
    ax_cal.set_ylim(0, 75)
    ax_cal.set_xlabel("Mean Pre-Drill Stated Pg (%)")
    ax_cal.set_ylabel("Realized Hydrocarbon Discovery Rate (%)")
    ax_cal.set_title("B. Two-Regime Calibration Curve (95% Wilson CIs)")
    ax_cal.legend(loc="upper left", fontsize=7.8, frameon=True, facecolor="white")

    fig.tight_layout()
    save_both(fig, "fig1_spatial_join_and_calibration")


def build_fig2(t2: dict) -> None:
    fig, (ax_bf, ax_op) = plt.subplots(1, 2, figsize=(12.2, 5.0), dpi=220)

    factors = ["Reservoir", "Charge", "Retention", "Trap"]
    fear = [21.5, 32.6, 16.4, 29.5]
    actual = [47.6, 32.5, 14.0, 5.9]
    y = np.arange(len(factors))
    h = 0.35

    ax_bf.barh(y - h / 2, fear, h, color="#2563eb", label="Pre-drill #1 Fear (n=891)")
    ax_bf.barh(y + h / 2, actual, h, color="#dc2626", label="Actual Dry-Hole Cause (214 wells)")
    for i, (f, a) in enumerate(zip(fear, actual)):
        ax_bf.text(f + 0.8, i - h / 2, f"{f:.1f}%", va="center", fontsize=8.5, color="#1d4ed8")
        tag = f"{a:.1f}%"
        if i == 0:
            tag = f"{a:.1f}% (2.2x)"
        elif i == 3:
            tag = f"{a:.1f}% (5x over-feared)"
        ax_bf.text(a + 0.8, i + h / 2, tag, va="center", fontsize=8.5, fontweight="bold", color="#b91c1c")

    ax_bf.set_yticks(y)
    ax_bf.set_yticklabels(factors, fontweight="bold")
    ax_bf.invert_yaxis()
    ax_bf.set_xlim(0, 64)
    ax_bf.set_xlabel("Share (%)")
    ax_bf.set_title("A. Pre-Drill Risk Fear vs Actual Dry-Hole Killer")
    ax_bf.legend(loc="lower right", fontsize=8.2, frameon=True, facecolor="white")

    ops = t2["fingerprints"]["by_operator"]
    op_rows = []
    if isinstance(ops, dict):
        for name, val in ops.items():
            res = val.get("basin_adjusted_pg_pp")
            if res is None:
                res = val.get("basin_adjusted_pg_diff_pp")
            n = val.get("n_with_pg", val.get("n_prospects", 0))
            if res is not None and n >= 20:
                op_rows.append((name, float(res), int(n)))
    elif isinstance(ops, list):
        for val in ops:
            res = val.get("basin_adjusted_pg_diff_pp", val.get("basin_adj_pg_residual_pp"))
            n = val.get("n_with_pg", val.get("n_prospects", 0))
            name = val.get("operator")
            if name and res is not None and n >= 20:
                op_rows.append((name, float(res), int(n)))

    op_rows.sort(key=lambda x: x[1], reverse=True)
    if len(op_rows) > 14:
        op_rows = op_rows[:7] + op_rows[-7:]

    names = [f"{r[0]} (n={r[2]})" for r in op_rows]
    vals = [r[1] for r in op_rows]
    cols = ["#dc2626" if v > 0 else "#2563eb" for v in vals]
    y2 = np.arange(len(names))
    ax_op.barh(y2, vals, color=cols, height=0.65)
    ax_op.axvline(0, color="#334155", lw=1.0)
    for i, v in enumerate(vals):
        off = 0.25 if v >= 0 else -0.25
        ha = "left" if v >= 0 else "right"
        ax_op.text(v + off, i, f"{v:+.1f} pp", va="center", ha=ha, fontsize=8.2)
    ax_op.set_yticks(y2)
    ax_op.set_yticklabels(names, fontsize=8.5)
    ax_op.invert_yaxis()
    ax_op.set_xlim(-10.5, 13.0)
    ax_op.set_xlabel("Basin-Adjusted Stated Pg Residual (percentage points)")
    ax_op.set_title("B. Operator Optimism Fingerprint (n >= 20)")

    fig.tight_layout()
    save_both(fig, "fig2_reservoir_blindspot_and_operators")


def build_fig3(kept_json: dict) -> None:
    fig, (ax_sc, ax_hist) = plt.subplots(1, 2, figsize=(12.2, 5.0), dpi=220)

    def pick_vol_mean(assessment: dict) -> float | None:
        vols = assessment.get("volumes") or []
        oe = [v for v in vols if v.get("phase") in ("oil_equivalent", "total_hc") and v.get("basis") == "recoverable"]
        if not oe:
            oe = [v for v in vols if v.get("basis") == "recoverable"]
        if not oe:
            return None
        vals = []
        for v in oe:
            m = safe_canonical_volume_msmo3(v, "mean")
            if m is not None and m > 0:
                vals.append(m)
        if not vals:
            return None
        return float(max(vals))

    init_stages = {"application", "award", "apa_application", "pre_award"}
    final_stages = {"relinquishment", "final", "post_drill", "drill_or_drop", "updated"}

    vol_pairs = []
    risked_ratios = []
    for rec in kept_json.values():
        area = (rec.get("licence") or {}).get("area") or "Other"
        for p in rec.get("prospects") or []:
            ass = p.get("assessments") or []
            if len(ass) < 2:
                continue
            init_a = next((a for a in ass if str(a.get("stage") or "").lower() in init_stages), None)
            fin_a = next((a for a in reversed(ass) if str(a.get("stage") or "").lower() in final_stages), None)
            if init_a is None or fin_a is None or init_a is fin_a:
                continue
            v0 = pick_vol_mean(init_a)
            v1 = pick_vol_mean(fin_a)
            if v0 and v1 and v0 > 0 and v1 > 0 and abs(v1 - v0) / v0 > 1e-4:
                vol_pairs.append((v0, v1, area))
                pg0 = (init_a.get("risk") or {}).get("pg")
                pg1 = (fin_a.get("risk") or {}).get("pg")
                if isinstance(pg0, (int, float)) and isinstance(pg1, (int, float)) and pg0 > 0 and pg1 > 0:
                    risked_ratios.append((pg1 * v1) / (pg0 * v0))

    basin_colors = {"North Sea": "#dc2626", "Norwegian Sea": "#2563eb", "Barents Sea": "#7c3aed"}
    for basin, col in basin_colors.items():
        xs = [x[0] for x in vol_pairs if x[2] == basin]
        ys = [x[1] for x in vol_pairs if x[2] == basin]
        if xs:
            ax_sc.scatter(xs, ys, s=26, color=col, alpha=0.72, edgecolors="white", linewidths=0.3, label=f"{basin} (n={len(xs)})")

    ax_sc.plot([0.1, 400], [0.1, 400], linestyle="--", color="#334155", lw=1.2, label="1 to 1 (no change)")
    ax_sc.plot([0.1, 400], [0.048, 192], linestyle=":", color="#dc2626", lw=1.3, label="Median re-eval cut (0.48x)")
    ax_sc.set_xscale("log")
    ax_sc.set_yscale("log")
    ax_sc.set_xlim(0.15, 350)
    ax_sc.set_ylim(0.05, 350)
    ax_sc.set_xlabel("Award / Application Mean Volume (MSm3 o.e., log)")
    ax_sc.set_ylabel("Relinquishment Mean Volume (MSm3 o.e., log)")
    ax_sc.set_title(f"A. Paired Award vs Relinquishment Volume (n={len(vol_pairs)})")
    ax_sc.legend(loc="upper left", fontsize=8, frameon=True, facecolor="white")

    logs = np.log2(np.array(risked_ratios))
    bins = np.linspace(-5.0, 3.0, 25)
    shrink_logs = logs[logs < 0]
    grow_logs = logs[logs >= 0]
    ax_hist.hist(shrink_logs, bins=bins, color="#dc2626", alpha=0.8, edgecolor="white", label=f"Shrank ({100*len(shrink_logs)/len(logs):.1f}%)")
    ax_hist.hist(grow_logs, bins=bins, color="#16a34a", alpha=0.8, edgecolor="white", label=f"Grew ({100*len(grow_logs)/len(logs):.1f}%)")
    ax_hist.axvline(0.0, color="#334155", lw=1.2, linestyle="--")
    med_log = float(np.median(logs))
    med_pct = (2.0**med_log - 1.0) * 100.0
    ax_hist.axvline(med_log, color="#991b1b", lw=1.8, linestyle="-", label=f"Median {med_pct:.1f}% ({2**med_log:.2f}x)")
    ax_hist.set_xlabel("log2(Final Risked Volume / Award Risked Volume)")
    ax_hist.set_ylabel("Re-evaluated Prospects (count)")
    ax_hist.set_title(f"B. Risked Volume Drift Distribution (n={len(logs)})")
    ax_hist.legend(loc="upper left", fontsize=8.2, frameon=True, facecolor="white")

    fig.tight_layout()
    save_both(fig, "fig3_apa_shrinkage_method")


def build_fig4(t4: dict) -> None:
    fig, (ax_dhi, ax_iou) = plt.subplots(1, 2, figsize=(12.2, 5.0), dpi=220)

    labels = [
        "Amp. Conf. (+)",
        "Bright Spot (+)",
        "AVO Anom. (+)",
        "Unassessed",
        "Flat Spot (all)",
        "Neg / No DHI",
    ]
    rates = [69.0, 61.5, 55.4, 42.6, 28.0, 22.6]
    ns = [42, 26, 65, 585, 25, 62]
    colors = ["#16a34a", "#22c55e", "#2563eb", "#94a3b8", "#dc2626", "#991b1b"]
    y = np.arange(len(labels))
    ax_dhi.barh(y, rates, color=colors, height=0.62)
    for i, (r, n) in enumerate(zip(rates, ns)):
        ax_dhi.text(r + 1.2, i, f"{r:.1f}% (n={n})", va="center", fontsize=8.5, fontweight="bold" if i in (0, 4) else "normal")
    ax_dhi.set_yticks(y)
    ax_dhi.set_yticklabels(labels, fontweight="bold")
    ax_dhi.invert_yaxis()
    ax_dhi.set_xlim(0, 108)
    ax_dhi.set_xlabel("Technical Discovery Rate (%)")
    ax_dhi.set_title("A. DHI Discovery Rate & Barents Gas-Only Inset")

    ins = ax_dhi.inset_axes([0.62, 0.06, 0.35, 0.36])
    ins.bar([0, 1, 2], [6.7, 43.3, 84.6], color=["#2563eb", "#d97706", "#7c3aed"], width=0.58)
    ins.set_xticks([0, 1, 2])
    ins.set_xticklabels(["North", "Norw.", "Barents"])
    for xi, val in enumerate([6.7, 43.3, 84.6]):
        ins.text(xi, val + 3, f"{val:.0f}%", ha="center", fontsize=7.5, fontweight="bold")
    ins.set_ylim(0, 105)
    ins.set_title("Gas-Only Share (+DHI)", fontsize=7.8, fontweight="bold")
    ins.tick_params(labelsize=7.5)
    ins.grid(axis="y", linestyle="--", alpha=0.5)

    poly = t4["angle_b_llm_consistency"]["geojson_polygon_consistency"]
    dig_ious = poly.get("digitised_figure_only", {}).get("ious")
    if not dig_ious:
        pairs = t4["angle_b_llm_consistency"].get("per_pair_summary") or []
        dig_ious = [p["median_iou_digitised"] for p in pairs if p.get("median_iou_digitised") is not None]

    if dig_ious and len(dig_ious) >= 15:
        ax_iou.hist(dig_ious, bins=np.linspace(0.0, 1.0, 21), color="#2563eb", alpha=0.82, edgecolor="white", label=f"Independent VLM map traces (n={len(dig_ious)})")
        med = float(np.median(dig_ious))
        ax_iou.axvline(med, color="#dc2626", lw=2.0, linestyle="--", label=f"Median IoU = {med:.3f} (shift 116.8 m)")
        ax_iou.set_xlabel("Polygon Intersection-over-Union (IoU)")
        ax_iou.set_ylabel("Matched Prospect Polygons")
        ax_iou.set_title("B. 18-PDF Natural Experiment (VLM Map Digitization IoU)")
        ax_iou.legend(loc="upper left", fontsize=8.2, frameon=True, facecolor="white")
    else:
        metrics = ["Reservoir\nPeriod", "Exact Pg\nMatch", "Exact Vol.\nMatch", "Name\nJaccard", "VLM Map\nMed. IoU", "Exact Count\nMatch"]
        vals = [100.0, 95.5, 92.2, 86.2, 86.1, 55.6]
        cols = ["#16a34a", "#16a34a", "#2563eb", "#2563eb", "#7c3aed", "#d97706"]
        bars = ax_iou.bar(metrics, vals, color=cols, width=0.58)
        for b, v in zip(bars, vals):
            ax_iou.text(b.get_x() + b.get_width() / 2, v + 1.8, f"{v:.1f}%", ha="center", fontsize=8.5, fontweight="bold")
        ax_iou.set_ylim(0, 112)
        ax_iou.set_ylabel("Inter-Run Agreement (%)")
        ax_iou.set_title("B. 18-PDF Natural Experiment (Claude vs Claude)")

    fig.tight_layout()
    save_both(fig, "fig4_dhi_paradox_and_llm_iou")


def main() -> None:
    raw_json, raw_geo = load_raw_records()
    kept_json, kept_geo, _ = deduplicate_records(raw_json, raw_geo)
    t1 = json.loads((ROOT / "analyses" / "track1_findings.json").read_text(encoding="utf-8"))
    t2 = json.loads((ROOT / "analyses" / "track2_findings.json").read_text(encoding="utf-8"))
    t4 = json.loads((ROOT / "analyses" / "track4_findings.json").read_text(encoding="utf-8"))

    build_fig1(t1, t2, kept_geo)
    build_fig2(t2)
    build_fig3(kept_json)
    build_fig4(t4)
    print("Generated 4 figures in", FIG_DIR)


if __name__ == "__main__":
    main()
