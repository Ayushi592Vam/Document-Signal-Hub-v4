"""
modules/enrichment.py
LLM-powered Cause-of-Loss extraction and claim enrichment.
"""

import re
import datetime

import streamlit as st

from modules.audit import _append_audit
from modules.llm import _llm_available, _llm_call

# ── Taxonomy definitions ──────────────────────────────────────────────────────
_COL_TAXONOMY_GENERAL = [
    "Slip and Fall", "Trip and Fall", "Vehicle Collision", "Rear-End Collision",
    "Fire - Electrical", "Fire - Arson", "Fire - Unknown", "Theft", "Burglary",
    "Vandalism", "Water Damage - Flood", "Water Damage - Pipe", "Wind / Hail",
    "Lightning", "Earthquake", "Product Liability", "Professional Error",
    "Medical Malpractice", "Assault / Battery", "Equipment Failure",
    "Explosion", "Repetitive Stress Injury", "Strain / Sprain",
    "Animal Bite", "Falling Object", "Other",
]
_COL_TAXONOMY_PROF_LIABILITY = [
    "Negligent Advice", "Unsuitable Product Recommendation", "Misrepresentation",
    "Failure to Execute Instructions", "Breach of Fiduciary Duty",
    "Conflict of Interest", "Unauthorized Trading", "Due Diligence Failure",
    "Inadequate Risk Assessment", "Failure to Disclose", "Elder Financial Abuse",
    "Fraud / Intentional Misrepresentation", "Omission of Material Fact",
    "Portfolio Mismanagement", "Failure to Supervise", "Other - Professional Liability",
]
_COL_TAXONOMY_WORKERS_COMP = [
    "Strain / Sprain - Back", "Strain / Sprain - Shoulder", "Strain / Sprain - Knee",
    "Laceration", "Fracture", "Contusion / Bruising", "Slip and Fall", "Trip and Fall",
    "Repetitive Stress Injury", "Occupational Disease", "Heat / Chemical Exposure",
    "Electrical Injury", "Crush Injury", "Vehicle Accident - Work Related",
    "Falling Object", "Equipment Failure", "Other - Workers Comp",
]
_COL_TAXONOMY_AUTO = [
    "Rear-End Collision", "Side-Impact Collision", "Head-On Collision",
    "Single Vehicle Accident", "Pedestrian Strike", "Uninsured Motorist",
    "Hit and Run", "Backing Accident", "Vehicle Rollover", "Weather-Related Collision",
    "DUI-Related Accident", "Vehicle Theft", "Vandalism", "Other - Auto",
]
_COL_TAXONOMY_PROPERTY = [
    "Fire - Electrical", "Fire - Arson", "Fire - Unknown", "Water Damage - Pipe",
    "Water Damage - Flood", "Wind / Hail Damage", "Lightning Strike", "Earthquake",
    "Theft / Burglary", "Vandalism", "Collapse", "Equipment Breakdown", "Mold",
    "Sinkhole", "Other - Property",
]


def _pick_taxonomy(sheet_name: str, claim_text: str) -> list:
    s = (sheet_name + " " + claim_text).lower()
    if any(x in s for x in ["prof liab", "professional liab", "e&o", "errors", "fiduciary", "advisory", "malpractice"]):
        return _COL_TAXONOMY_PROF_LIABILITY
    if any(x in s for x in ["workers comp", "work comp", "wc loss", "injury", "strain", "sprain", "lacerat"]):
        return _COL_TAXONOMY_WORKERS_COMP
    if any(x in s for x in ["auto", "vehicle", "collision", "motor", "driving", "fleet"]):
        return _COL_TAXONOMY_AUTO
    if any(x in s for x in ["property", "building", "premises", "fire", "water damage", "theft", "hail"]):
        return _COL_TAXONOMY_PROPERTY
    return _COL_TAXONOMY_GENERAL


def _llm_extract_cause_of_loss(description_text: str, sheet_name: str = "") -> dict:
    taxonomy     = _pick_taxonomy(sheet_name, description_text)
    taxonomy_str = "\n".join(f"- {t}" for t in taxonomy)
    prompt = (
        "You are an insurance claims analyst. Read the loss description and:\n"
        "1. Pick the SINGLE best-matching cause of loss from the taxonomy below.\n"
        "   You MUST choose exactly one label from the list — do not invent new labels.\n"
        "   If nothing fits well, choose 'Other' or the most similar 'Other - ...' entry.\n"
        "2. Write one factual plain-English sentence summarizing what the claimant alleges happened.\n"
        "   Base the summary ONLY on the text provided — do not invent facts.\n\n"
        f"TAXONOMY (choose one exactly as written):\n{taxonomy_str}\n\n"
        f"LOSS DESCRIPTION:\n{description_text[:1200]}\n\n"
        'Reply ONLY with valid JSON, no markdown, no explanation:\n'
        '{"cause_of_loss": "<exact taxonomy label>", "summary": "<one sentence>"}'
    )
    raw = _llm_call(prompt, max_tokens=120)
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    return __import__("json").loads(raw)


_DESC_PAT = re.compile(
    r"desc|narr|detail|note|comment|descript|loss\s*desc|allegation"
    r"|nature|nature.of.claim|nature.of.loss|nature.of.injury"
    r"|type.of.claim|type.of.loss|cause.of.loss"
    r"|services.involved|service.type"
    r"|injury.type|accident.type|incident.type"
    r"|claim.type|peril|event.type"
    r"|description.of.loss|what.happened|loss.description"
    r"|went.wrong|ouch|incident|gibber|ploop|flibber|boo|thingThat|went|wrong|happened",
    re.IGNORECASE,
)
_EXCL_PAT = re.compile(
    r"^(date|claim.?id|claim.?num|claimant|adjuster|insured|"
    r"paid|incurred|reserve|total|cost|amount|number|id|#)$",
    re.IGNORECASE,
)


def enrich_claim_cause_of_loss(claim_data: dict, claim_id: str, selected_sheet: str) -> bool:
    """
    Attempts LLM Cause-of-Loss extraction for a single claim.
    Returns True only when it actually enriched new data (triggers a st.rerun).
    """
    if not _llm_available():
        return False
    cache_key = f"_col_enriched_{selected_sheet}_{claim_id}"
    if st.session_state.get(cache_key):
        return False

    from modules.normalization import _best_standard_name  # avoid circular at module level

    desc_keys: list = []
    for k in claim_data:
        if _DESC_PAT.search(k) and not _EXCL_PAT.match(k.strip()):
            val = str(claim_data[k].get("modified") or claim_data[k].get("value", "")).strip()
            if val and len(val) > 6 and not re.match(r"^\d{1,4}[-/]\d{1,2}[-/]\d{2,4}$", val):
                desc_keys.append(k)
        else:
            std = _best_standard_name(k)
            if std and re.search(r"description|cause|loss|narrative", std, re.IGNORECASE):
                val = str(claim_data[k].get("modified") or claim_data[k].get("value", "")).strip()
                if val and len(val) > 6 and not re.match(r"^\d{1,4}[-/]\d{1,2}[-/]\d{2,4}$", val):
                    if k not in desc_keys:
                        desc_keys.append(k)

    if not desc_keys:
        st.session_state[cache_key] = True
        return False

    texts = [
        str(claim_data[k].get("modified") or claim_data[k].get("value", "")).strip()
        for k in desc_keys
        if claim_data[k].get("modified") or claim_data[k].get("value", "")
    ]
    combined = " | ".join(t for t in texts if t and len(t) > 4)
    if not combined:
        st.session_state[cache_key] = True
        return False

    for k, info in claim_data.items():
        if re.search(r"^cause\s*of\s*loss$|^cause_of_loss$", k.strip(), re.IGNORECASE):
            existing = str(info.get("modified") or info.get("value", "")).strip()
            if existing and len(existing) > 3 and len(existing) < 60 and "." not in existing:
                st.session_state[cache_key] = True
                return False

    try:
        result  = _llm_extract_cause_of_loss(combined, sheet_name=selected_sheet)
        col_val = result.get("cause_of_loss", "")
        summary = result.get("summary", "")

        taxonomy = _pick_taxonomy(selected_sheet, combined)
        if col_val and col_val not in taxonomy:
            col_val = "Other"

        if col_val:
            # Store ONLY in session state — never touch claim_data["modified"]
            # so the Extracted column always shows the raw Excel value
            for field_key in ["Cause of Loss", "Cause Of Loss", "cause_of_loss", "Cause_of_Loss"]:
                for mk in (
                    f"mod_{selected_sheet}_{claim_id}_schema_{field_key}",
                    f"mod_{selected_sheet}_{claim_id}_{field_key}",
                ):
                    # Only set if user hasn't already edited it manually
                    if mk not in st.session_state:
                        st.session_state[mk] = col_val

        if summary:
            st.session_state[f"_col_summary_{selected_sheet}_{claim_id}"] = summary
        st.session_state[f"_col_source_fields_{selected_sheet}_{claim_id}"] = desc_keys
        st.session_state[cache_key] = True
        _append_audit({
            "event":         "LLM_CAUSE_ENRICHED",
            "timestamp":     datetime.datetime.now().isoformat(),
            "sheet":         selected_sheet,
            "claim_id":      claim_id,
            "source_fields": desc_keys,
            "input_text":    combined[:200],
            "cause_of_loss": col_val,
            "summary":       summary,
        })
        return True
    except Exception:
        st.session_state[cache_key] = True
        return False
