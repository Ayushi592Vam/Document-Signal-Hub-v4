"""
modules/dup_detection.py
Field-level duplicate detection across claims in a sheet.
"""

from modules.schema_mapping import detect_claim_id


def _build_field_value_index(data: list, selected_sheet: str) -> dict:
    """
    Build an index: {field_name: {value_lower: [claim_ids]}}
    Used to detect fields that carry the same value across multiple claims.
    """
    index: dict = {}
    for i, claim in enumerate(data):
        cid = detect_claim_id(claim, i)
        for field, info in claim.items():
            val = str(info.get("modified") or info.get("value", "")).strip()
            if not val:
                continue
            vl = val.lower()
            if field not in index:
                index[field] = {}
            if vl not in index[field]:
                index[field][vl] = []
            if cid not in index[field][vl]:
                index[field][vl].append(cid)
    return index


def _field_dup_confidence(val: str, field: str, field_index: dict) -> tuple[int, list]:
    """
    Returns (dup_confidence 0-100, list_of_other_claim_ids_with_same_value).
    0 means unique.
    """
    if not val:
        return 0, []
    vl     = val.strip().lower()
    others = [cid for cid in field_index.get(field, {}).get(vl, []) if cid != ""]
    if len(others) <= 1:
        return 0, []
    dup_conf = min(100, 60 + len(others) * 10)
    return dup_conf, others
