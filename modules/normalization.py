"""
modules/normalization.py
Unicode normalizer, field-value formatters, column renamer, and
auto-normalize-on-schema-activate helpers.
"""

import datetime
import re

import streamlit as st

from config.settings import DATE_FMT_MAP

# ── Unicode dash/quote normalizer ─────────────────────────────────────────────
_DASH_TABLE = str.maketrans({
    '\u2013': '-', '\u2014': '-', '\u2012': '-', '\u2015': '-',
    '\u2212': '-', '\ufe58': '-', '\ufe63': '-', '\uff0d': '-',
    '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
    '\u00a0': ' ', '\u202f': ' ',
})


def normalize_str(s: str) -> str:
    if not s:
        return s
    return s.translate(_DASH_TABLE)


# ── Date helpers ──────────────────────────────────────────────────────────────

def _parse_date_flexible(val: str):
    val = val.strip().replace("\u2013", "-").replace("\u2014", "-")
    for fmt in [
        "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%d-%m-%Y",
        "%m/%d/%y", "%m-%d-%y", "%d/%m/%y", "%Y/%m/%d",
        "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y",
        "%d %B %Y", "%d %b %Y",
    ]:
        try:
            return datetime.datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _format_date_for_schema(val: str, schema_name: str) -> str:
    from config.schemas import SCHEMAS
    if not val or not val.strip():
        return val
    parsed  = _parse_date_flexible(val.strip())
    if parsed is None:
        return val
    fmt_key = SCHEMAS.get(schema_name, {}).get("date_format", "YYYY-MM-DD")
    strfmt  = DATE_FMT_MAP.get(fmt_key, "%Y-%m-%d")
    return parsed.strftime(strfmt)


def _format_amount_for_schema(val: str) -> str:
    if not val or not val.strip():
        return val
    s      = val.strip()
    is_neg = s.startswith("(") and s.endswith(")")
    s      = s.replace("$", "").replace(",", "").replace("(", "").replace(")", "").strip()
    try:
        num = float(s)
        if is_neg:
            num = -abs(num)
        return f"{num:.2f}"
    except ValueError:
        return val


def _format_status_for_schema(val: str, schema_name: str) -> str:
    from config.schemas import SCHEMAS
    if not val or not val.strip():
        return val
    allowed = SCHEMAS.get(schema_name, {}).get("status_values", [])
    v_lower = val.strip().lower()
    for sv in allowed:
        if sv.lower() == v_lower:
            return sv
    _synonyms = {
        "open":      ["open", "active", "in progress", "inprogress", "new", "opened"],
        "closed":    ["closed", "close", "completed", "done", "finalized", "resolved"],
        "pending":   ["pending", "pend", "on hold", "hold", "waiting", "review"],
        "reopened":  ["reopen", "reopened", "re-opened", "re open"],
        "reopen":    ["reopen", "reopened", "re-opened", "re open"],
        "denied":    ["denied", "deny", "rejected", "reject", "declined"],
        "submitted": ["submitted", "submit", "filed"],
        "draft":     ["draft", "drafting"],
        "settled":   ["settled", "settlement"],
    }
    for canonical, syns in _synonyms.items():
        if v_lower in syns or v_lower == canonical:
            for sv in allowed:
                if sv.lower() == canonical:
                    return sv
    return val


def _format_name_for_schema(val: str) -> str:
    if not val or not val.strip():
        return val
    _keep_upper = {"llc", "inc", "lp", "llp", "na", "n/a", "dba", "usa", "us", "uk", "ltd", "corp", "co"}
    parts  = val.strip().split()
    result = []
    for part in parts:
        if part.lower() in _keep_upper:
            result.append(part.upper())
        else:
            result.append(part.capitalize())
    return " ".join(result)


def _format_state_for_schema(val: str) -> str:
    if not val or not val.strip():
        return val
    v = val.strip()
    if len(v) == 2:
        return v.upper()
    _st = {
        "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
        "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
        "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
        "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
        "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
        "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
        "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
        "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
        "new mexico": "NM", "new york": "NY", "north carolina": "NC",
        "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
        "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
        "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
        "vermont": "VT", "virginia": "VA", "washington": "WA",
        "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
        "district of columbia": "DC",
    }
    return _st.get(v.lower(), v)


def _format_boolean_for_schema(val: str) -> str:
    if not val or not val.strip():
        return val
    v = val.strip().lower()
    if v in ("yes", "y", "true", "1", "x"):
        return "true"
    if v in ("no", "n", "false", "0"):
        return "false"
    return val


# ── Field-pattern regexes ─────────────────────────────────────────────────────
_DATE_FIELD_PAT   = re.compile(r"date|loss\s*dt|incident\s*dt|injury\s*dt|accident\s*dt|closed\s*dt|reopen\s*dt|updated\s*dt|effective\s*dt|expiry\s*dt", re.IGNORECASE)
_AMOUNT_FIELD_PAT = re.compile(r"incurred|paid|reserve|amount|deductible|recovery|subrogation|damage|bi\s*loss|interruption", re.IGNORECASE)
_STATUS_FIELD_PAT = re.compile(r"\bstatus\b|open.?closed", re.IGNORECASE)
_NAME_FIELD_PAT   = re.compile(r"(claimant|insured|adjuster|employer|driver|employee|injured)\s*(name)?$|^name$", re.IGNORECASE)
_STATE_FIELD_PAT  = re.compile(r"\bstate\b|\bjurisdiction\b|\bstate\s*code\b", re.IGNORECASE)
_BOOL_FIELD_PAT   = re.compile(r"\bat\s*fault\b|\blitigation\s*flag\b|\bsubrogation\s*flag\b", re.IGNORECASE)


def auto_normalize_field(field_name: str, value: str, schema_name: str) -> str:
    if not value or not str(value).strip():
        return value
    v  = str(value).strip()
    fn = field_name.strip()
    if _DATE_FIELD_PAT.search(fn):    return _format_date_for_schema(v, schema_name)
    if _AMOUNT_FIELD_PAT.search(fn):  return _format_amount_for_schema(v)
    if _STATUS_FIELD_PAT.search(fn):  return _format_status_for_schema(v, schema_name)
    if _NAME_FIELD_PAT.search(fn):    return _format_name_for_schema(v)
    if _STATE_FIELD_PAT.search(fn):   return _format_state_for_schema(v)
    if _BOOL_FIELD_PAT.search(fn):    return _format_boolean_for_schema(v)
    return v


def auto_normalize_claim(claim_data: dict, schema_name: str) -> dict:
    changes: dict = {}
    for field, info in claim_data.items():
        original   = info.get("modified") or info.get("value", "")
        if not original:
            continue
        normalized = auto_normalize_field(field, str(original), schema_name)
        if normalized != original:
            changes[field] = normalized
    return changes


def auto_normalize_on_schema_activate(data: list, schema_name: str, selected_sheet: str) -> None:
    """
    Writes normalised values ONLY to session_state — never to claim["modified"].
    This ensures the Extracted column always shows the raw Excel value.
    Modified column only diverges when the user explicitly edits a field.
    """
    from modules.schema_mapping import detect_claim_id
    for i, claim in enumerate(data):
        claim_id = detect_claim_id(claim, i)
        changes  = auto_normalize_claim(claim, schema_name)
        for field, new_val in changes.items():
            mk_schema = f"mod_{selected_sheet}_{claim_id}_schema_{field}"
            mk_plain  = f"mod_{selected_sheet}_{claim_id}_{field}"
            # Only set if the user hasn't already edited manually
            if mk_schema not in st.session_state:
                st.session_state[mk_schema] = new_val
            if mk_plain not in st.session_state:
                st.session_state[mk_plain] = new_val
            # DO NOT write to claim[field]["modified"] — that would change the
            # Extracted column display which must always show the raw Excel value


# ── Standard-name renamer ─────────────────────────────────────────────────────
_STANDARD_NAME_MAP: dict[str, str] = {
    "claim number": "Claim Number", "claim id": "Claim Number", "claim ref": "Claim Number",
    "claim no": "Claim Number", "file number": "Claim Number", "file no": "Claim Number",
    "ref no": "Claim Number", "reference": "Claim Number", "loss ref": "Claim Number",
    "loss date": "Loss Date", "date of loss": "Loss Date", "incident date": "Loss Date",
    "accident date": "Loss Date", "injury date": "Loss Date", "occurrence date": "Loss Date",
    "date reported": "Date Reported", "report date": "Date Reported", "reported date": "Date Reported",
    "open date": "Date Reported", "date closed": "Date Closed", "close date": "Date Closed",
    "claimant name": "Claimant Name", "claimant": "Claimant Name", "injured party": "Claimant Name",
    "employee name": "Claimant Name", "driver name": "Claimant Name", "plaintiff": "Claimant Name",
    "person": "Claimant Name",
    "insured name": "Insured Name", "insured": "Insured Name", "policyholder": "Insured Name",
    "named insured": "Insured Name", "customer": "Insured Name", "account name": "Insured Name",
    "adjuster name": "Adjuster Name", "adjuster": "Adjuster Name", "examiner": "Adjuster Name",
    "handler": "Adjuster Name", "claim handler": "Adjuster Name",
    "policy number": "Policy Number", "policy no": "Policy Number", "policy id": "Policy Number",
    "policy code": "Policy Number", "pol no": "Policy Number",
    "total incurred": "Total Incurred", "incurred": "Total Incurred", "total cost": "Total Incurred",
    "gross incurred": "Total Incurred", "total exposure": "Total Incurred",
    "total paid": "Total Paid", "amount paid": "Total Paid", "paid amount": "Total Paid",
    "disbursed": "Total Paid", "total disbursed": "Total Paid",
    "reserve": "Reserve", "case reserve": "Reserve", "outstanding reserve": "Reserve",
    "indemnity paid": "Indemnity Paid", "indemnity": "Indemnity Paid", "wage loss": "Indemnity Paid",
    "medical paid": "Medical Paid", "medical": "Medical Paid", "med paid": "Medical Paid",
    "expense paid": "Expense Paid", "expense": "Expense Paid", "legal expense": "Expense Paid",
    "status": "Status", "claim status": "Status", "current status": "Status",
    "open closed": "Status", "file status": "Status",
    "description of loss": "Description of Loss", "loss description": "Description of Loss",
    "narrative": "Description of Loss", "incident description": "Description of Loss",
    "nature of claim": "Description of Loss", "what happened": "Description of Loss",
    "cause of loss": "Cause of Loss", "cause": "Cause of Loss", "peril": "Cause of Loss",
    "type of loss": "Cause of Loss",
    "line of business": "Line of Business", "lob": "Line of Business", "coverage line": "Line of Business",
    "coverage type": "Coverage Type", "coverage": "Coverage Type",
    "state": "State", "jurisdiction": "State", "state code": "State",
    "location": "Location", "property location": "Location", "site": "Location",
    "days lost": "Days Lost", "disability days": "Days Lost",
    "body part": "Body Part", "body part injured": "Body Part",
    "job title": "Job Title", "occupation": "Job Title",
    "vehicle id": "Vehicle ID", "vin": "Vehicle ID",
    "at fault": "At Fault", "fault": "At Fault",
    "deductible": "Deductible", "deductible amount": "Deductible",
    "notes": "Notes", "comments": "Notes",
    "ref": "Claim Number", "peep name": "Adjuster Name", "situation": "Status",
    "cost nugget": "Total Incurred", "ouch cost": "Total Incurred",
    "gave out": "Total Paid", "already gave": "Total Paid",
    "saving": "Reserve", "saving for": "Reserve",
    "boo happen": "Loss Date", "told us": "Date Reported",
    "wobble code": "Policy Number", "flubber title": "Insured Name",
    "got ouchie": "Claimant Name", "went wrong": "Description of Loss",
    "incident gibberish": "Description of Loss", "status blobble": "Status",
    "paid zork": "Total Paid", "reserve flumple": "Reserve",
    "incurred nizzle": "Total Incurred", "report flargle": "Date Reported",
    "nugget ref": "Claim Number", "claimant squawk": "Claimant Name",
    "blorp name": "Insured Name", "policy tag": "Policy Number",
    "blargle": "Claim Number", "zog flibber": "Loss Date", "flibber date": "Loss Date",
}


def _semantic_tokens(name: str) -> list[str]:
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', s)
    s = re.sub(r'[^a-zA-Z]+', ' ', s)
    return [t.lower() for t in s.split() if len(t) > 1]


def _best_standard_name(raw_col: str) -> str | None:
    tokens = _semantic_tokens(raw_col)
    if not tokens:
        return None
    candidates: dict[str, int] = {}
    for n in range(1, min(5, len(tokens) + 1)):
        for start in range(len(tokens) - n + 1):
            phrase = " ".join(tokens[start: start + n])
            if phrase in _STANDARD_NAME_MAP:
                std   = _STANDARD_NAME_MAP[phrase]
                score = n * 10 - start
                if std not in candidates or score > candidates[std]:
                    candidates[std] = score
    if not candidates:
        return None
    best       = max(candidates, key=candidates.get)
    best_score = candidates[best]
    if best_score < 8:
        return None
    return best


def rename_columns_to_standard(data: list, llm_map: dict = None) -> tuple[list, dict]:
    if not data:
        return data, {}
    all_cols   = list(data[0].keys())
    rename_map = {}
    used_std   = set()
    for col in all_cols:
        std = _best_standard_name(col)
        if std and std not in used_std:
            rename_map[col] = std
            used_std.add(std)
    if llm_map:
        for src_col, schema_field in llm_map.get("mappings", {}).items():
            if src_col in all_cols and src_col not in rename_map and schema_field not in used_std:
                rename_map[src_col] = schema_field
                used_std.add(schema_field)
    if not rename_map:
        return data, {}
    renamed_data = []
    for row in data:
        new_row = {rename_map.get(col, col): info for col, info in row.items()}
        renamed_data.append(new_row)
    return renamed_data, rename_map
