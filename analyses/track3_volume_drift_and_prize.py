import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, r"C:\Users\philip\Documents\ncs-relinquished-atlas\src")
from loader import deduplicate_records, load_raw_records, safe_canonical_volume_msmo3

OUTPUT_DIR = Path(r"C:\Users\philip\Documents\ncs-relinquished-atlas\analyses")
OUTPUT_JSON = OUTPUT_DIR / "track3_findings.json"
MSMO3_TO_MMBOE = 6.28981077

INITIAL_STAGES = {"application", "award"}
FINAL_STAGES = {"final", "post_well", "drill_or_drop"}
STRICT_FINAL_STAGES = {"final"}
POST_AWARD_STAGES = {"final", "drill_or_drop", "intermediate"}

GEO_RISK_TAGS = {
    "high_risk",
    "reservoir_risk",
    "charge_risk",
    "trap_risk",
    "migration_risk",
    "seal_risk",
    "fault_seal_risk",
    "no_prospectivity",
    "well_result_nearby",
    "poor_seismic_imaging",
    "compartmentalisation",
}

COMMERCIAL_TAGS = {
    "volume_too_small",
    "commercial",
    "negative_emv",
    "below_mef",
}

NON_TECH_TAGS = {
    "infrastructure_distance",
    "dependency_on_infrastructure",
    "portfolio_strategy",
    "prospect_moved_outside_licence",
    "protection_acreage_not_needed",
}

DRILLED_STATUSES = {"drilled_dry", "drilled_discovery", "discovery_marginal"}
INVALID_STATUSES = {"invalidated", "no_longer_closure", "outside_licence", "not_awarded", "retained"}


def safe_volume_clean(vol: dict[str, Any], field: str = "mean") -> tuple[float | None, bool]:
    val = safe_canonical_volume_msmo3(vol, field)
    if val is None:
        return None, False
    dist = vol.get("distribution") or {}
    us = (dist.get("_derived") or {}).get("unit_scale") or {}
    raw_unit = str(dist.get("unit") or "").strip().lower()
    factor = us.get("factor", 1)
    if (
        vol.get("phase") in ("oil", "condensate")
        and "1e9" in raw_unit
        and isinstance(factor, (int, float))
        and factor >= 100
    ):
        return float(val) / 1000.0, True
    return float(val), False


def normalize_operator(op: str | None) -> str:
    if not op:
        return "Unknown"
    s = op.strip()
    sl = s.lower()
    if any(k in sl for k in ("equinor", "statoil")):
        return "Equinor (incl. Statoil)"
    if any(k in sl for k in ("aker bp", "det norske", "bp norge")):
        return "Aker BP (incl. Det norske)"
    if "lundin" in sl:
        return "Lundin"
    if any(k in sl for k in ("vår energi", "var energi", "eni norge", "point resources")):
        return "Vår Energi (incl. Eni)"
    if any(k in sl for k in ("wintershall", "dea norge")):
        return "Wintershall Dea"
    if "conocophillips" in sl:
        return "ConocoPhillips"
    if "shell" in sl:
        return "Shell"
    if "omv" in sl:
        return "OMV"
    if any(k in sl for k in ("dno ", "faroe")):
        return "DNO (incl. Faroe)"
    if any(k in sl for k in ("spirit energy", "centrica", "bayerngas")):
        return "Spirit / Centrica"
    if "okea" in sl:
        return "OKEA"
    if any(k in sl for k in ("total ", "totalenergies", "maersk oil")):
        return "TotalEnergies (incl. Maersk)"
    if any(k in sl for k in ("neptune", "gdf suez", "engie", "vng ")):
        return "Neptune / VNG / ENGIE"
    if "repsol" in sl or "talisman" in sl:
        return "Repsol (incl. Talisman)"
    if "wellesley" in sl:
        return "Wellesley"
    if "tullow" in sl:
        return "Tullow"
    if "suncor" in sl:
        return "Suncor"
    if "edison" in sl:
        return "Edison"
    if "mol " in sl:
        return "MOL"
    if "pgnig" in sl or "orlen" in sl:
        return "PGNiG / Orlen"
    if "capricorn" in sl or "cairn" in sl:
        return "Capricorn / Cairn"
    if "harbour" in sl or "premier oil" in sl or "chrysaor" in sl:
        return "Harbour (incl. Premier)"
    if "sval" in sl:
        return "Sval Energi"
    if "nexen" in sl or "cnooc" in sl:
        return "Nexen / CNOOC"
    if "e.on" in sl:
        return "E.ON"
    if "bg norge" in sl:
        return "BG Norge"
    if "chevron" in sl:
        return "Chevron"
    if "exxon" in sl or "esso" in sl:
        return "ExxonMobil"
    if "hess" in sl:
        return "Hess"
    if "dong" in sl:
        return "DONG"
    if "idemitsu" in sl:
        return "Idemitsu"
    if "lotos" in sl:
        return "LOTOS"
    if "noreco" in sl or "norwegian energy" in sl:
        return "Noreco"
    if "pandion" in sl:
        return "Pandion"
    return s


def extract_year(date_str: str | None) -> int | None:
    if not date_str:
        return None
    m = re.search(r"(19\d{2}|20\d{2})", str(date_str))
    return int(m.group(1)) if m else None


def licence_award_year(rec: dict[str, Any]) -> int | None:
    lic = rec.get("licence") or {}
    d = ((lic.get("_derived") or {}).get("dates") or {}).get("award_date") or {}
    y = extract_year(d.get("start")) or extract_year(lic.get("award_date"))
    if y:
        return y
    ar = ((lic.get("_derived") or {}).get("identifiers") or {}).get("award_round") or {}
    if isinstance(ar.get("round_year"), int):
        return ar["round_year"] + 1
    return None


def licence_relinq_year(rec: dict[str, Any]) -> int | None:
    lic = rec.get("licence") or {}
    d = ((lic.get("_derived") or {}).get("dates") or {}).get("relinquishment_date") or {}
    return extract_year(d.get("start")) or extract_year(lic.get("relinquishment_date"))


def decade_bucket(year: int | None) -> str:
    if year is None:
        return "Unknown"
    if year < 2010:
        return "2000s (<=2009)"
    if year < 2020:
        return "2010s (2010-2019)"
    return "2020s (>=2020)"


def extract_assessment_volume(
    assessment: dict[str, Any], field: str = "mean"
) -> tuple[float | None, str | None, list[dict[str, Any]]]:
    vols = assessment.get("volumes") or []
    anomalies: list[dict[str, Any]] = []
    rec_vols = [
        v for v in vols
        if v.get("basis") == "recoverable" and v.get("risking") == "unrisked"
    ]
    if not rec_vols:
        return None, None, anomalies

    by_case: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for v in rec_vols:
        val, fixed = safe_volume_clean(v, field)
        if val is None or val < 0:
            continue
        if fixed:
            anomalies.append({
                "phase": v.get("phase"),
                "raw_unit": (v.get("distribution") or {}).get("unit"),
                "fixed_val": val,
                "original_text": (v.get("distribution") or {}).get("original_text"),
            })
        case_key = str(v.get("case_label") or "").strip().lower()
        target_key = str(v.get("target_id") or "").strip().lower()
        phase = str(v.get("phase") or "unknown").strip().lower()
        existing = by_case[case_key][target_key].get(phase)
        if existing is None or val > existing:
            by_case[case_key][target_key][phase] = val

    if not by_case:
        return None, None, anomalies

    case_totals: list[tuple[str, float, str]] = []
    for case_key, targets in by_case.items():
        total_case = 0.0
        phases_used: set[str] = set()
        for target_key, phase_map in targets.items():
            if "oil_equivalent" in phase_map:
                total_case += phase_map["oil_equivalent"]
                phases_used.add("oil_equivalent")
            elif "total_hc" in phase_map:
                total_case += phase_map["total_hc"]
                phases_used.add("total_hc")
            else:
                for ph in ("oil", "gas", "associated_gas", "condensate", "free_gas", "solution_gas"):
                    if ph in phase_map:
                        total_case += phase_map[ph]
                        phases_used.add(ph)
        if "oil" in phases_used and ("gas" in phases_used or "associated_gas" in phases_used):
            dom_phase = "oil_and_gas"
        elif "oil" in phases_used:
            dom_phase = "oil"
        elif "gas" in phases_used or "condensate" in phases_used:
            dom_phase = "gas"
        elif "oil_equivalent" in phases_used or "total_hc" in phases_used:
            dom_phase = assessment.get("phase_case") or "oil_equivalent"
        else:
            dom_phase = "unknown"
        case_totals.append((case_key, total_case, dom_phase))

    if len(case_totals) == 1:
        return case_totals[0][1], case_totals[0][2], anomalies

    for pref in ("base", "total", "aggregated", "combined", "oil_and_gas", "oil&gas", "main", ""):
        for ck, tv, dp in case_totals:
            if ck == pref or (pref and pref in ck):
                return tv, dp, anomalies

    best = max(case_totals, key=lambda x: x[1])
    return best[1], best[2], anomalies


def extract_assessment_pg(assessment: dict[str, Any]) -> float | None:
    rk = assessment.get("risk") or {}
    pg = rk.get("pg")
    if isinstance(pg, (int, float)) and not isinstance(pg, bool):
        if 0.0 <= pg <= 1.0:
            return float(pg)
        if 1.0 < pg <= 100.0:
            return float(pg) / 100.0
    return None


def pick_stage_assessment(
    assessments: list[dict[str, Any]],
    stages: set[str],
    stage_priority: list[str],
    require_field: str,
    preferred_phase_case: str | None = None,
) -> tuple[dict[str, Any] | None, float | None, str | None, list[dict[str, Any]]]:
    candidates = [a for a in assessments if a.get("stage") in stages]
    if not candidates:
        return None, None, None, []

    scored: list[tuple[int, int, int, float, dict[str, Any], str | None, list[dict[str, Any]]]] = []
    for idx, a in enumerate(candidates):
        st = a.get("stage") or ""
        prio = stage_priority.index(st) if st in stage_priority else 99
        phase_match = 0 if (preferred_phase_case and a.get("phase_case") == preferred_phase_case) else 1
        if require_field == "pg":
            val = extract_assessment_pg(a)
            dom_phase = a.get("phase_case")
            anoms: list[dict[str, Any]] = []
        else:
            val, dom_phase, anoms = extract_assessment_volume(a, require_field)
        if val is not None:
            scored.append((prio, phase_match, -idx, val, a, dom_phase, anoms))

    if not scored:
        return None, None, None, []

    scored.sort(key=lambda x: (x[0], x[1], x[2]))
    best = scored[0]
    return best[4], best[3], best[5], best[6]


def summarize_ratios(
    pairs: list[dict[str, Any]],
    init_key: str,
    final_key: str,
    tol: float = 0.01,
    changed_only: bool = False,
) -> dict[str, Any]:
    valid = [
        p for p in pairs
        if p.get(init_key) is not None and p.get(final_key) is not None and p[init_key] > 0
    ]
    if changed_only:
        valid = [p for p in valid if abs(p[final_key] / p[init_key] - 1.0) > tol]
    n = len(valid)
    if n == 0:
        return {"n": 0}

    ratios = [p[final_key] / p[init_key] for p in valid]
    pos_ratios = [r for r in ratios if r > 0]
    shrank = sum(1 for r in ratios if r < 1.0 - tol)
    grew = sum(1 for r in ratios if r > 1.0 + tol)
    unchanged = n - shrank - grew

    ratios_sorted = sorted(ratios)
    p25 = ratios_sorted[int(0.25 * (n - 1))]
    p75 = ratios_sorted[int(0.75 * (n - 1))]
    geo_mean = math.exp(sum(math.log(r) for r in pos_ratios) / len(pos_ratios)) if pos_ratios else None
    sum_init = sum(p[init_key] for p in valid)
    sum_final = sum(p[final_key] for p in valid)

    return {
        "n": n,
        "pct_shrank": round(100.0 * shrank / n, 1),
        "pct_unchanged": round(100.0 * unchanged / n, 1),
        "pct_grew": round(100.0 * grew / n, 1),
        "n_shrank": shrank,
        "n_unchanged": unchanged,
        "n_grew": grew,
        "median_ratio": round(statistics.median(ratios), 4),
        "mean_ratio": round(statistics.mean(ratios), 4),
        "geom_mean_ratio": round(geo_mean, 4) if geo_mean is not None else None,
        "p25_ratio": round(p25, 4),
        "p75_ratio": round(p75, 4),
        "portfolio_ratio": round(sum_final / sum_init, 4) if sum_init > 0 else None,
        "sum_initial": round(sum_init, 2),
        "sum_final": round(sum_final, 2),
        "median_pct_change": round((statistics.median(ratios) - 1.0) * 100.0, 1),
        "portfolio_pct_change": round((sum_final / sum_init - 1.0) * 100.0, 1) if sum_init > 0 else None,
    }


def summarize_pg_drift(
    pairs: list[dict[str, Any]],
    tol_pp: float = 0.005,
    changed_only: bool = False,
) -> dict[str, Any]:
    valid = [
        p for p in pairs
        if p.get("init_pg") is not None and p.get("final_pg") is not None and p["init_pg"] > 0
    ]
    if changed_only:
        valid = [p for p in valid if abs(p["final_pg"] - p["init_pg"]) > tol_pp]
    n = len(valid)
    if n == 0:
        return {"n": 0}

    diffs = [p["final_pg"] - p["init_pg"] for p in valid]
    ratios = [p["final_pg"] / p["init_pg"] for p in valid]
    pos_ratios = [r for r in ratios if r > 0]
    dropped = sum(1 for d in diffs if d < -tol_pp)
    increased = sum(1 for d in diffs if d > tol_pp)
    unchanged = n - dropped - increased

    diffs_sorted = sorted(diffs)
    p25_diff = diffs_sorted[int(0.25 * (n - 1))]
    p75_diff = diffs_sorted[int(0.75 * (n - 1))]
    geo_mean = math.exp(sum(math.log(r) for r in pos_ratios) / len(pos_ratios)) if pos_ratios else None

    return {
        "n": n,
        "pct_dropped": round(100.0 * dropped / n, 1),
        "pct_unchanged": round(100.0 * unchanged / n, 1),
        "pct_increased": round(100.0 * increased / n, 1),
        "n_dropped": dropped,
        "n_unchanged": unchanged,
        "n_increased": increased,
        "mean_initial_pg_pct": round(100.0 * statistics.mean(p["init_pg"] for p in valid), 2),
        "mean_final_pg_pct": round(100.0 * statistics.mean(p["final_pg"] for p in valid), 2),
        "median_initial_pg_pct": round(100.0 * statistics.median(p["init_pg"] for p in valid), 2),
        "median_final_pg_pct": round(100.0 * statistics.median(p["final_pg"] for p in valid), 2),
        "median_diff_pp": round(100.0 * statistics.median(diffs), 2),
        "mean_diff_pp": round(100.0 * statistics.mean(diffs), 2),
        "p25_diff_pp": round(100.0 * p25_diff, 2),
        "p75_diff_pp": round(100.0 * p75_diff, 2),
        "median_ratio": round(statistics.median(ratios), 4),
        "mean_ratio": round(statistics.mean(ratios), 4),
        "geom_mean_ratio": round(geo_mean, 4) if geo_mean is not None else None,
    }


def detect_non_tech_subtypes(text: str, reasons: set[str], partner_views: Any) -> set[str]:
    tl = text.lower()
    subtypes: set[str] = set()
    if (
        partner_views
        or re.search(
            r"partner\w*\s+(disagree|diverg|differ|unable|withdraw|exit|not\s+wish|could\s+not\s+attract|farm[\-\s]?out|majority|sole\s+risk|voting)",
            tl,
        )
        or re.search(
            r"different\s+views|unable\s+to\s+reach\s+(a\s+)?(consensus|agreement|positive\s+drill)|no\s+unanimous|lack\s+of\s+partner|farm[\-\s]?out\s+(failed|unsuccessful|process)",
            tl,
        )
    ):
        subtypes.add("partner_disagreement_or_farmout")
    if (
        "infrastructure_distance" in reasons
        or "dependency_on_infrastructure" in reasons
        or re.search(
            r"tie[\-\s]?back|infrastructure|host\s+facility|ullage|processing\s+capacity|distance\s+to\s+(host|platform|infrastructure)|stand[\-\s]?alone",
            tl,
        )
    ):
        subtypes.add("infrastructure_or_capacity")
    if re.search(
        r"gas\s+(export|market|evacuation|offtake|pipeline|infrastructure|monetis|monetiz)|lng|snøhvit|snohvit|barents\s+gas|no\s+gas\s+export|gas\s+price",
        tl,
    ):
        subtypes.add("gas_market_or_evacuation")
    if (
        "portfolio_strategy" in reasons
        or re.search(
            r"portfolio|prioriti[sz]|capital\s+allocation|corporate\s+strateg|company\s+strateg|ranking|competing\s+opportunit",
            tl,
        )
    ):
        subtypes.add("portfolio_prioritization")
    if re.search(
        r"\brig\b|drilling\s+(cost|rig|capacity|slot|market)|well\s+cost\s+too\s+high|expensive\s+well|high\s+drilling\s+cost",
        tl,
    ):
        subtypes.add("rig_or_well_cost")
    if "prospect_moved_outside_licence" in reasons or re.search(
        r"outside\s+(the\s+)?licence|straddl|not\s+awarded|open\s+acreage", tl
    ):
        subtypes.add("outside_licence_or_boundary")
    if re.search(
        r"maximum\s+10[\-\s]year|licence\s+expir|initial\s+period\s+expir|deadline|drill[\-\s]or[\-\s]drop\s+deadline|could\s+not\s+mature\s+in\s+time",
        tl,
    ):
        subtypes.add("licence_expiry_or_time")
    return subtypes


def prospect_is_drilled(p: dict[str, Any]) -> bool:
    if p.get("status_at_report") in DRILLED_STATUSES:
        return True
    if p.get("classification") == "discovery":
        return True
    dr = p.get("drilling")
    if isinstance(dr, dict):
        if dr.get("drilled") is True or dr.get("well_name") or dr.get("wellbore"):
            return True
    elif isinstance(dr, list) and len(dr) > 0:
        return True
    return False


def deduplicate_straddling_prize(cands: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: dict[tuple[str, float, float], dict[str, Any]] = {}
    dups = 0
    for c in cands:
        key = (
            re.sub(r"[^a-z0-9]", "", c["name"].lower()),
            round(c["unrisked_mean_msmo3"], 1),
            round(c["pg"], 2),
        )
        if key in seen:
            dups += 1
            existing = seen[key]
            if c["licence_id"] not in existing["licence_id"]:
                existing["licence_id"] = f"{existing['licence_id']} / {c['licence_id']}"
        else:
            seen[key] = dict(c)
    return list(seen.values()), dups


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_j, raw_g = load_raw_records()
    kept_j, kept_g, dropped_stems = deduplicate_records(raw_j, raw_g)
    records = list(kept_j.values())

    anomalies_caught: list[dict[str, Any]] = []
    paired_records: list[dict[str, Any]] = []

    prospect_drop_rows: list[dict[str, Any]] = []
    licence_non_tech_counter: Counter[str] = Counter()
    licence_non_tech_by_basin: dict[str, Counter[str]] = defaultdict(Counter)
    licence_count_by_basin: Counter[str] = Counter()

    undrilled_prize_post_award: list[dict[str, Any]] = []
    undrilled_prize_all_stages: list[dict[str, Any]] = []
    excluded_pg_100: list[dict[str, Any]] = []

    all_prospects_count = 0
    parent_ids_present: set[tuple[str, str]] = set()
    for rec in records:
        lic_id = (rec.get("licence") or {}).get("licence_id") or rec.get("record_key")
        for p in rec.get("prospects") or []:
            pid = p.get("prospect_id")
            if pid:
                parent_ids_present.add((lic_id, pid))

    for rec in records:
        lic = rec.get("licence") or {}
        lic_id = lic.get("licence_id") or rec.get("record_key")
        basin = lic.get("area") or "Unknown"
        licence_count_by_basin[basin] += 1
        op_raw = lic.get("operator") or "Unknown"
        op_norm = normalize_operator(op_raw)
        award_yr = licence_award_year(rec)
        relinq_yr = licence_relinq_year(rec)
        award_dec = decade_bucket(award_yr)
        relinq_dec = decade_bucket(relinq_yr)
        lic_reason = str(lic.get("relinquishment_reason") or "")
        work_perf = json.dumps(lic.get("work_performed") or "", ensure_ascii=False).lower()
        has_new_3d = bool(re.search(r"3d|reprocess|broadband|psdm|pstm|cgg|pgs|tgs|seismic\s+acqui", work_perf))

        lic_all_nt: set[str] = detect_non_tech_subtypes(lic_reason, set(), None)
        if lic.get("farm_out") or lic.get("operator_sole_risk_actions"):
            lic_all_nt.add("partner_disagreement_or_farmout")

        for p in rec.get("prospects") or []:
            all_prospects_count += 1
            pname = p.get("name") or "Unnamed"
            pid = p.get("prospect_id") or pname
            status = p.get("status_at_report") or "unknown"
            cls = p.get("classification") or "unknown"
            parent_pid = p.get("parent_prospect_id")
            is_child_segment = bool(parent_pid and (lic_id, parent_pid) in parent_ids_present)
            drilled = prospect_is_drilled(p)
            assessments = p.get("assessments") or []

            init_a_mean, init_mean, _, a1 = pick_stage_assessment(
                assessments, INITIAL_STAGES, ["application", "award"], "mean"
            )
            pref_pc = init_a_mean.get("phase_case") if init_a_mean else None
            fin_a_mean, fin_mean, _, a2 = pick_stage_assessment(
                assessments, FINAL_STAGES, ["final", "post_well", "drill_or_drop"], "mean", pref_pc
            )
            _, strict_fin_mean, _, _ = pick_stage_assessment(
                assessments, STRICT_FINAL_STAGES, ["final"], "mean", pref_pc
            )

            init_a_p50, init_p50, _, _ = pick_stage_assessment(
                assessments, INITIAL_STAGES, ["application", "award"], "p50"
            )
            fin_a_p50, fin_p50, _, _ = pick_stage_assessment(
                assessments,
                FINAL_STAGES,
                ["final", "post_well", "drill_or_drop"],
                "p50",
                init_a_p50.get("phase_case") if init_a_p50 else None,
            )

            init_a_pg, init_pg, _, _ = pick_stage_assessment(
                assessments, INITIAL_STAGES, ["application", "award"], "pg"
            )
            fin_a_pg, fin_pg, _, _ = pick_stage_assessment(
                assessments,
                FINAL_STAGES,
                ["final", "post_well", "drill_or_drop"],
                "pg",
                init_a_pg.get("phase_case") if init_a_pg else None,
            )

            for an in a1 + a2:
                an["licence_id"] = lic_id
                an["prospect"] = pname
                anomalies_caught.append(an)

            if (
                (init_mean is not None and fin_mean is not None)
                or (init_p50 is not None and fin_p50 is not None)
                or (init_pg is not None and fin_pg is not None)
            ):
                init_risked = (init_mean * init_pg) if (init_mean is not None and init_pg is not None) else None
                fin_risked = (fin_mean * fin_pg) if (fin_mean is not None and fin_pg is not None) else None
                paired_records.append({
                    "licence_id": lic_id,
                    "prospect_id": pid,
                    "name": pname,
                    "basin": basin,
                    "operator": op_norm,
                    "operator_raw": op_raw,
                    "award_year": award_yr,
                    "relinq_year": relinq_yr,
                    "award_decade": award_dec,
                    "relinq_decade": relinq_dec,
                    "has_new_3d": has_new_3d,
                    "status": status,
                    "classification": cls,
                    "drilled": drilled,
                    "is_child_segment": is_child_segment,
                    "init_stage": (init_a_mean or init_a_pg or init_a_p50 or {}).get("stage"),
                    "final_stage": (fin_a_mean or fin_a_pg or fin_a_p50 or {}).get("stage"),
                    "init_mean": init_mean,
                    "final_mean": fin_mean,
                    "strict_final_mean": strict_fin_mean,
                    "init_p50": init_p50,
                    "final_p50": fin_p50,
                    "init_pg": init_pg,
                    "final_pg": fin_pg,
                    "init_risked": init_risked,
                    "final_risked": fin_risked,
                })

            concl = p.get("conclusion") or {}
            reasons = set(concl.get("reasons_not_drilled") or [])
            concl_text = str(concl.get("text") or "")
            rem_pot = str(concl.get("remaining_potential") or "")
            econ_notes = " ".join(
                str((a.get("economics") or {}).get("notes") or "")
                for a in assessments
            )
            pv = p.get("partner_views")
            pv_text = json.dumps(pv, ensure_ascii=False) if pv else ""
            constraints_text = json.dumps(p.get("constraints") or "", ensure_ascii=False)
            combined_text = " ".join([concl_text, rem_pot, econ_notes, pv_text, constraints_text])

            has_geo = bool(reasons & GEO_RISK_TAGS) or status in ("invalidated", "no_longer_closure")
            has_comm = bool(reasons & COMMERCIAL_TAGS) or bool(
                re.search(
                    r"sub[\-\s]?commercial|uneconomic|non[\-\s]?economic|too\s+small|below\s+mef|negative\s+(emv|npv|econom)",
                    combined_text.lower(),
                )
            )
            nt_subtypes = detect_non_tech_subtypes(combined_text, reasons, pv)
            lic_all_nt.update(nt_subtypes)
            has_nontech = bool(reasons & NON_TECH_TAGS) or bool(nt_subtypes)

            if drilled:
                primary_cat = "drilled"
            elif status == "outside_licence":
                primary_cat = "outside_licence_or_non_tech"
            elif has_geo and has_comm:
                primary_cat = "both_geo_and_commercial"
            elif has_geo:
                primary_cat = "geo_risk_only"
            elif has_comm:
                primary_cat = "commercial_only"
            elif has_nontech:
                primary_cat = "outside_licence_or_non_tech"
            else:
                primary_cat = "other_or_unspecified"

            prospect_drop_rows.append({
                "licence_id": lic_id,
                "basin": basin,
                "drilled": drilled,
                "status": status,
                "has_geo": has_geo,
                "has_comm": has_comm,
                "has_nontech": has_nontech,
                "nt_subtypes": nt_subtypes,
                "reasons": reasons,
                "primary_cat": primary_cat,
            })

            def build_prize_entry(
                a_vol: dict[str, Any] | None,
                vol_val: float | None,
                phase_val: str | None,
                a_pg: dict[str, Any] | None,
                pg_val: float | None,
            ) -> dict[str, Any] | None:
                if vol_val is None or vol_val <= 0 or pg_val is None or pg_val < 0.20:
                    return None
                if pg_val >= 0.99:
                    excluded_pg_100.append({
                        "licence_id": lic_id,
                        "name": pname,
                        "unrisked_mean_msmo3": round(vol_val, 3),
                        "pg": pg_val,
                        "stage": (a_vol or {}).get("stage"),
                    })
                    return None
                dev_opts = []
                for a in assessments:
                    e = a.get("economics") or {}
                    for dopt in e.get("development_options") or []:
                        if isinstance(dopt, dict):
                            host = dopt.get("host")
                            dist_km = dopt.get("distance_km")
                            if host:
                                dev_opts.append(f"{host} ({dist_km} km)" if dist_km else str(host))
                return {
                    "licence_id": lic_id,
                    "prospect_id": pid,
                    "name": pname,
                    "basin": basin,
                    "operator": op_norm,
                    "operator_raw": op_raw,
                    "award_year": award_yr,
                    "relinq_year": relinq_yr,
                    "classification": cls,
                    "status": status,
                    "vol_stage": (a_vol or {}).get("stage"),
                    "pg_stage": (a_pg or {}).get("stage"),
                    "phase": phase_val or "unknown",
                    "unrisked_mean_msmo3": round(vol_val, 3),
                    "unrisked_mean_mmboe": round(vol_val * MSMO3_TO_MMBOE, 1),
                    "pg": round(pg_val, 4),
                    "risked_mean_msmo3": round(vol_val * pg_val, 3),
                    "risked_mean_mmboe": round(vol_val * pg_val * MSMO3_TO_MMBOE, 1),
                    "has_geo": has_geo,
                    "has_comm": has_comm,
                    "has_nontech": has_nontech,
                    "dropped_comm_or_nt": has_comm or has_nontech,
                    "primary_cat": primary_cat,
                    "reasons_not_drilled": sorted(reasons),
                    "non_tech_subtypes": sorted(nt_subtypes),
                    "dev_hosts": sorted(set(dev_opts))[:3],
                    "conclusion_text": concl_text[:350],
                    "licence_reason": lic_reason[:300],
                }

            if not drilled and status not in INVALID_STATUSES and not is_child_segment:
                pa_a_vol, pa_vol, pa_phase, _ = pick_stage_assessment(
                    assessments, POST_AWARD_STAGES, ["final", "drill_or_drop", "intermediate"], "mean"
                )
                pa_a_pg, pa_pg, _, _ = pick_stage_assessment(
                    assessments,
                    POST_AWARD_STAGES,
                    ["final", "drill_or_drop", "intermediate"],
                    "pg",
                    pa_a_vol.get("phase_case") if pa_a_vol else None,
                )
                entry_pa = build_prize_entry(pa_a_vol, pa_vol, pa_phase, pa_a_pg, pa_pg)
                if entry_pa is not None:
                    undrilled_prize_post_award.append(entry_pa)

                all_a_vol, all_vol, all_phase, _ = pick_stage_assessment(
                    assessments,
                    {"final", "drill_or_drop", "intermediate", "application", "award", "unknown"},
                    ["final", "drill_or_drop", "intermediate", "application", "award", "unknown"],
                    "mean",
                )
                all_a_pg, all_pg, _, _ = pick_stage_assessment(
                    assessments,
                    {"final", "drill_or_drop", "intermediate", "application", "award", "unknown"},
                    ["final", "drill_or_drop", "intermediate", "application", "award", "unknown"],
                    "pg",
                    all_a_vol.get("phase_case") if all_a_vol else None,
                )
                entry_all = build_prize_entry(all_a_vol, all_vol, all_phase, all_a_pg, all_pg)
                if entry_all is not None:
                    undrilled_prize_all_stages.append(entry_all)

        for st in lic_all_nt:
            licence_non_tech_counter[st] += 1
            licence_non_tech_by_basin[basin][st] += 1

    undrilled_pairs = [r for r in paired_records if not r["drilled"]]
    drilled_pairs = [r for r in paired_records if r["drilled"]]
    non_child_pairs = [r for r in paired_records if not r["is_child_segment"]]

    drift_overall = {
        "all_paired": {
            "mean_volume": summarize_ratios(paired_records, "init_mean", "final_mean"),
            "mean_volume_reevaluated_only": summarize_ratios(
                paired_records, "init_mean", "final_mean", changed_only=True
            ),
            "strict_final_mean_volume": summarize_ratios(paired_records, "init_mean", "strict_final_mean"),
            "p50_volume": summarize_ratios(paired_records, "init_p50", "final_p50"),
            "pg": summarize_pg_drift(paired_records),
            "pg_reevaluated_only": summarize_pg_drift(paired_records, changed_only=True),
            "risked_mean_volume": summarize_ratios(paired_records, "init_risked", "final_risked"),
            "risked_mean_volume_reevaluated_only": summarize_ratios(
                paired_records, "init_risked", "final_risked", changed_only=True
            ),
        },
        "undrilled_only": {
            "mean_volume": summarize_ratios(undrilled_pairs, "init_mean", "final_mean"),
            "mean_volume_reevaluated_only": summarize_ratios(
                undrilled_pairs, "init_mean", "final_mean", changed_only=True
            ),
            "p50_volume": summarize_ratios(undrilled_pairs, "init_p50", "final_p50"),
            "pg": summarize_pg_drift(undrilled_pairs),
            "pg_reevaluated_only": summarize_pg_drift(undrilled_pairs, changed_only=True),
            "risked_mean_volume": summarize_ratios(undrilled_pairs, "init_risked", "final_risked"),
            "risked_mean_volume_reevaluated_only": summarize_ratios(
                undrilled_pairs, "init_risked", "final_risked", changed_only=True
            ),
        },
        "drilled_only": {
            "mean_volume": summarize_ratios(drilled_pairs, "init_mean", "final_mean"),
            "pg": summarize_pg_drift(drilled_pairs),
            "risked_mean_volume": summarize_ratios(drilled_pairs, "init_risked", "final_risked"),
        },
        "excluding_child_segments": {
            "mean_volume": summarize_ratios(non_child_pairs, "init_mean", "final_mean"),
            "pg": summarize_pg_drift(non_child_pairs),
            "risked_mean_volume": summarize_ratios(non_child_pairs, "init_risked", "final_risked"),
        },
    }

    by_basin: dict[str, Any] = {}
    for b in ("North Sea", "Norwegian Sea", "Barents Sea"):
        sub = [r for r in paired_records if r["basin"] == b]
        sub_u = [r for r in undrilled_pairs if r["basin"] == b]
        by_basin[b] = {
            "mean_volume": summarize_ratios(sub, "init_mean", "final_mean"),
            "mean_volume_reevaluated_only": summarize_ratios(sub, "init_mean", "final_mean", changed_only=True),
            "pg": summarize_pg_drift(sub),
            "pg_reevaluated_only": summarize_pg_drift(sub, changed_only=True),
            "risked_mean_volume": summarize_ratios(sub, "init_risked", "final_risked"),
            "undrilled_mean_volume": summarize_ratios(sub_u, "init_mean", "final_mean"),
            "undrilled_pg": summarize_pg_drift(sub_u),
        }

    op_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in paired_records:
        op_groups[r["operator"]].append(r)
    by_operator: dict[str, Any] = {}
    for op, rows in sorted(op_groups.items(), key=lambda kv: -len(kv[1])):
        vol_s = summarize_ratios(rows, "init_mean", "final_mean")
        vol_rc = summarize_ratios(rows, "init_mean", "final_mean", changed_only=True)
        pg_s = summarize_pg_drift(rows)
        if vol_s.get("n", 0) >= 8 or pg_s.get("n", 0) >= 10:
            by_operator[op] = {
                "mean_volume": vol_s,
                "mean_volume_reevaluated_only": vol_rc,
                "pg": pg_s,
                "risked_mean_volume": summarize_ratios(rows, "init_risked", "final_risked"),
            }

    by_award_decade: dict[str, Any] = {}
    for dec in ("2000s (<=2009)", "2010s (2010-2019)", "2020s (>=2020)"):
        sub = [r for r in paired_records if r["award_decade"] == dec]
        by_award_decade[dec] = {
            "mean_volume": summarize_ratios(sub, "init_mean", "final_mean"),
            "mean_volume_reevaluated_only": summarize_ratios(sub, "init_mean", "final_mean", changed_only=True),
            "pg": summarize_pg_drift(sub),
            "risked_mean_volume": summarize_ratios(sub, "init_risked", "final_risked"),
        }

    by_relinq_decade: dict[str, Any] = {}
    for dec in ("2000s (<=2009)", "2010s (2010-2019)", "2020s (>=2020)"):
        sub = [r for r in paired_records if r["relinq_decade"] == dec]
        by_relinq_decade[dec] = {
            "mean_volume": summarize_ratios(sub, "init_mean", "final_mean"),
            "mean_volume_reevaluated_only": summarize_ratios(sub, "init_mean", "final_mean", changed_only=True),
            "pg": summarize_pg_drift(sub),
            "risked_mean_volume": summarize_ratios(sub, "init_risked", "final_risked"),
        }

    by_3d_seismic = {
        "with_new_or_reprocessed_3d": {
            "mean_volume": summarize_ratios([r for r in paired_records if r["has_new_3d"]], "init_mean", "final_mean"),
            "mean_volume_reevaluated_only": summarize_ratios(
                [r for r in paired_records if r["has_new_3d"]], "init_mean", "final_mean", changed_only=True
            ),
            "pg": summarize_pg_drift([r for r in paired_records if r["has_new_3d"]]),
        },
        "without_new_3d_mention": {
            "mean_volume": summarize_ratios([r for r in paired_records if not r["has_new_3d"]], "init_mean", "final_mean"),
            "mean_volume_reevaluated_only": summarize_ratios(
                [r for r in paired_records if not r["has_new_3d"]], "init_mean", "final_mean", changed_only=True
            ),
            "pg": summarize_pg_drift([r for r in paired_records if not r["has_new_3d"]]),
        },
    }

    biggest_shrinkers = sorted(
        [
            r for r in paired_records
            if r["init_mean"] is not None and r["final_mean"] is not None and r["init_mean"] >= 20.0
        ],
        key=lambda r: r["final_mean"] / r["init_mean"],
    )[:10]

    biggest_growers = sorted(
        [
            r for r in paired_records
            if r["init_mean"] is not None and r["final_mean"] is not None and r["init_mean"] >= 5.0
        ],
        key=lambda r: -(r["final_mean"] / r["init_mean"]),
    )[:10]

    total_p = len(prospect_drop_rows)
    undrilled_drop_rows = [r for r in prospect_drop_rows if not r["drilled"]]
    n_undrilled = len(undrilled_drop_rows)

    primary_counts_all = Counter(r["primary_cat"] for r in prospect_drop_rows)
    primary_counts_undrilled = Counter(r["primary_cat"] for r in undrilled_drop_rows)
    tag_counts_all = Counter(t for r in prospect_drop_rows for t in r["reasons"])
    nt_subtype_counts_undrilled = Counter(s for r in undrilled_drop_rows for s in r["nt_subtypes"])

    drop_by_basin: dict[str, Any] = {}
    for b in ("North Sea", "Norwegian Sea", "Barents Sea"):
        sub = [r for r in undrilled_drop_rows if r["basin"] == b]
        nb = len(sub)
        pc = Counter(r["primary_cat"] for r in sub)
        ntc = Counter(s for r in sub for s in r["nt_subtypes"])
        drop_by_basin[b] = {
            "n_undrilled": nb,
            "primary_pct": {k: round(100.0 * v / nb, 1) for k, v in pc.items()} if nb else {},
            "any_geo_pct": round(100.0 * sum(1 for r in sub if r["has_geo"]) / nb, 1) if nb else 0.0,
            "any_commercial_pct": round(100.0 * sum(1 for r in sub if r["has_comm"]) / nb, 1) if nb else 0.0,
            "any_nontech_pct": round(100.0 * sum(1 for r in sub if r["has_nontech"]) / nb, 1) if nb else 0.0,
            "non_tech_subtypes": dict(ntc.most_common()),
        }

    dedup_post_award, dups_pa = deduplicate_straddling_prize(undrilled_prize_post_award)
    dedup_all_stages, dups_all = deduplicate_straddling_prize(undrilled_prize_all_stages)

    def summarize_prize(cands: list[dict[str, Any]]) -> dict[str, Any]:
        by_b: dict[str, Any] = {}
        for b in ("North Sea", "Norwegian Sea", "Barents Sea"):
            sub = [c for c in cands if c["basin"] == b]
            by_b[b] = {
                "n": len(sub),
                "unrisked_msmo3": round(sum(c["unrisked_mean_msmo3"] for c in sub), 2),
                "unrisked_mmboe": round(sum(c["unrisked_mean_msmo3"] for c in sub) * MSMO3_TO_MMBOE, 1),
                "risked_msmo3": round(sum(c["risked_mean_msmo3"] for c in sub), 2),
                "risked_mmboe": round(sum(c["risked_mean_msmo3"] for c in sub) * MSMO3_TO_MMBOE, 1),
            }
        by_ph: dict[str, Any] = {}
        for ph in sorted(set(c["phase"] for c in cands)):
            sub = [c for c in cands if c["phase"] == ph]
            by_ph[ph] = {
                "n": len(sub),
                "unrisked_msmo3": round(sum(c["unrisked_mean_msmo3"] for c in sub), 2),
                "risked_msmo3": round(sum(c["risked_mean_msmo3"] for c in sub), 2),
            }
        tot_u = sum(c["unrisked_mean_msmo3"] for c in cands)
        tot_r = sum(c["risked_mean_msmo3"] for c in cands)
        return {
            "n": len(cands),
            "total_unrisked_msmo3": round(tot_u, 2),
            "total_unrisked_mmboe": round(tot_u * MSMO3_TO_MMBOE, 1),
            "total_risked_msmo3": round(tot_r, 2),
            "total_risked_mmboe": round(tot_r * MSMO3_TO_MMBOE, 1),
            "by_basin": by_b,
            "by_phase": by_ph,
        }

    pa_comm_20 = [c for c in dedup_post_award if c["dropped_comm_or_nt"]]
    pa_comm_25 = [c for c in pa_comm_20 if c["pg"] >= 0.25]
    all_comm_20 = [c for c in dedup_all_stages if c["dropped_comm_or_nt"]]
    all_comm_25 = [c for c in all_comm_20 if c["pg"] >= 0.25]
    pa_all_25 = [c for c in dedup_post_award if c["pg"] >= 0.25]
    all_all_25 = [c for c in dedup_all_stages if c["pg"] >= 0.25]

    top_15_post_award = sorted(pa_comm_20, key=lambda c: -c["risked_mean_msmo3"])[:15]
    top_15_all_stages = sorted(all_comm_20, key=lambda c: -c["risked_mean_msmo3"])[:15]
    top_15_post_award_oil = sorted(
        [c for c in pa_comm_20 if c["phase"] in ("oil", "oil_and_gas")],
        key=lambda c: -c["risked_mean_msmo3"],
    )[:10]

    results = {
        "dataset": {
            "raw_licences": len(raw_j),
            "deduplicated_licences": len(kept_j),
            "dropped_duplicate_files": sorted(dropped_stems),
            "total_prospects": all_prospects_count,
            "extra_unit_anomalies_fixed": anomalies_caught,
            "straddling_prize_duplicates_merged": {"post_award": dups_pa, "all_stages": dups_all},
            "excluded_pg_100_appraisal_segments": excluded_pg_100,
        },
        "track3_part1_optimism_tax": {
            "overall": drift_overall,
            "by_basin": by_basin,
            "by_operator": by_operator,
            "by_award_decade": by_award_decade,
            "by_relinquishment_decade": by_relinq_decade,
            "by_3d_seismic_activity": by_3d_seismic,
            "notable_shrinkers_init_ge_20msmo3": [
                {
                    "licence_id": r["licence_id"],
                    "name": r["name"],
                    "basin": r["basin"],
                    "operator": r["operator"],
                    "init_mean": round(r["init_mean"], 2),
                    "final_mean": round(r["final_mean"], 2),
                    "ratio": round(r["final_mean"] / r["init_mean"], 3),
                    "init_pg": r["init_pg"],
                    "final_pg": r["final_pg"],
                    "status": r["status"],
                }
                for r in biggest_shrinkers
            ],
            "notable_growers_init_ge_5msmo3": [
                {
                    "licence_id": r["licence_id"],
                    "name": r["name"],
                    "basin": r["basin"],
                    "operator": r["operator"],
                    "init_mean": round(r["init_mean"], 2),
                    "final_mean": round(r["final_mean"], 2),
                    "ratio": round(r["final_mean"] / r["init_mean"], 3),
                    "init_pg": r["init_pg"],
                    "final_pg": r["final_pg"],
                    "status": r["status"],
                }
                for r in biggest_growers
            ],
        },
        "track3_part2_walk_away_reasons": {
            "total_prospects": total_p,
            "total_undrilled_prospects": n_undrilled,
            "primary_category_all_prospects": {
                k: {"count": v, "pct": round(100.0 * v / total_p, 1)}
                for k, v in primary_counts_all.most_common()
            },
            "primary_category_undrilled": {
                k: {"count": v, "pct": round(100.0 * v / n_undrilled, 1)}
                for k, v in primary_counts_undrilled.most_common()
            },
            "multi_label_undrilled": {
                "any_geo_risk": {
                    "count": sum(1 for r in undrilled_drop_rows if r["has_geo"]),
                    "pct": round(100.0 * sum(1 for r in undrilled_drop_rows if r["has_geo"]) / n_undrilled, 1),
                },
                "any_commercial_or_size": {
                    "count": sum(1 for r in undrilled_drop_rows if r["has_comm"]),
                    "pct": round(100.0 * sum(1 for r in undrilled_drop_rows if r["has_comm"]) / n_undrilled, 1),
                },
                "any_non_technical": {
                    "count": sum(1 for r in undrilled_drop_rows if r["has_nontech"]),
                    "pct": round(100.0 * sum(1 for r in undrilled_drop_rows if r["has_nontech"]) / n_undrilled, 1),
                },
            },
            "structured_reasons_not_drilled_tags": dict(tag_counts_all.most_common()),
            "non_tech_subtypes_undrilled_prospects": {
                k: {"count": v, "pct_of_undrilled": round(100.0 * v / n_undrilled, 2)}
                for k, v in nt_subtype_counts_undrilled.most_common()
            },
            "non_tech_subtypes_licences_full": {
                k: {"count": v, "pct_of_738_licences": round(100.0 * v / len(records), 1)}
                for k, v in licence_non_tech_counter.most_common()
            },
            "non_tech_licences_by_basin_pct": {
                b: {
                    k: round(100.0 * v / licence_count_by_basin[b], 1)
                    for k, v in c.most_common()
                }
                for b, c in licence_non_tech_by_basin.items()
            },
            "undrilled_by_basin": drop_by_basin,
        },
        "track3_part3_untested_prize": {
            "post_award_assessed_all_pg_ge_020": summarize_prize(dedup_post_award),
            "post_award_assessed_comm_or_nt_pg_ge_020": summarize_prize(pa_comm_20),
            "post_award_assessed_all_pg_ge_025": summarize_prize(pa_all_25),
            "post_award_assessed_comm_or_nt_pg_ge_025": summarize_prize(pa_comm_25),
            "all_stages_incl_app_fallback_all_pg_ge_020": summarize_prize(dedup_all_stages),
            "all_stages_incl_app_fallback_comm_or_nt_pg_ge_020": summarize_prize(all_comm_20),
            "all_stages_incl_app_fallback_all_pg_ge_025": summarize_prize(all_all_25),
            "all_stages_incl_app_fallback_comm_or_nt_pg_ge_025": summarize_prize(all_comm_25),
            "top_15_post_award_comm_nt_pg20": top_15_post_award,
            "top_15_all_stages_comm_nt_pg20": top_15_all_stages,
            "top_10_post_award_oil_comm_nt_pg20": top_15_post_award_oil,
        },
    }

    OUTPUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUTPUT_JSON}")

    print("\n=== PART 1: RE-EVALUATED VS ALL PAIRED ===")
    mv_all = drift_overall["all_paired"]["mean_volume"]
    mv_re = drift_overall["all_paired"]["mean_volume_reevaluated_only"]
    pg_all = drift_overall["all_paired"]["pg"]
    pg_re = drift_overall["all_paired"]["pg_reevaluated_only"]
    rv_all = drift_overall["all_paired"]["risked_mean_volume"]
    rv_re = drift_overall["all_paired"]["risked_mean_volume_reevaluated_only"]
    print(f"Mean Vol ALL  (n={mv_all['n']}): shrank={mv_all['pct_shrank']}%, unch={mv_all['pct_unchanged']}%, grew={mv_all['pct_grew']}%, med={mv_all['median_ratio']}, port={mv_all['portfolio_ratio']}")
    print(f"Mean Vol REEV (n={mv_re['n']}): shrank={mv_re['pct_shrank']}%, grew={mv_re['pct_grew']}%, med={mv_re['median_ratio']}, geom={mv_re['geom_mean_ratio']}, port={mv_re['portfolio_ratio']}")
    print(f"Pg ALL        (n={pg_all['n']}): drop={pg_all['pct_dropped']}%, unch={pg_all['pct_unchanged']}%, inc={pg_all['pct_increased']}%, mean {pg_all['mean_initial_pg_pct']}%->{pg_all['mean_final_pg_pct']}% ({pg_all['mean_diff_pp']}pp)")
    print(f"Pg REEV       (n={pg_re['n']}): drop={pg_re['pct_dropped']}%, inc={pg_re['pct_increased']}%, mean {pg_re['mean_initial_pg_pct']}%->{pg_re['mean_final_pg_pct']}% ({pg_re['mean_diff_pp']}pp, med={pg_re['median_diff_pp']}pp)")
    print(f"Risked REEV   (n={rv_re['n']}): shrank={rv_re['pct_shrank']}%, med={rv_re['median_ratio']}, geom={rv_re['geom_mean_ratio']}, port={rv_re['portfolio_ratio']}")

    print("\nBy Basin (Re-evaluated Only):")
    for b, d in by_basin.items():
        bm = d["mean_volume_reevaluated_only"]
        bp = d["pg_reevaluated_only"]
        print(f"  {b:14s} Vol_Reev(n={bm['n']:3d}): shrank={bm['pct_shrank']:4.1f}%, med={bm['median_ratio']:.3f}, port={bm['portfolio_ratio']:.3f} | Pg_Reev(n={bp['n']:3d}): drop={bp['pct_dropped']:4.1f}%, mean_diff={bp['mean_diff_pp']:+.1f}pp")

    print("\nBy Operator (Re-evaluated Only, n_all >= 8):")
    for op, d in by_operator.items():
        bm = d["mean_volume"]
        bmr = d["mean_volume_reevaluated_only"]
        bp = d["pg"]
        if bm["n"] >= 8:
            print(f"  {op:28s} All(n={bm['n']:2d}, med={bm['median_ratio']:.3f}, port={bm['portfolio_ratio']:.3f}) | Reev(n={bmr['n']:2d}, shrank={bmr.get('pct_shrank',0):4.1f}%, med={bmr.get('median_ratio',0):.3f}) | Pg(n={bp['n']:2d}, {bp.get('mean_diff_pp',0):+.1f}pp)")

    print("\n=== PART 2: LICENCE-LEVEL NON-TECHNICAL REASONS (FULL, n=738) ===")
    for k, v in results["track3_part2_walk_away_reasons"]["non_tech_subtypes_licences_full"].items():
        print(f"  {k:32s}: {v['count']:3d} ({v['pct_of_738_licences']:4.1f}%)")
    print("Non-tech licences by basin (%):")
    for b, d in results["track3_part2_walk_away_reasons"]["non_tech_licences_by_basin_pct"].items():
        print(f"  {b}: {d}")

    print("\n=== PART 3: DEDUPLICATED UNTESTED PRIZE ===")
    for label in (
        "post_award_assessed_comm_or_nt_pg_ge_020",
        "post_award_assessed_comm_or_nt_pg_ge_025",
        "all_stages_incl_app_fallback_comm_or_nt_pg_ge_020",
        "all_stages_incl_app_fallback_comm_or_nt_pg_ge_025",
    ):
        s = results["track3_part3_untested_prize"][label]
        print(f"  {label:48s}: n={s['n']:3d} | unrisked={s['total_unrisked_msmo3']:7.1f} MSm3 ({s['total_unrisked_mmboe']:7.0f} MMboe) | risked={s['total_risked_msmo3']:6.1f} MSm3 ({s['total_risked_mmboe']:6.0f} MMboe)")

    print("\nTop 12 Post-Award Assessed Undrilled Relinquished Prospects (Pg>=0.20, Comm/Non-Tech):")
    for i, c in enumerate(top_15_post_award[:12], 1):
        print(f"  {i:2d}. {c['name']} ({c['licence_id']}, {c['basin']}, {c['operator']}, {c['relinq_year']}) | {c['unrisked_mean_msmo3']} MSm3 ({c['unrisked_mean_mmboe']} MMboe) | Pg={c['pg']*100:.0f}% | Risked={c['risked_mean_msmo3']} MSm3 ({c['risked_mean_mmboe']} MMboe) | {c['phase']} | stage={c['vol_stage']}")


if __name__ == "__main__":
    main()
