import json
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

DEFAULT_DOWNLOADS = Path(r"C:\Users\philip\Downloads")
DEFAULT_FACTPAGES_WELLS = Path(
    r"C:\Users\philip\Documents\wellbore-completion\data\factpages\wellbore_exploration_all.parquet"
)
ZIP_GLOB = "756_Norwegian_licence_relinquishment_reports_with_geojson_prospect_outlines_part*of5.zip"


def load_raw_records(
    downloads_dir: Path = DEFAULT_DOWNLOADS,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    json_records: dict[str, dict[str, Any]] = {}
    geojson_records: dict[str, dict[str, Any]] = {}
    for zpath in sorted(downloads_dir.glob(ZIP_GLOB)):
        with zipfile.ZipFile(zpath) as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                stem = Path(name).stem
                if name.endswith(".json"):
                    json_records[stem] = json.loads(zf.read(name))
                elif name.endswith(".geojson"):
                    geojson_records[stem] = json.loads(zf.read(name))
    return json_records, geojson_records


def find_duplicate_licence_groups(
    json_records: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    by_lic: dict[str, list[str]] = defaultdict(list)
    for stem, rec in json_records.items():
        lic = (rec.get("licence") or {}).get("licence_id")
        if lic:
            by_lic[lic].append(stem)
    return {k: sorted(v) for k, v in by_lic.items() if len(v) > 1}


def deduplicate_records(
    json_records: dict[str, dict[str, Any]],
    geojson_records: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], set[str]]:
    dup_groups = find_duplicate_licence_groups(json_records)
    dropped: set[str] = set()
    for stems in dup_groups.values():
        ranked = sorted(
            stems,
            key=lambda s: (
                -len(json_records[s].get("prospects") or []),
                s,
            ),
        )
        dropped.update(ranked[1:])
    kept_json = {k: v for k, v in json_records.items() if k not in dropped}
    kept_geo = {k: v for k, v in geojson_records.items() if k not in dropped}
    return kept_json, kept_geo, dropped


def safe_canonical_volume_msmo3(vol: dict[str, Any], field: str = "mean") -> float | None:
    dist = vol.get("distribution") or {}
    us = (dist.get("_derived") or {}).get("unit_scale") or {}
    cunit = us.get("canonical_unit")
    cvals = us.get("values") or {}
    raw_unit = str(dist.get("unit") or "").strip()
    val = cvals.get(field)
    if not isinstance(val, (int, float)) or isinstance(val, bool):
        return None
    if raw_unit.lower() == "bcf" and cunit == "1e6 Sm3 o.e." and us.get("factor", 1) > 10:
        return float(val) / 1000.0
    if raw_unit == "GSm³ OE" and cunit == "1e6 Sm3 o.e." and us.get("factor") == 1000.0:
        return float(val) / 1000.0
    if (
        vol.get("phase") == "condensate"
        and raw_unit.lower().replace(" ", "") == "1e9sm3"
        and cunit == "1e6 Sm3"
        and us.get("factor") == 1000.0
        and float(val) > 500.0
    ):
        return float(val) / 1000.0
    if cunit == "1e6 Sm3 o.e.":
        return float(val)
    if cunit == "1e6 Sm3":
        return float(val)
    if cunit == "1e9 Sm3":
        return float(val)
    return None
