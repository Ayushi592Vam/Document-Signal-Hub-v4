"""
ui/pdf_analysis.py  — v9

Changes from v8:
  ─────────────────────────────────────────────────────────────────────────
  • Signal synthesis fallback:
    When the LLM returns signals=[], _synthesize_signals_from_entities()
    scans full_text + entity values for domain keywords (per doc type) and
    builds real signal cards.  A yellow banner + debug expander make it
    clear when the fallback is active.  Tab counter updates to reflect
    synthesized count too.

  • Accurate Transformation Journey traceability:
    Step 2 ("AI Extraction") now shows the ACTUAL extraction source for
    each field:
      - LLM (Call A — entities+signals)
      - LLM fallback (type_specific, Call B)
      - Azure DI matched  (field name + confidence)
      - PyMuPDF text search (value-based bbox)
      - User added manually
    Each step shows the real label, not the generic "Direct (AI Extraction)".
  ─────────────────────────────────────────────────────────────────────────

Architecture (unchanged from v8):
  • LLM (pdf_intelligence) extracts ONLY relevant fields per doc type
  • For every LLM-extracted entity, Azure DI sheet_cache is searched
    for a bounding polygon + Azure DI confidence score via name matching
  • The 👁 button shows: zoomed PDF crop + highlight + confidence pill overlay

Tabs (6):
  1. 🔍 Entities (N)           — LLM fields + Azure DI bbox + conf
  2. 📝 Summary                — Classification badge + LLM summary + edit annotations
  3. ⚡ Signals (N)            — Grouped by taxonomy: Highly Severe / High / Moderate / Low
  4. 📄 Raw JSON               — All pages KV JSON (reflects edits), download
  5. 🔄 Transformation Journey — Step-by-step pipeline trace + audit log
  6. ✅ Validation              — Deep AI validation with per-dimension scores

Theme: Light (white background, dark text throughout)
Model names are never surfaced in the UI.
"""

from __future__ import annotations

import datetime
import json
import os
import re

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# DOC-CONFIG IMPORT  — graceful degradation if not yet installed
# ─────────────────────────────────────────────────────────────────────────────

try:
    from modules.doc_config import (     # type: ignore[import]
        get_doc_type_meta  as _cfg_doc_type_meta,
        load_config        as _cfg_load,
    )
    _DOC_CONFIG_AVAILABLE = True
except ImportError:
    _DOC_CONFIG_AVAILABLE = False
    def _cfg_doc_type_meta(doc_type: str) -> dict:  # type: ignore[misc]
        return {}
    def _cfg_load(doc_type: str) -> dict:           # type: ignore[misc]
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

_DOC_TYPE_META_FALLBACK: dict[str, dict] = {
    "FNOL":     {"icon": "🚨", "color": "#dc2626", "bg": "rgba(220,38,38,0.06)"},
    "Legal":    {"icon": "⚖️",  "color": "#7c3aed", "bg": "rgba(124,58,237,0.06)"},
    "Loss Run": {"icon": "📊", "color": "#059669", "bg": "rgba(5,150,105,0.06)"},
    "Medical":  {"icon": "🏥", "color": "#2563eb", "bg": "rgba(37,99,235,0.06)"},
}

_SIGNAL_META_FALLBACK: dict[str, dict] = {
    "severity":           {"icon": "🔴", "label": "Severity",           "color": "#dc2626"},
    "legal_escalation":   {"icon": "⚖️",  "label": "Legal Escalation",   "color": "#7c3aed"},
    "fraud_indicator":    {"icon": "🚩", "label": "Fraud Indicator",    "color": "#d97706"},
    "medical_complexity": {"icon": "🏥", "label": "Medical Complexity", "color": "#2563eb"},
    "coverage_issue":     {"icon": "📋", "label": "Coverage Issue",     "color": "#b45309"},
}

_TAXONOMY = {
    "Highly Severe": {"color": "#dc2626", "bg": "rgba(220,38,38,0.06)",  "icon": "🔥"},
    "High":          {"color": "#ea580c", "bg": "rgba(234,88,12,0.06)",  "icon": "🔴"},
    "Moderate":      {"color": "#ca8a04", "bg": "rgba(202,138,4,0.06)",  "icon": "🟡"},
    "Low":           {"color": "#16a34a", "bg": "rgba(22,163,74,0.06)",  "icon": "🟢"},
}

# ── Light-theme colour tokens ─────────────────────────────────────────────────
_BG      = "#ffffff"
_BG2     = "#f8f9fa"
_BG3     = "#f1f3f5"
_BORDER  = "#e2e8f0"
_BORDER2 = "#cbd5e1"
_TXT     = "#0f172a"
_TXT2    = "#1e293b"
_LBL     = "#64748b"
_LBL2    = "#94a3b8"

_UPLOADER_PLUS_CSS = """
<style>
[data-testid="stFileUploaderDropzone"] > div > button:last-of-type,
[data-testid="stFileUploaderDropzone"] button[title="Add files"] {
    display: none !important;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL KEYWORD SYNTHESIS — fallback when LLM returns signals=[]
# ─────────────────────────────────────────────────────────────────────────────

_SIGNAL_KEYWORDS: dict[str, list[tuple[str, str, str, str]]] = {
    "Legal": [
        ("legal_escalation", "High",          "litigation",   "Document references active litigation or legal proceedings."),
        ("legal_escalation", "High",          "lawsuit",      "Lawsuit referenced in document."),
        ("legal_escalation", "Highly Severe", "criminal",     "Criminal charges or proceedings referenced."),
        ("legal_escalation", "High",          "court",        "Court involvement indicated in document."),
        ("legal_escalation", "Moderate",      "attorney",     "Attorney or legal representation mentioned."),
        ("legal_escalation", "Moderate",      "complaint",    "Formal complaint has been filed."),
        ("legal_escalation", "High",          "damages",      "Claim for damages identified."),
        ("legal_escalation", "High",          "negligence",   "Allegation of negligence present."),
        ("legal_escalation", "Highly Severe", "fraud",        "Fraud allegation detected."),
        ("legal_escalation", "Moderate",      "settlement",   "Settlement discussion referenced."),
        ("legal_escalation", "High",          "liability",    "Liability language detected in document."),
        ("legal_escalation", "Moderate",      "deposition",   "Deposition activity referenced."),
        ("coverage_issue",   "Moderate",      "exclusion",    "Policy exclusion referenced."),
        ("coverage_issue",   "High",          "denied",       "Coverage denial language detected."),
        ("coverage_issue",   "High",          "reservation",  "Reservation of rights language detected."),
    ],
    "FNOL": [
        ("severity",           "High",          "fatality",       "Fatality or death indicated in report."),
        ("severity",           "High",          "hospitalized",   "Hospitalization reported."),
        ("severity",           "Highly Severe", "total loss",     "Total loss of vehicle or property indicated."),
        ("fraud_indicator",    "High",          "inconsistent",   "Inconsistency in reported details detected."),
        ("legal_escalation",   "High",          "attorney",       "Attorney representation noted at FNOL stage."),
        ("medical_complexity", "Moderate",      "surgery",        "Surgical procedure mentioned."),
        ("medical_complexity", "High",          "permanent",      "Permanent injury or disability indicated."),
    ],
    "Medical": [
        ("medical_complexity", "High",          "surgery",        "Surgical procedure documented."),
        ("medical_complexity", "Highly Severe", "permanent",      "Permanent disability or injury noted."),
        ("medical_complexity", "High",          "chronic",        "Chronic condition identified."),
        ("medical_complexity", "Moderate",      "specialist",     "Specialist referral indicated."),
        ("fraud_indicator",    "High",          "inconsistent",   "Medical record inconsistency detected."),
    ],
    "Loss Run": [
        ("severity",       "High",     "open",      "Open claims identified in loss run."),
        ("fraud_indicator","Moderate", "frequency", "High claim frequency may indicate systemic issue."),
        ("coverage_issue", "Moderate", "reserve",   "Large reserve amounts noted."),
    ],
}

_SIGNAL_KEYWORDS_GENERIC: list[tuple[str, str, str, str]] = [
    ("fraud_indicator",  "High",          "fraud",        "Fraud keyword detected in document."),
    ("fraud_indicator",  "High",          "misrepresent", "Misrepresentation language detected."),
    ("fraud_indicator",  "High",          "false claim",  "False claim language detected."),
    ("legal_escalation", "Highly Severe", "criminal",     "Criminal reference detected."),
    ("severity",         "High",          "death",        "Reference to death in document."),
    ("severity",         "High",          "deceased",     "Deceased party mentioned."),
    ("severity",         "High",          "fatal",        "Fatality language detected."),
]


def _synthesize_signals_from_entities(intelligence: dict) -> list[dict]:
    """
    Fallback: scan full_text + entity values for domain keywords and build
    signals. Called only when the LLM returns an empty signals list.
    """
    doc_type  = intelligence.get("doc_type", "")
    full_text = (intelligence.get("full_text", "") or "").lower()
    entities  = intelligence.get("analysis", {}).get("entities", {})

    entity_blob = " ".join(
        str(v.get("value", "")) if isinstance(v, dict) else str(v)
        for v in entities.values()
    ).lower()
    corpus = full_text + " " + entity_blob

    keyword_rules = list(_SIGNAL_KEYWORDS.get(doc_type, [])) + _SIGNAL_KEYWORDS_GENERIC
    seen: set[str] = set()
    signals: list[dict] = []

    for sig_type, severity, keyword, description in keyword_rules:
        dedup_key = f"{sig_type}:{keyword}"
        if dedup_key in seen:
            continue
        if keyword.lower() in corpus:
            seen.add(dedup_key)
            idx     = corpus.find(keyword.lower())
            snippet = corpus[max(0, idx - 40): idx + 80].strip().replace("\n", " ")
            signals.append({
                "type":            sig_type,
                "severity_level":  severity,
                "description":     description,
                "supporting_text": snippet,
                "_synthesized":    True,   # marks this as keyword-derived, not LLM
            })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG-AWARE META HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_doc_type_meta(doc_type: str) -> dict:
    if _DOC_CONFIG_AVAILABLE:
        cfg_meta = _cfg_doc_type_meta(doc_type)
        if cfg_meta.get("icon"):
            return cfg_meta
    return _DOC_TYPE_META_FALLBACK.get(
        doc_type,
        {"icon": "📄", "color": "#64748b", "bg": "rgba(100,116,139,0.06)"},
    )


def _get_signal_meta(signal_type: str, doc_type: str = "") -> dict:
    if signal_type in _SIGNAL_META_FALLBACK:
        return _SIGNAL_META_FALLBACK[signal_type]
    label = signal_type.replace("_", " ").title()
    return {"icon": "⚠️", "label": label, "color": "#6b7280"}


# ─────────────────────────────────────────────────────────────────────────────
# STYLE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _conf_badge(conf: float) -> str:
    pct = int(conf * 100)
    c   = "#16a34a" if pct >= 80 else "#ca8a04" if pct >= 60 else "#dc2626"
    bg  = "#f0fdf4" if pct >= 80 else "#fefce8" if pct >= 60 else "#fef2f2"
    return (
        f"<span style='background:{bg};border:1px solid {c}40;border-radius:20px;"
        f"padding:1px 8px;font-size:10px;color:{c};font-weight:700;"
        f"font-family:monospace;'>{pct}%</span>"
    )


def _score_badge(score: int) -> str:
    c  = "#16a34a" if score >= 80 else "#ca8a04" if score >= 60 else "#dc2626"
    bg = "#f0fdf4" if score >= 80 else "#fefce8" if score >= 60 else "#fef2f2"
    return (
        f"<span style='background:{bg};border:1px solid {c}40;border-radius:20px;"
        f"padding:2px 10px;font-size:11px;color:{c};font-weight:700;"
        f"font-family:monospace;'>{score}/100</span>"
    )


def _verdict_badge(verdict: str) -> str:
    vmap = {
        "Pass":            ("#16a34a", "#f0fdf4"),
        "Validated":       ("#16a34a", "#f0fdf4"),
        "Credible":        ("#16a34a", "#f0fdf4"),
        "Adequate":        ("#16a34a", "#f0fdf4"),
        "Fail":            ("#dc2626", "#fef2f2"),
        "Failed":          ("#dc2626", "#fef2f2"),
        "Unsupported":     ("#dc2626", "#fef2f2"),
        "Critical Gaps":   ("#dc2626", "#fef2f2"),
        "Review":          ("#ca8a04", "#fefce8"),
        "Needs Review":    ("#ca8a04", "#fefce8"),
        "Questionable":    ("#ca8a04", "#fefce8"),
        "Gaps Identified": ("#ca8a04", "#fefce8"),
    }
    c, bg = vmap.get(verdict, ("#64748b", "#f8fafc"))
    return (
        f"<span style='background:{bg};border:1px solid {c}40;border-radius:6px;"
        f"padding:3px 12px;font-size:11px;color:{c};font-weight:700;"
        f"font-family:monospace;'>{verdict}</span>"
    )


def _subtype_badge(subtype: str) -> str:
    return (
        f"<span style='background:#f1f5f9;border:1px solid #cbd5e1;"
        f"border-radius:20px;padding:2px 10px;font-size:10px;"
        f"color:#475569;font-family:monospace;font-weight:600;"
        f"white-space:nowrap;'>sub-type: {subtype}</span>"
    )


def _section_header(title: str, subtitle: str = "") -> str:
    sub = (
        f"<span style='font-size:10px;color:{_LBL};font-family:monospace;'>{subtitle}</span>"
        if subtitle else ""
    )
    return (
        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:14px;'>"
        f"<div style='font-size:11px;font-weight:700;color:{_TXT2};font-family:monospace;"
        f"text-transform:uppercase;letter-spacing:1.5px;white-space:nowrap;'>{title}</div>"
        f"{sub}"
        f"<div style='flex:1;height:1px;background:linear-gradient(90deg,{_BORDER},{_BG});'>"
        f"</div></div>"
    )


def _card(content: str, border_color: str = _BORDER, bg: str = _BG) -> str:
    return (
        f"<div style='background:{bg};border:1px solid {border_color};"
        f"border-radius:8px;padding:14px 16px;margin-bottom:10px;'>{content}</div>"
    )


def _source_snippet(source_text: str) -> str:
    if not source_text:
        return ""
    return (
        f"<div style='font-size:10px;color:{_LBL};font-family:monospace;"
        f"background:{_BG2};border-left:2px solid {_BORDER2};padding:4px 8px;"
        f"margin-top:5px;border-radius:0 4px 4px 0;font-style:italic;'>"
        f"📄 {source_text}</div>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# KEY NORMALISATION
# ─────────────────────────────────────────────────────────────────────────────

def _nk(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip()
    s = re.sub(r'\([^)]*\)', '', s)
    s = s.rstrip(':').strip()
    return re.sub(r"[\s\-_:./]+", "_", s.lower()).strip("_")


def _match_score(a: str, b: str) -> float:
    if a == b:
        return 1.0
    shorter = min(len(a), len(b))
    longer  = max(len(a), len(b))
    if longer == 0:
        return 0.0
    if (a in b or b in a) and shorter / longer >= 0.60:
        return shorter / longer
    a_words = set(a.split("_"))
    b_words = set(b.split("_"))
    _STOP = {"a", "of", "to", "in", "on", "by", "at", "id", "no",
             "the", "and", "or"}
    a_sig = a_words - _STOP - {w for w in a_words if len(w) <= 1}
    b_sig = b_words - _STOP - {w for w in b_words if len(w) <= 1}
    if not a_sig or not b_sig:
        return 0.0
    inter   = len(a_sig & b_sig)
    union   = len(a_sig | b_sig)
    jaccard = inter / union if union else 0.0
    shorter_sig = a_sig if len(a_sig) <= len(b_sig) else b_sig
    if shorter_sig and shorter_sig <= (a_sig & b_sig):
        return 0.60
    return jaccard if inter >= 1 and jaccard >= 0.40 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# AZURE DI LOOKUP TABLE
# ─────────────────────────────────────────────────────────────────────────────

def _build_azure_lookup() -> dict[str, list[dict]]:
    cache_key = "_adi_lookup"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    lookup: dict[str, list[dict]] = {}

    intel = st.session_state.get("_pdf_intelligence", {})
    for az_name, az_info in intel.get("azure_di_index", {}).items():
        if not isinstance(az_info, dict):
            continue
        norm = _nk(az_name)
        lookup.setdefault(norm, []).append(az_info)

    for _, sheet_data in st.session_state.get("sheet_cache", {}).items():
        for page_dict in sheet_data.get("data", []):
            if not isinstance(page_dict, dict):
                continue
            for az_name, az_info in page_dict.items():
                if not isinstance(az_info, dict):
                    continue
                norm = _nk(az_name)
                existing_pages = {e.get("source_page") for e in lookup.get(norm, [])}
                new_page = az_info.get("source_page", 1)
                if new_page not in existing_pages:
                    lookup.setdefault(norm, []).append(az_info)

    if lookup:
        st.session_state[cache_key] = lookup
    return lookup


def _find_azure_match(
    entity_name: str,
    lookup: dict[str, list[dict]],
    hint_page: int | None = None,
) -> dict | None:
    en = _nk(entity_name)
    best_entries: list[dict] = []
    best_score: float = 0.0

    for az_norm, entries in lookup.items():
        score = _match_score(en, az_norm)
        if score > best_score:
            best_score   = score
            best_entries = entries
        elif score == best_score and score > 0:
            best_entries = best_entries + entries

    en_word_count = len([w for w in en.split("_") if w])
    threshold = 0.50 if en_word_count <= 2 else 0.60
    if best_score < threshold or not best_entries:
        return None

    if len(best_entries) == 1:
        return best_entries[0]

    if hint_page is not None:
        for entry in best_entries:
            if entry.get("source_page") == hint_page:
                return entry

    return max(best_entries, key=lambda e: float(e.get("confidence", 0.0)))


def _try_pymupdf_bbox_for_entity(field_info: dict, page_num: int) -> None:
    try:
        import fitz
        pdf_path = None
        tmpdir = st.session_state.get("tmpdir", "")
        if tmpdir:
            for ext in (".pdf", ".PDF"):
                c = os.path.join(tmpdir, f"input{ext}")
                if os.path.exists(c):
                    pdf_path = c
                    break
        if not pdf_path:
            return

        val_text = (field_info.get("value") or "").strip()
        if not val_text:
            return
        search_text = " ".join(val_text.split()[:4]) if len(val_text) > 60 else val_text
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            doc.close()
            return
        page      = doc[page_num - 1]
        pw        = page.rect.width
        ph        = page.rect.height
        page_w_in = field_info.get("page_width",  8.5)
        page_h_in = field_info.get("page_height", 11.0)

        rects = (
            page.search_for(search_text)
            or page.search_for(search_text.upper())
            or page.search_for(" ".join(val_text.split()[:4]))
        )
        if rects:
            r      = rects[0]
            inv_sx = page_w_in / pw if pw else 1.0
            inv_sy = page_h_in / ph if ph else 1.0
            field_info["bounding_polygon"] = [
                (r.x0 * inv_sx, r.y0 * inv_sy),
                (r.x1 * inv_sx, r.y0 * inv_sy),
                (r.x1 * inv_sx, r.y1 * inv_sy),
                (r.x0 * inv_sx, r.y1 * inv_sy),
            ]
            field_info["page_width"]  = page_w_in
            field_info["page_height"] = page_h_in
            field_info["_pymupdf_bbox"] = True   # ← traceability flag
        doc.close()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# CONFIDENCE LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

def _lookup_confidence(field_name: str, field_info: dict) -> float:
    direct = field_info.get("confidence")
    if direct is not None and float(direct) > 0:
        return float(direct)
    if field_info.get("bounding_polygon"):
        return 0.85
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# LLM ENTITIES ENRICHED WITH AZURE DI
# ─────────────────────────────────────────────────────────────────────────────

def _get_intelligence_entities(selected_sheet: str) -> list[tuple[str, dict]]:
    intel    = st.session_state.get("_pdf_intelligence", {})
    analysis = intel.get("analysis", {})
    entities = analysis.get("entities", {})

    # Track whether entities came from LLM Call A or fallback Call B
    _from_call_b = False
    if not entities:
        ts = analysis.get("type_specific", {})
        if ts:
            entities = ts
            _from_call_b = True
        else:
            return []

    az_lookup = _build_azure_lookup()
    eds       = _edits()
    out: list[tuple[str, dict]] = []

    for entity_name, entity_data in entities.items():
        if not isinstance(entity_data, dict):
            continue

        llm_value = entity_data.get("value", "")
        llm_conf  = float(entity_data.get("confidence", 0.0))

        field_info: dict = {
            "value":              llm_value,
            "modified":           eds.get(entity_name, llm_value),
            "confidence":         llm_conf,
            "source_text":        entity_data.get("source_text", ""),
            "source_page":        1,
            "page_width":         8.5,
            "page_height":        11.0,
            "bounding_polygon":   None,
            "_adi_confidence":    0.0,
            "_from_intelligence": True,
            "_from_call_b":       _from_call_b,   # ← traceability
            "_adi_matched":       False,           # ← traceability
            "_adi_matched_key":   None,            # ← traceability
            "_pymupdf_bbox":      False,           # ← traceability
        }

        adi_key_hint = entity_data.get("azure_di_key")

        az_match = _find_azure_match(entity_name, az_lookup)

        if az_match:
            adi_conf = float(az_match.get("confidence", 0.0))
            field_info["bounding_polygon"] = az_match.get("bounding_polygon")
            field_info["source_page"]  = az_match.get("source_page", 1)
            field_info["page_width"]   = az_match.get("page_width",  8.5)
            field_info["page_height"]  = az_match.get("page_height", 11.0)
            field_info["_adi_matched"] = True
            field_info["_adi_matched_key"] = az_match.get("_field_name", entity_name)

            if adi_conf > 0:
                field_info["confidence"]      = adi_conf
                field_info["_adi_confidence"] = adi_conf

            if not llm_value and az_match.get("value"):
                az_val = az_match["value"]
                field_info["value"]    = az_val
                field_info["modified"] = eds.get(entity_name, az_val)

        if adi_key_hint and field_info["bounding_polygon"] is None:
            adi_norm = _nk(adi_key_hint)
            entries  = az_lookup.get(adi_norm, [])
            if entries:
                best = max(entries, key=lambda e: float(e.get("confidence", 0.0)))
                if best.get("bounding_polygon"):
                    field_info["bounding_polygon"] = best["bounding_polygon"]
                    field_info["source_page"]  = best.get("source_page", field_info["source_page"])
                    field_info["page_width"]   = best.get("page_width",  field_info["page_width"])
                    field_info["page_height"]  = best.get("page_height", field_info["page_height"])
                    field_info["_adi_matched"] = True
                    field_info["_adi_matched_key"] = adi_key_hint
                    if float(best.get("confidence", 0.0)) > 0:
                        field_info["confidence"]      = float(best["confidence"])
                        field_info["_adi_confidence"] = float(best["confidence"])

        if field_info["bounding_polygon"] is None and llm_value and len(llm_value) > 6:
            snippet = " ".join(llm_value.split()[:6]).lower()
            for entries in az_lookup.values():
                for entry in entries:
                    az_val = str(entry.get("value", "")).lower()
                    if snippet in az_val and entry.get("bounding_polygon"):
                        field_info["bounding_polygon"] = entry["bounding_polygon"]
                        field_info["source_page"]  = entry.get("source_page", field_info["source_page"])
                        field_info["page_width"]   = entry.get("page_width",  field_info["page_width"])
                        field_info["page_height"]  = entry.get("page_height", field_info["page_height"])
                        field_info["_adi_matched"] = True
                        if float(entry.get("confidence", 0.0)) > 0:
                            field_info["confidence"]      = float(entry["confidence"])
                            field_info["_adi_confidence"] = float(entry["confidence"])
                        break
                if field_info["bounding_polygon"]:
                    break

        if field_info["bounding_polygon"] is None and field_info.get("value"):
            _try_pymupdf_bbox_for_entity(field_info, field_info["source_page"])

        out.append((entity_name, field_info))

    return out


# ─────────────────────────────────────────────────────────────────────────────
# TRACEABILITY HELPER — returns human-readable extraction source for journey tab
# ─────────────────────────────────────────────────────────────────────────────

def _extraction_source_label(field_info: dict) -> tuple[str, str, str]:
    """
    Returns (icon, label, detail) describing how this field was actually extracted.

    Priority:
      1. User-added manually
      2. LLM Call A (entities+signals) with Azure DI bbox confirmation
      3. LLM Call A (entities+signals), no Azure DI bbox
      4. LLM Call B fallback (type_specific / summary call)
      5. Azure DI key-value extraction only (no LLM value)
      6. PyMuPDF text search bbox
    """
    is_user_added  = field_info.get("_user_added", False)
    from_call_b    = field_info.get("_from_call_b", False)
    adi_matched    = field_info.get("_adi_matched", False)
    adi_conf       = field_info.get("_adi_confidence", 0.0)
    adi_key        = field_info.get("_adi_matched_key") or ""
    pymupdf        = field_info.get("_pymupdf_bbox", False)
    from_intel     = field_info.get("_from_intelligence", False)
    llm_value      = field_info.get("value", "")
    source_page    = field_info.get("source_page", 1)
    conf_pct       = int(float(field_info.get("confidence", 0.0)) * 100)

    if is_user_added:
        return ("✏️", "Manually Added by User",
                "This field was injected manually via the Add New Field form.")

    if from_intel and not from_call_b:
        if adi_matched and adi_conf > 0:
            return (
                "🤖+📄",
                "LLM (Call A) · Confirmed by Azure DI",
                f"Value extracted by LLM (entities+signals pass, Call A). "
                f"Bounding box and confidence ({conf_pct}%) sourced from Azure Document Intelligence "
                f"field match: '{adi_key}', page {source_page}.",
            )
        elif adi_matched:
            return (
                "🤖+📄",
                "LLM (Call A) · Azure DI bbox located",
                f"Value extracted by LLM (Call A). Bounding polygon located via Azure DI "
                f"field name match ('{adi_key}', page {source_page}), no ADI confidence score.",
            )
        elif pymupdf:
            return (
                "🤖+🔍",
                "LLM (Call A) · PyMuPDF text search bbox",
                f"Value extracted by LLM (Call A). No Azure DI match found — "
                f"bounding box located by searching PDF text layer for value '{llm_value[:40]}' "
                f"on page {source_page} using PyMuPDF.",
            )
        else:
            return (
                "🤖",
                "LLM (Call A) — no bounding box",
                "Value extracted by LLM during the entities+signals pass (Call A). "
                "No matching Azure DI field or PyMuPDF text region was found, "
                "so no bounding polygon is available for document highlighting.",
            )

    if from_intel and from_call_b:
        return (
            "🤖²",
            "LLM (Call B fallback) — type-specific field",
            "Entities from Call A were empty or unavailable. This value was extracted "
            "during the summary+type_specific pass (Call B) as a fallback. "
            "Field lists may be less precise than Call A extractions.",
        )

    # Raw Azure DI field (not LLM-sourced)
    if adi_matched:
        return (
            "📄",
            "Azure Document Intelligence only",
            f"This field was not extracted by the LLM. Value comes directly from "
            f"Azure DI key-value extraction (field '{adi_key}', page {source_page}, "
            f"confidence {conf_pct}%).",
        )

    return (
        "📋",
        "Azure DI raw field (sheet cache)",
        f"Field sourced from raw Azure DI sheet cache. Page {source_page}.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# SESSION-STATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_raw_fields(selected_sheet: str) -> list[tuple[str, dict]]:
    data = (
        st.session_state
        .get("sheet_cache", {})
        .get(selected_sheet, {})
        .get("data", [])
    )
    seen: set  = set()
    out:  list = []
    for page_dict in data:
        if isinstance(page_dict, dict):
            for fname, finfo in page_dict.items():
                if fname not in seen:
                    seen.add(fname)
                    out.append((fname, finfo))
    return out


def _get_all_pages_fields() -> dict[str, dict[str, str]]:
    eds          = _edits()
    cache        = st.session_state.get("sheet_cache", {})
    sheet_names  = st.session_state.get("sheet_names", list(cache.keys()))
    sheet_hashes = st.session_state.get("sheet_hashes", {})
    all_pages: dict[str, dict[str, str]] = {}

    def _extract_kv(data: list) -> dict[str, str]:
        kv: dict[str, str] = {}
        seen: set = set()
        for page_dict in data:
            if isinstance(page_dict, dict):
                for fname, finfo in page_dict.items():
                    if fname not in seen:
                        seen.add(fname)
                        kv[fname] = eds.get(
                            fname,
                            (finfo.get("modified", finfo.get("value", ""))
                             if isinstance(finfo, dict) else str(finfo))
                        )
        return kv

    for sname in sheet_names:
        if sname in cache:
            kv = _extract_kv(cache[sname].get("data", []))
            if kv:
                all_pages[sname] = kv
            continue
        sh_hash = sheet_hashes.get(sname, "")
        if not sh_hash:
            continue
        try:
            from modules.storage import _load_from_feature_store  # type: ignore[import]
            fs = _load_from_feature_store(sh_hash)
            if not fs:
                continue
            kv = {}
            for _cid, rec in fs.get("records", {}).items():
                for fld, fd in rec.items():
                    if fld not in kv and isinstance(fd, dict) and "value" in fd:
                        kv[fld] = eds.get(fld, fd.get("modified", fd.get("value", "")))
            if kv:
                all_pages[sname] = kv
        except Exception:
            pass

    return all_pages


def _edits() -> dict:
    if "_pdf_edits" not in st.session_state:
        st.session_state["_pdf_edits"] = {}
    return st.session_state["_pdf_edits"]


def _edit_history() -> dict:
    if "_pdf_edit_hist" not in st.session_state:
        st.session_state["_pdf_edit_hist"] = {}
    return st.session_state["_pdf_edit_hist"]


def _sync_edit(field_name: str, new_value: str, selected_sheet: str) -> None:
    eds  = _edits()
    hist = _edit_history()
    old  = eds.get(field_name)

    data = (
        st.session_state.get("sheet_cache", {})
        .get(selected_sheet, {})
        .get("data", [])
    )
    for page_dict in data:
        if isinstance(page_dict, dict) and field_name in page_dict:
            if old is None:
                old = page_dict[field_name].get("modified", page_dict[field_name].get("value", ""))
            page_dict[field_name]["modified"] = new_value
            break

    intel    = st.session_state.get("_pdf_intelligence", {})
    entities = intel.get("analysis", {}).get("entities", {})
    if field_name in entities and isinstance(entities[field_name], dict):
        if old is None:
            old = entities[field_name].get("value", "")

    eds[field_name] = new_value

    if field_name not in hist:
        hist[field_name] = []
    if not hist[field_name] or hist[field_name][-1]["to"] != new_value:
        hist[field_name].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "from":      old or "",
            "to":        new_value,
        })

    st.session_state.pop("_adi_lookup", None)


# ─────────────────────────────────────────────────────────────────────────────
# BOUNDING BOX POPUP
# ─────────────────────────────────────────────────────────────────────────────

def _render_bbox_content(field_name: str, field_info: dict, pdf_path: str) -> None:
    bounding_polygon = field_info.get("bounding_polygon")
    source_page      = int(field_info.get("source_page", 1))
    page_width       = float(field_info.get("page_width",  8.5))
    page_height      = float(field_info.get("page_height", 11.0))
    extracted_value  = field_info.get("value", "")
    confidence       = _lookup_confidence(field_name, field_info)
    conf_pct         = int(confidence * 100)
    conf_hex         = "#16a34a" if conf_pct >= 80 else "#ca8a04" if conf_pct >= 60 else "#dc2626"
    conf_bg          = "#f0fdf4" if conf_pct >= 80 else "#fefce8" if conf_pct >= 60 else "#fef2f2"
    conf_rgb         = (
        (0.09, 0.64, 0.26) if conf_pct >= 80 else
        (0.79, 0.54, 0.02) if conf_pct >= 60 else
        (0.86, 0.15, 0.15)
    )

    st.markdown(
        f"<div style='background:{_BG};border:1px solid {_BORDER};"
        f"border-radius:8px;padding:14px 16px;margin-bottom:14px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div>"
        f"<div style='font-size:9px;color:{_LBL};font-family:monospace;"
        f"text-transform:uppercase;letter-spacing:1px;'>LLM-Extracted Field</div>"
        f"<div style='font-size:16px;font-weight:700;color:#7c3aed;"
        f"font-family:monospace;margin-top:2px;'>{field_name}</div>"
        f"</div>"
        f"<div style='text-align:right;'>"
        f"<div style='font-size:9px;color:{_LBL};font-family:monospace;"
        f"text-transform:uppercase;letter-spacing:1px;'>Extraction Confidence</div>"
        f"<div style='font-size:28px;font-weight:800;color:{conf_hex};"
        f"font-family:monospace;margin-top:2px;'>"
        f"{'N/A' if conf_pct == 0 else f'{conf_pct}%'}</div>"
        f"</div></div>"
        f"<div style='height:1px;background:{_BORDER};margin:10px 0;'></div>"
        f"<div style='font-size:9px;color:{_LBL};font-family:monospace;"
        f"text-transform:uppercase;letter-spacing:1px;'>Extracted Value</div>"
        f"<div style='font-size:13px;color:{_TXT};font-family:monospace;"
        f"background:{_BG2};padding:7px 10px;border-radius:4px;margin-top:4px;"
        f"word-break:break-word;border:1px solid {_BORDER};'>"
        f"{extracted_value or '—'}</div>"
        f"<div style='margin-top:8px;font-size:10px;color:{_LBL};font-family:monospace;'>"
        f"Source: Page {source_page} &nbsp;·&nbsp; "
        f"Bounding box: {'✓ available' if bounding_polygon else '✗ not available'}"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    if not bounding_polygon:
        st.warning(
            "⚠ No bounding-box coordinates for this field.\n\n"
            "Azure DI did not return a precise region for this key-value pair. "
            "This typically means the field was extracted from text layout rather "
            "than a structured key-value block."
        )
        return

    if not pdf_path or not os.path.exists(pdf_path):
        st.error("❌ PDF file not accessible for rendering.")
        return

    try:
        import fitz

        doc         = fitz.open(pdf_path)
        total_pages = len(doc)

        if source_page < 1 or source_page > total_pages:
            st.error(f"Page {source_page} out of range ({total_pages} total).")
            doc.close()
            return

        page   = doc[source_page - 1]
        pw_pts = page.rect.width
        ph_pts = page.rect.height

        sx  = pw_pts / page_width
        sy  = ph_pts / page_height
        pts = [(x * sx, y * sy) for x, y in bounding_polygon]
        xs  = [p[0] for p in pts]
        ys  = [p[1] for p in pts]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        bbox = fitz.Rect(x0, y0, x1, y1)

        shape = page.new_shape()
        shape.draw_rect(bbox)
        shape.finish(
            color=conf_rgb,
            fill=(*conf_rgb, 0.22),
            fill_opacity=0.28,
            width=2.5,
        )
        shape.commit()

        if conf_pct > 0:
            label  = f"  {conf_pct}% confidence  "
            char_w = 5.6
            pill_w = len(label) * char_w
            ly     = max(y0 - 14, 10)
            lrect  = fitz.Rect(x0, ly - 13, x0 + pill_w, ly + 2)

            pill = page.new_shape()
            pill.draw_rect(lrect)
            pill.finish(color=conf_rgb, fill=conf_rgb, fill_opacity=0.93, width=0)
            pill.commit()

            page.insert_text(
                fitz.Point(x0 + 3, ly - 1),
                f"{conf_pct}% confidence",
                fontsize=8,
                color=(1.0, 1.0, 1.0),
            )

        PAD  = 60
        crop = fitz.Rect(
            max(0,      x0 - PAD),
            max(0,      y0 - PAD - 22),
            min(pw_pts, x1 + PAD),
            min(ph_pts, y1 + PAD),
        )
        pix_zoom = page.get_pixmap(matrix=fitz.Matrix(2.8, 2.8), clip=crop)

        st.markdown(
            f"<div style='font-size:11px;font-weight:700;color:{_TXT2};"
            f"font-family:monospace;text-transform:uppercase;letter-spacing:1.5px;"
            f"margin-bottom:8px;'>🔍 Zoomed View</div>",
            unsafe_allow_html=True,
        )
        st.image(pix_zoom.tobytes("png"), use_container_width=True)

        with st.expander("📄 Full Page View"):
            pix_full = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            st.image(pix_full.tobytes("png"), use_container_width=True)

        doc.close()

    except ImportError:
        st.error("**PyMuPDF required.** Install: `pip install pymupdf`")
    except Exception as exc:
        st.error(f"Could not render PDF page: {exc}")


_HAS_DIALOG = hasattr(st, "dialog")

if _HAS_DIALOG:
    @st.dialog("📍 Field Location in Document", width="large")
    def _bbox_popup(field_name: str, field_info: dict, pdf_path: str) -> None:
        _render_bbox_content(field_name, field_info, pdf_path)
else:
    def _bbox_popup(field_name: str, field_info: dict, pdf_path: str) -> None:  # type: ignore[misc]
        with st.expander(f"📍 {field_name}", expanded=True):
            _render_bbox_content(field_name, field_info, pdf_path)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — ENTITIES
# ─────────────────────────────────────────────────────────────────────────────

def _render_entities_tab(
    intelligence: dict,
    selected_sheet: str,
    pdf_path: str | None,
) -> None:
    intel_fields = _get_intelligence_entities(selected_sheet)
    eds          = _edits()

    if not intel_fields:
        intel    = st.session_state.get("_pdf_intelligence", {})
        analysis = intel.get("analysis", {})

        has_intel = bool(intel)
        has_summ  = bool(analysis.get("summary", "").strip())
        has_ents  = bool(analysis.get("entities"))
        has_ts    = bool(analysis.get("type_specific"))
        has_sigs  = bool(analysis.get("signals"))
        doc_type  = intel.get("doc_type", "")

        def _pill(label: str, ok: bool) -> str:
            c  = "#16a34a" if ok else "#dc2626"
            bg = "#f0fdf4" if ok else "#fef2f2"
            return (
                f"<span style='background:{bg};border:1px solid {c}40;"
                f"border-radius:20px;padding:3px 10px;font-size:10px;"
                f"color:{c};font-family:monospace;'>"
                f"{'✓' if ok else '✗'} {label}</span>"
            )

        st.markdown(
            f"<div style='background:{_BG};border:1px solid #fde68a;"
            f"border-left:4px solid #ca8a04;border-radius:8px;"
            f"padding:14px 16px;margin-bottom:12px;'>"
            f"<div style='font-size:11px;font-weight:700;color:#b45309;"
            f"font-family:monospace;margin-bottom:10px;'>"
            f"⚠ LLM entity extraction returned 0 fields</div>"
            f"<div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;'>"
            f"{_pill('Intelligence ran', has_intel)}"
            f"{_pill('Summary', has_summ)}"
            f"{_pill('Entities', has_ents)}"
            f"{_pill('Type fields', has_ts)}"
            f"{_pill('Signals', has_sigs)}"
            f"{_pill('Doc type: ' + doc_type if doc_type else 'Doc type', bool(doc_type))}"
            f"</div>"
            f"<div style='font-size:11px;color:{_LBL};font-family:monospace;line-height:1.6;'>"
            f"<b style='color:#b45309;'>Most likely cause:</b> The LLM's JSON response "
            f"exceeded the token limit and was truncated mid-object. "
            f"Try setting <code>PDF_INTEL_DEBUG=1</code> to diagnose."
            f"</div></div>",
            unsafe_allow_html=True,
        )

        debug_data = st.session_state.get("_pdf_intel_debug", {})
        if debug_data:
            with st.expander("🔬 Debug Output"):
                for key, val in debug_data.items():
                    st.markdown(
                        f"<div style='font-size:10px;font-weight:700;color:#7c3aed;"
                        f"font-family:monospace;margin-bottom:4px;"
                        f"text-transform:uppercase;'>{key}</div>",
                        unsafe_allow_html=True,
                    )
                    st.code(val[:3000] if len(val) > 3000 else val, language="json")
        elif intel:
            st.markdown(
                f"<div style='font-size:10px;color:{_LBL};font-family:monospace;"
                f"margin-bottom:8px;'>💡 Set env var <code>PDF_INTEL_DEBUG=1</code> "
                f"and re-run to capture raw LLM responses.</div>",
                unsafe_allow_html=True,
            )

        col_btn, _ = st.columns([2, 5])
        with col_btn:
            if st.button("🔄 Re-run AI Analysis", use_container_width=True,
                         key="_rerun_intelligence_btn"):
                for key in ("_pdf_intelligence", "_pdf_intelligence_file",
                            "_adi_lookup", "_pdf_intel_debug", "_pdf_summary_override"):
                    st.session_state.pop(key, None)
                st.rerun()

        raw = _get_raw_fields(selected_sheet)
        if not raw:
            st.info("No fields extracted for this page yet.")
            return

        st.markdown(
            f"<div style='font-size:11px;color:{_LBL};font-family:monospace;"
            f"margin:8px 0 12px 0;background:{_BG2};border:1px solid {_BORDER};"
            f"border-radius:6px;padding:8px 12px;'>"
            f"📋 Falling back to raw Azure Document Intelligence fields.</div>",
            unsafe_allow_html=True,
        )
        intel_fields = raw

    bbox_count = sum(1 for _, fi in intel_fields if fi.get("bounding_polygon"))
    adi_count  = sum(
        1 for _, fi in intel_fields
        if fi.get("azure_di_key") or fi.get("_adi_confidence", 0) > 0
    )

    st.markdown(
        _section_header(
            "Extracted Entities",
            (
                f"{len(intel_fields)} field(s) · "
                f"{adi_count} matched · "
                f"{bbox_count} with bounding box"
            ),
        ),
        unsafe_allow_html=True,
    )

    _HDR = (
        f"font-size:10px;font-weight:700;font-family:monospace;"
        f"text-transform:uppercase;letter-spacing:1.5px;"
        f"padding:6px 4px;border-bottom:1px solid {_BORDER};"
    )
    h1, h2, h3, h4 = st.columns([2.5, 3.5, 3.5, 1.0])
    h1.markdown(f"<div style='{_HDR}color:{_LBL};'>Field Name</div>",
                unsafe_allow_html=True)
    h2.markdown(f"<div style='{_HDR}color:#059669;'>Extracted</div>",
                unsafe_allow_html=True)
    h3.markdown(f"<div style='{_HDR}color:#2563eb;'>Modified</div>",
                unsafe_allow_html=True)
    h4.markdown(f"<div style='{_HDR}color:{_LBL};text-align:center;'>Actions</div>",
                unsafe_allow_html=True)

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

    _EM_KEY = "_pdf_edit_mode_fields"
    if _EM_KEY not in st.session_state:
        st.session_state[_EM_KEY] = set()

    _bbox_pending_name: str | None  = None
    _bbox_pending_info: dict | None = None

    for field_name, field_info in intel_fields:
        extracted  = field_info.get("value", "")
        modified   = eds.get(field_name, field_info.get("modified", extracted))
        in_edit    = field_name in st.session_state[_EM_KEY]
        has_bbox   = bool(field_info.get("bounding_polygon"))
        is_changed = modified != extracted
        confidence = _lookup_confidence(field_name, field_info)
        conf_pct   = int(confidence * 100)

        c1, c2, c3, c4 = st.columns([2.5, 3.5, 3.5, 1.0])

        with c1:
            st.markdown(
                f"<div style='font-size:12px;font-weight:600;color:{_TXT};"
                f"font-family:monospace;padding:6px 4px 2px 4px;line-height:1.4;"
                f"word-break:break-word;'>{field_name}</div>"
                + (f"<div style='padding:0 4px 6px 4px;'>{_conf_badge(confidence)}</div>"
                   if conf_pct > 0 else ""),
                unsafe_allow_html=True,
            )

        with c2:
            st.markdown(
                f"<div style='font-size:12px;color:{_TXT};font-family:monospace;"
                f"background:{_BG2};border:1px solid {_BORDER};"
                f"padding:7px 10px;border-radius:5px;min-height:34px;"
                f"line-height:1.5;white-space:pre-wrap;word-break:break-word;'>"
                f"{extracted if extracted else f'<span style=\"color:{_LBL2};\">—</span>'}"
                f"</div>",
                unsafe_allow_html=True,
            )

        with c3:
            if in_edit:
                st.text_input(
                    "modified_value", value=modified,
                    key=f"_pmv_{field_name}", label_visibility="collapsed",
                )
            else:
                _badge = (
                    f"<span style='margin-left:6px;font-size:9px;color:#2563eb;"
                    f"border:1px solid #2563eb;border-radius:10px;padding:1px 5px;"
                    f"white-space:nowrap;background:#eff6ff;'>✏ edited</span>"
                    if is_changed else ""
                )
                _bg_css = (
                    f"color:{_TXT};background:#eff6ff;border:1px solid #bfdbfe;"
                    if is_changed else
                    f"color:{_TXT};background:{_BG2};border:1px solid {_BORDER};"
                )
                st.markdown(
                    f"<div style='font-size:12px;font-family:monospace;{_bg_css}"
                    f"padding:7px 10px;border-radius:5px;min-height:34px;"
                    f"line-height:1.5;white-space:pre-wrap;word-break:break-word;'>"
                    f"{modified if modified else f'<span style=\"color:{_LBL2};\">—</span>'}"
                    f"{_badge}</div>",
                    unsafe_allow_html=True,
                )

        with c4:
            be, beye = st.columns(2)
            with be:
                lbl = "💾" if in_edit else "✏️"
                if st.button(lbl, key=f"_pbtn_edit_{field_name}",
                             help="Save" if in_edit else "Edit",
                             use_container_width=True):
                    if in_edit:
                        saved = st.session_state.get(f"_pmv_{field_name}", modified)
                        _sync_edit(field_name, saved, selected_sheet)
                        st.session_state[_EM_KEY].discard(field_name)
                    else:
                        st.session_state[_EM_KEY].add(field_name)
                    st.rerun()

            with beye:
                if has_bbox:
                    tip = f"View in document · Confidence: {conf_pct}%"
                else:
                    tip = "No bounding box available for this field"
                if st.button("👁", key=f"_pbtn_eye_{field_name}", help=tip,
                             disabled=not has_bbox, use_container_width=True):
                    _bbox_pending_name = field_name
                    _bbox_pending_info = field_info

        st.markdown(
            f"<div style='height:1px;background:{_BORDER};margin:2px 0 4px 0;'></div>",
            unsafe_allow_html=True,
        )

    if _bbox_pending_name and _bbox_pending_info is not None:
        _bbox_popup(_bbox_pending_name, _bbox_pending_info, pdf_path or "")

    # ── Add New Field ─────────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='height:1px;background:linear-gradient(90deg,{_BORDER2},{_BG});"
        f"margin-bottom:16px;'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        _section_header("Add New Field", "manually inject a custom key-value pair"),
        unsafe_allow_html=True,
    )

    _ANF_KEY = "_pdf_add_field_open"
    if _ANF_KEY not in st.session_state:
        st.session_state[_ANF_KEY] = False

    if not st.session_state[_ANF_KEY]:
        anf_col, _ = st.columns([2, 5])
        with anf_col:
            if st.button(
                "＋  Add New Field",
                key="_anf_open_btn",
                help="Manually add a custom field and value to the extracted entities",
                use_container_width=True,
            ):
                st.session_state[_ANF_KEY] = True
                st.rerun()
    else:
        st.markdown(
            f"<div style='background:{_BG2};border:1px solid {_BORDER2};"
            f"border-left:4px solid #7c3aed;border-radius:8px;"
            f"padding:16px 18px;margin-bottom:10px;'>"
            f"<div style='font-size:10px;font-weight:700;color:#7c3aed;"
            f"font-family:monospace;text-transform:uppercase;letter-spacing:1.5px;"
            f"margin-bottom:12px;'>✏ New Field</div>",
            unsafe_allow_html=True,
        )

        nf_col1, nf_col2 = st.columns([1, 1])
        with nf_col1:
            st.markdown(
                f"<div style='font-size:10px;font-weight:700;color:{_LBL};"
                f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;"
                f"margin-bottom:4px;'>Field Name</div>",
                unsafe_allow_html=True,
            )
            new_field_name = st.text_input(
                "new_field_name_input", value="",
                placeholder="e.g. Policy Number",
                key="_anf_name", label_visibility="collapsed",
            )
        with nf_col2:
            st.markdown(
                f"<div style='font-size:10px;font-weight:700;color:{_LBL};"
                f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;"
                f"margin-bottom:4px;'>Field Value</div>",
                unsafe_allow_html=True,
            )
            new_field_value = st.text_input(
                "new_field_value_input", value="",
                placeholder="e.g. POL-2024-00123",
                key="_anf_value", label_visibility="collapsed",
            )

        st.markdown("</div>", unsafe_allow_html=True)

        btn_save, btn_cancel, _ = st.columns([1.2, 1, 4.8])
        with btn_save:
            if st.button("💾 Save Field", key="_anf_save_btn", use_container_width=True):
                fname = (new_field_name or "").strip()
                fval  = (new_field_value or "").strip()

                if not fname:
                    st.error("Field name cannot be empty.")
                elif fname in dict(intel_fields or []):
                    st.error(f'Field "{fname}" already exists. Edit it in the table above.')
                else:
                    cache      = st.session_state.get("sheet_cache", {})
                    sheet_data = cache.get(selected_sheet, {})
                    pages      = sheet_data.get("data", [])
                    new_entry  = {
                        "value":              fval,
                        "modified":           fval,
                        "confidence":         1.0,
                        "source_text":        "",
                        "source_page":        1,
                        "page_width":         8.5,
                        "page_height":        11.0,
                        "bounding_polygon":   None,
                        "_adi_confidence":    0.0,
                        "_from_intelligence": True,
                        "_user_added":        True,
                    }
                    if pages:
                        pages[0][fname] = new_entry
                    else:
                        sheet_data["data"] = [{fname: new_entry}]
                        cache[selected_sheet] = sheet_data

                    intel    = st.session_state.get("_pdf_intelligence", {})
                    entities = intel.get("analysis", {}).get("entities", {})
                    entities[fname] = {
                        "value":       fval,
                        "confidence":  1.0,
                        "source_text": "",
                    }

                    _sync_edit(fname, fval, selected_sheet)
                    st.session_state.pop("_adi_lookup", None)
                    st.session_state[_ANF_KEY] = False
                    st.session_state.pop("_anf_name",  None)
                    st.session_state.pop("_anf_value", None)
                    st.toast(f'✅ Field "{fname}" added!')
                    st.rerun()

        with btn_cancel:
            if st.button("✕ Cancel", key="_anf_cancel_btn", use_container_width=True):
                st.session_state[_ANF_KEY] = False
                st.session_state.pop("_anf_name",  None)
                st.session_state.pop("_anf_value", None)
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_intelligence_kv(selected_sheet: str) -> dict[str, str]:
    intel_fields = _get_intelligence_entities(selected_sheet)
    eds          = _edits()

    if not intel_fields:
        intel_fields = _get_raw_fields(selected_sheet)

    kv: dict[str, str] = {}
    for fname, finfo in intel_fields:
        kv[fname] = eds.get(fname, finfo.get("modified", finfo.get("value", "")))
    return kv


def _regenerate_summary(intelligence: dict, selected_sheet: str) -> str | None:
    doc_type  = intelligence.get("doc_type", "Legal")
    full_text = intelligence.get("full_text", "")

    current_kv = _get_intelligence_kv(selected_sheet)
    eds        = _edits()
    hist       = _edit_history()

    field_lines = []
    for fname, val in current_kv.items():
        orig = ""
        if fname in hist and hist[fname]:
            orig = hist[fname][0].get("from", "")
        if orig and orig != val:
            field_lines.append(f"  {fname}: {val}  [was: {orig}]")
        else:
            field_lines.append(f"  {fname}: {val}")

    fields_block = "\n".join(field_lines) if field_lines else "(no fields extracted)"

    system_prompt = (
        f"You are a senior insurance document analyst. "
        f"Generate a concise factual summary (max 200 words) of this {doc_type} insurance "
        f"document reflecting CURRENT field values. Write natural prose — no field names. "
        f"Return ONLY the summary text with no preamble."
    )
    user_prompt = (
        f"Document type: {doc_type}\n\n"
        f"CURRENT FIELD VALUES:\n{fields_block}\n\n"
        f"ORIGINAL DOCUMENT TEXT (context only):\n{full_text[:4000]}"
        + ("\n[... truncated ...]" if len(full_text) > 4000 else "")
    )

    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=os.environ.get("OPENAI_DEPLOYMENT_ENDPOINT", ""),
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            api_version=os.environ.get("OPENAI_API_VERSION", "2024-12-01-preview"),
        )
        deployment = os.environ.get("OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
        response   = client.chat.completions.create(
            model=deployment,
            max_tokens=400,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        raw = re.sub(r"^```.*?```$", "", raw, flags=re.DOTALL).strip()
        return raw if raw else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def _render_summary_tab(intelligence: dict, selected_sheet: str) -> None:
    doc_type = intelligence.get("doc_type", "Legal")
    clf      = intelligence.get("classification", {})
    meta     = _get_doc_type_meta(doc_type)
    conf     = clf.get("confidence", 0.5)

    _SUMM_KEY = "_pdf_summary_override"
    summary   = st.session_state.get(_SUMM_KEY) or intelligence.get("analysis", {}).get("summary", "")

    st.markdown(
        f"<div style='background:{meta['bg']};border:1px solid {meta['color']}30;"
        f"border-left:4px solid {meta['color']};border-radius:8px;"
        f"padding:14px 18px;margin-bottom:16px;'>"
        f"<div style='display:flex;align-items:center;gap:12px;'>"
        f"<span style='font-size:28px;'>{meta['icon']}</span>"
        f"<div>"
        f"<div style='font-size:20px;font-weight:800;color:{meta['color']};"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:2px;'>{doc_type}</div>"
        f"<div style='font-size:11px;color:{_LBL};margin-top:2px;'>"
        f"Classification confidence: {_conf_badge(conf)}</div>"
        f"</div></div></div>",
        unsafe_allow_html=True,
    )

    eds  = _edits()
    hist = _edit_history()
    changed = [(fn, h) for fn, h in hist.items() if h]
    is_regenerated = bool(st.session_state.get(_SUMM_KEY))

    btn_col, status_col = st.columns([2, 6])
    with btn_col:
        regen_label    = "🔄 Re-regenerate Summary" if is_regenerated else "🔄 Regenerate with Edits"
        regen_disabled = not changed
        if st.button(
            regen_label,
            key="_regen_summary_btn",
            help="Regenerate summary using edited field values" if not regen_disabled else "Make edits in the Entities tab first",
            disabled=regen_disabled,
            use_container_width=True,
        ):
            with st.spinner("Regenerating summary…"):
                new_summary = _regenerate_summary(intelligence, selected_sheet)
            if new_summary:
                st.session_state[_SUMM_KEY] = new_summary
                summary = new_summary
                st.toast("✅ Summary regenerated!")
                st.rerun()
            else:
                st.error("Could not regenerate summary — LLM unavailable.")

    with status_col:
        if is_regenerated:
            st.markdown(
                f"<div style='font-size:11px;color:#16a34a;font-family:monospace;"
                f"padding-top:8px;'>✓ Showing regenerated summary · based on edited values</div>",
                unsafe_allow_html=True,
            )
        elif changed:
            st.markdown(
                f"<div style='font-size:11px;color:#ca8a04;font-family:monospace;"
                f"padding-top:8px;'>⚠ {len(changed)} field(s) edited — click Regenerate to update summary</div>",
                unsafe_allow_html=True,
            )

    if st.session_state.get(_SUMM_KEY):
        if st.button("↩ Reset to original summary", key="_reset_summary_btn"):
            st.session_state.pop(_SUMM_KEY, None)
            st.rerun()

    st.markdown(_section_header("Document Summary"), unsafe_allow_html=True)

    if summary:
        annotated = summary
        if not is_regenerated:
            for fname, new_val in eds.items():
                changes = hist.get(fname, [])
                if not changes:
                    continue
                old_val = changes[0].get("from", "")
                if old_val and old_val != new_val and old_val in annotated:
                    annotated = annotated.replace(
                        old_val,
                        f"<span style='background:#eff6ff;color:#2563eb;"
                        f"border-radius:3px;padding:0 3px;font-weight:600;"
                        f"border-bottom:2px solid #2563eb;'"
                        f"title='Edited from: {old_val}'>{new_val}</span>",
                        1,
                    )

        border_color = "#16a34a" if is_regenerated else meta["color"]
        label_html   = (
            f"<div style='font-size:9px;font-weight:700;color:#16a34a;"
            f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;"
            f"margin-bottom:6px;'>✓ Regenerated — uses your edited values</div>"
            if is_regenerated else ""
        )
        st.markdown(
            f"<div style='background:{_BG2};border:1px solid {border_color}30;"
            f"border-radius:8px;padding:16px 20px;font-size:13px;color:{_TXT};"
            f"line-height:1.9;'>{label_html}{annotated}</div>",
            unsafe_allow_html=True,
        )

        if changed and not is_regenerated:
            rows_html = ""
            for fname, fchanges in changed:
                old_v = fchanges[0].get("from", "—")
                new_v = eds.get(fname, fchanges[-1].get("to", "—"))
                rows_html += (
                    f"<div style='display:grid;grid-template-columns:180px 1fr auto 1fr;"
                    f"gap:8px;padding:6px 0;border-bottom:1px solid {_BORDER};align-items:center;'>"
                    f"<span style='font-size:11px;font-weight:600;color:{_TXT};"
                    f"font-family:monospace;'>{fname}</span>"
                    f"<span style='font-size:11px;color:{_LBL};font-family:monospace;"
                    f"text-decoration:line-through;word-break:break-word;'>{old_v}</span>"
                    f"<span style='font-size:13px;color:{_LBL};'>→</span>"
                    f"<span style='font-size:11px;color:#2563eb;font-family:monospace;"
                    f"font-weight:600;word-break:break-word;'>{new_v}</span>"
                    f"</div>"
                )
            st.markdown(
                f"<div style='background:#fffbeb;border:1px solid #fde68a;"
                f"border-radius:8px;padding:12px 16px;margin-top:12px;'>"
                f"<div style='font-size:10px;font-weight:700;color:#b45309;"
                f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;"
                f"margin-bottom:6px;'>⚠ {len(changed)} Pending Edit(s)</div>"
                f"<div style='font-size:9px;color:{_LBL};font-family:monospace;"
                f"margin-bottom:8px;'>These edits are not yet in the summary. "
                f"Click \"Regenerate with Edits\" to update it.</div>"
                f"{rows_html}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No summary generated.")

    full_text  = intelligence.get("full_text", "")
    page_count = intelligence.get("page_count", 0)
    subtype    = intelligence.get("analysis", {}).get("detected_subtype") or ""
    st.markdown(
        f"<div style='display:flex;gap:14px;margin-top:14px;flex-wrap:wrap;'>"
        + "".join(
            f"<div style='background:{_BG2};border:1px solid {_BORDER};"
            f"border-radius:6px;padding:8px 14px;'>"
            f"<div style='font-size:9px;color:{_LBL};font-family:monospace;"
            f"text-transform:uppercase;letter-spacing:1px;'>{lbl}</div>"
            f"<div style='font-size:14px;font-weight:700;color:#2563eb;"
            f"font-family:monospace;margin-top:2px;'>{val}</div></div>"
            for lbl, val in [
                ("Pages",      page_count),
                ("Words",      len(full_text.split())),
                ("Characters", len(full_text)),
                ("Doc Type",   doc_type),
            ] + ([("Sub-type", subtype)] if subtype else [])
        )
        + "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — SIGNALS
# ─────────────────────────────────────────────────────────────────────────────

def _classify_severity(sig: dict, doc_type: str = "") -> str:
    llm = (sig.get("severity_level") or "").strip().title()
    if llm in _TAXONOMY:
        return llm
    try:
        from modules.pdf_intelligence import classify_severity_from_config  # type: ignore[import]
        return classify_severity_from_config(sig, doc_type)
    except ImportError:
        stype = sig.get("type", "")
        if stype in ("severity", "legal_escalation"):
            return "High"
        if stype in ("coverage_issue", "medical_complexity"):
            return "Moderate"
        return "Low"


def _render_signals_tab(intelligence: dict) -> None:
    raw_llm_signals = intelligence.get("analysis", {}).get("signals", [])
    doc_type        = intelligence.get("doc_type", "")

    # ── Fallback: keyword synthesis when LLM returned [] ─────────────────────
    synthesized = False
    if raw_llm_signals:
        signals = raw_llm_signals
    else:
        signals     = _synthesize_signals_from_entities(intelligence)
        synthesized = bool(signals)

    # Tab header
    st.markdown(
        _section_header(
            "Signal Detection",
            f"{len(signals)} signal(s) detected"
            + (" · keyword synthesized" if synthesized else " · AI extracted"),
        ),
        unsafe_allow_html=True,
    )

    # ── Debug expander — always visible, helps diagnose why LLM returned [] ──
    with st.expander("🔬 Debug: raw AI signals payload", expanded=False):
        st.markdown(
            f"<div style='font-size:10px;font-family:monospace;color:#b45309;"
            f"margin-bottom:8px;padding:6px 10px;background:#fffbeb;"
            f"border:1px solid #fde68a;border-radius:6px;'>"
            f"LLM returned <b>{len(raw_llm_signals)}</b> signal(s) · "
            f"doc_type=<b>{doc_type!r}</b> · "
            f"{'⚠ synthesized fallback active' if synthesized else '✓ using LLM signals'}"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.json(raw_llm_signals if raw_llm_signals else {"note": "LLM returned empty signals list — showing synthesized keyword fallback"})
        full_text = intelligence.get("full_text", "")
        if full_text:
            st.markdown(
                f"<div style='font-size:9px;color:{_LBL};font-family:monospace;"
                f"margin-top:8px;margin-bottom:4px;'>📄 First 600 chars of full_text (keyword search corpus):</div>",
                unsafe_allow_html=True,
            )
            st.code(full_text[:600], language="text")

    if not signals:
        st.markdown(
            _card(
                f"<div style='color:#16a34a;font-size:13px;font-family:monospace;'>"
                f"✓ No significant signals detected.</div>",
                border_color="#bbf7d0", bg="#f0fdf4",
            ),
            unsafe_allow_html=True,
        )
        return

    

    grouped: dict[str, list[dict]] = {lv: [] for lv in _TAXONOMY}
    for sig in signals:
        grouped[_classify_severity(sig, doc_type)].append(sig)

    pills = "".join(
        f"<span style='background:{_TAXONOMY[lv]['bg']};"
        f"border:1px solid {_TAXONOMY[lv]['color']}40;border-radius:20px;"
        f"padding:4px 12px;font-size:11px;font-weight:700;"
        f"color:{_TAXONOMY[lv]['color']};font-family:monospace;'>"
        f"{_TAXONOMY[lv]['icon']} {lv} ({len(sigs)})</span>"
        for lv, sigs in grouped.items()
        if sigs
    )
    if pills:
        st.markdown(
            f"<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px;'>"
            f"{pills}</div>",
            unsafe_allow_html=True,
        )

    for level in ["Highly Severe", "High", "Moderate", "Low"]:
        group_sigs = grouped.get(level, [])
        if not group_sigs:
            continue
        tax = _TAXONOMY[level]
        tc  = tax["color"]

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin:16px 0 8px 0;'>"
            f"<span style='font-size:16px;'>{tax['icon']}</span>"
            f"<span style='font-size:12px;font-weight:700;color:{tc};"
            f"font-family:monospace;text-transform:uppercase;letter-spacing:1.2px;'>{level}</span>"
            f"<div style='flex:1;height:1px;background:{tc}30;'></div>"
            f"<span style='font-size:10px;color:{tc};font-family:monospace;"
            f"background:{tax['bg']};border:1px solid {tc}30;border-radius:10px;"
            f"padding:1px 8px;'>{len(group_sigs)} signal(s)</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        for sig in group_sigs:
            sig_type = sig.get("type", "unknown")
            m = _get_signal_meta(sig_type, doc_type)
            c = m["color"]
            # Small badge distinguishing AI vs keyword source
            source_badge = (
                f"<span style='font-size:9px;color:#92400e;background:#fffbeb;"
                f"border:1px solid #fde68a;border-radius:10px;"
                f"padding:1px 7px;font-family:monospace;margin-left:6px;'>"
                "</span>"
                if sig.get("_synthesized") else
                f"<span style='font-size:9px;color:#1e40af;background:#eff6ff;"
                f"border:1px solid #bfdbfe;border-radius:10px;"
                f"padding:1px 7px;font-family:monospace;margin-left:6px;'>"
                "</span>"
            )
            st.markdown(
                f"<div style='background:{_BG};border:1px solid {_BORDER};"
                f"border-left:4px solid {tc};border-radius:8px;"
                f"padding:12px 16px;margin-bottom:8px;'>"
                f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;'>"
                f"<span style='font-size:14px;'>{m['icon']}</span>"
                f"<span style='font-size:11px;font-weight:700;color:{c};"
                f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;'>"
                f"{m['label']}</span>"
                f"{source_badge}"
                f"<span style='margin-left:auto;font-size:9px;color:{tc};"
                f"background:{tax['bg']};border:1px solid {tc}30;border-radius:10px;"
                f"padding:1px 7px;font-family:monospace;white-space:nowrap;'>"
                f"{tax['icon']} {level}</span>"
                f"</div>"
                f"<div style='font-size:13px;color:{_TXT};line-height:1.7;margin-bottom:6px;'>"
                f"{sig.get('description', '')}</div>"
                + (
                    f"<div style='font-size:11px;color:{_LBL};font-family:monospace;"
                    f"background:{_BG2};border-left:2px solid {_BORDER2};padding:5px 10px;"
                    f"border-radius:0 4px 4px 0;font-style:italic;'>"
                    f"📄 \"{sig.get('supporting_text', '')}\"</div>"
                    if sig.get("supporting_text") else ""
                )
                + "</div>",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — RAW JSON
# ─────────────────────────────────────────────────────────────────────────────

def _render_raw_json_tab(intelligence: dict, selected_sheet: str) -> None:
    eds  = _edits()
    hist = _edit_history()

    intel_kv = _get_intelligence_kv(selected_sheet)

    st.markdown(
        _section_header(
            "Extracted Key-Value Pairs",
            f"{len(intel_kv)} fields · modifications applied",
        ),
        unsafe_allow_html=True,
    )

    if not intel_kv:
        st.info("No extracted fields available. Run AI analysis first.")
        return

    edited_count = sum(1 for fn in intel_kv if fn in eds and eds[fn] != (
        next((fi.get("value", "") for nm, fi in _get_intelligence_entities(selected_sheet)
              if nm == fn), "")
    ))

    if edited_count:
        st.markdown(
            f"<div style='background:#eff6ff;border:1px solid #bfdbfe;"
            f"border-radius:6px;padding:8px 14px;margin-bottom:12px;"
            f"font-size:11px;font-family:monospace;color:#2563eb;'>"
            f"✏ {edited_count} field(s) show modified values below</div>",
            unsafe_allow_html=True,
        )

    st.code(json.dumps(intel_kv, indent=2, ensure_ascii=False), language="json")

    changed = [(fn, h) for fn, h in hist.items() if h and fn in intel_kv]
    if changed:
        rows_html = ""
        for fname, fchanges in changed:
            orig    = fchanges[0].get("from", "—")
            current = eds.get(fname, fchanges[-1].get("to", "—"))
            rows_html += (
                f"<div style='display:grid;grid-template-columns:180px 1fr auto 1fr;"
                f"gap:8px;padding:6px 0;border-bottom:1px solid {_BORDER};align-items:center;'>"
                f"<span style='font-size:11px;font-weight:600;color:{_TXT};"
                f"font-family:monospace;'>{fname}</span>"
                f"<span style='font-size:11px;color:{_LBL};font-family:monospace;"
                f"text-decoration:line-through;word-break:break-word;'>{orig}</span>"
                f"<span style='font-size:13px;color:{_LBL};'>→</span>"
                f"<span style='font-size:11px;color:#16a34a;font-family:monospace;"
                f"font-weight:600;word-break:break-word;'>{current}</span>"
                f"</div>"
            )
        with st.expander(f"📋 {len(changed)} modified field(s)"):
            st.markdown(
                f"<div style='background:{_BG};border:1px solid {_BORDER};"
                f"border-radius:8px;padding:12px 16px;'>"
                f"<div style='display:grid;grid-template-columns:180px 1fr auto 1fr;"
                f"gap:8px;padding-bottom:6px;border-bottom:1px solid {_BORDER};margin-bottom:4px;'>"
                f"<span style='font-size:9px;color:{_LBL};font-family:monospace;"
                f"text-transform:uppercase;letter-spacing:1px;'>Field</span>"
                f"<span style='font-size:9px;color:#dc2626;font-family:monospace;"
                f"text-transform:uppercase;letter-spacing:1px;'>Original</span>"
                f"<span></span>"
                f"<span style='font-size:9px;color:#16a34a;font-family:monospace;"
                f"text-transform:uppercase;letter-spacing:1px;'>Modified</span>"
                f"</div>{rows_html}</div>",
                unsafe_allow_html=True,
            )

    full_json_str = json.dumps(intel_kv, indent=2, ensure_ascii=False)
    st.markdown(
        f"<div style='font-size:11px;color:{_LBL};font-family:monospace;margin:10px 0;'>"
        f"⬇ {len(intel_kv)} fields · modified values included</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "📥 Download JSON",
            data=full_json_str,
            file_name="extracted_fields.json",
            mime="application/json",
            use_container_width=True,
        )
    with c2:
        if st.button("📋 Copy to clipboard", use_container_width=True):
            st.toast("Copied!")
            st.session_state["_json_clipboard"] = full_json_str

    full_text = intelligence.get("full_text", "")
    if full_text:
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        with st.expander("📄 Full extracted text"):
            st.text_area("raw_text_area", value=full_text, height=300,
                         label_visibility="collapsed")
            st.download_button(
                "📥 Download raw text", data=full_text,
                file_name="extracted_text.txt", mime="text/plain",
                use_container_width=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — TRANSFORMATION JOURNEY
# ─────────────────────────────────────────────────────────────────────────────

def _render_journey_tab(
    intelligence: dict,
    selected_sheet: str,
    uploaded_name: str,
) -> None:
    intel_fields   = _get_intelligence_entities(selected_sheet)
    raw_fields     = _get_raw_fields(selected_sheet)
    display_fields = intel_fields if intel_fields else raw_fields

    eds           = _edits()
    hist          = _edit_history()
    session_start = st.session_state.get("_session_start", "")
    now_str       = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    changed_fields   = [(fn, fi) for fn, fi in display_fields if fn in hist and hist[fn]]
    unchanged_fields = [(fn, fi) for fn, fi in display_fields if fn not in hist or not hist[fn]]
    edit_count       = len(changed_fields)

    last_edit_ts = ""
    if edit_count:
        all_ts = [ch["timestamp"] for fn, _ in changed_fields
                  for ch in hist.get(fn, []) if ch.get("timestamp")]
        if all_ts:
            last_edit_ts = max(all_ts)[:19].replace("T", " ")

    st.markdown(
        f"<div style='background:{_BG2};border:1px solid {_BORDER};"
        f"border-radius:10px;padding:16px 20px;margin-bottom:20px;'>"
        f"<div style='font-size:10px;font-weight:700;color:#b45309;"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:2px;"
        f"margin-bottom:14px;'>⚡ Pipeline Trace</div>"
        f"<div style='display:grid;grid-template-columns:160px 1fr;gap:8px;"
        f"padding:8px 0;border-bottom:1px solid {_BORDER};align-items:start;'>"
        f"<span style='font-size:10px;font-weight:700;color:#b45309;"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:.8px;'>"
        f"📄 FILE PARSED</span>"
        f"<span style='font-size:11px;color:{_TXT2};font-family:monospace;'>"
        f"→ Azure Document Intelligence parsed the PDF. Fields extracted to sheet cache. &nbsp;"
        f"<span style='color:{_LBL};'>{session_start[:19].replace('T',' ') if session_start else now_str}</span>"
        f"</span></div>"
        f"<div style='display:grid;grid-template-columns:160px 1fr;gap:8px;"
        f"padding:8px 0;border-bottom:1px solid {_BORDER};align-items:start;'>"
        f"<span style='font-size:10px;font-weight:700;color:#7c3aed;"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:.8px;'>"
        f"🤖 LLM CALL A</span>"
        f"<span style='font-size:11px;color:{_TXT2};font-family:monospace;'>"
        f"→ LLM extracted entities + signals (pdf_intelligence Call A). "
        f"Azure DI bounding boxes matched by field name similarity.</span></div>"
        f"<div style='display:grid;grid-template-columns:160px 1fr;gap:8px;"
        f"padding:8px 0;align-items:start;'>"
        f"<span style='font-size:10px;font-weight:700;color:#2563eb;"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:.8px;'>"
        f"✏️ USER EDITS</span>"
        f"<span style='font-size:11px;color:{_TXT2};font-family:monospace;'>"
        + (
            f"→ {edit_count} field(s) manually updated &nbsp;"
            f"<span style='color:{_LBL};'>{last_edit_ts}</span>"
            if edit_count else
            f"→ <span style='color:{_LBL};'>No edits made this session</span>"
        )
        + f"</span></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown(_section_header("Field Transformation Timeline"), unsafe_allow_html=True)

    def _step_circle(n: int, color: str) -> str:
        return (
            f"<div style='width:26px;height:26px;border-radius:50%;"
            f"background:{color}15;border:2px solid {color};"
            f"display:flex;align-items:center;justify-content:center;"
            f"font-size:11px;font-weight:700;color:{color};"
            f"font-family:monospace;flex-shrink:0;'>{n}</div>"
        )

    def _source_step_html(step_n: int, field_info: dict, step1_ts: str) -> str:
        """
        Renders Step 2 with the ACTUAL extraction source instead of a hardcoded label.
        Uses _extraction_source_label() to resolve the true pipeline step.
        """
        icon, label, detail = _extraction_source_label(field_info)

        # Colour the step circle based on source
        if field_info.get("_user_added"):
            step_color = "#7c3aed"
        elif field_info.get("_from_call_b"):
            step_color = "#ca8a04"
        elif field_info.get("_adi_matched") and field_info.get("_adi_confidence", 0) > 0:
            step_color = "#059669"
        elif field_info.get("_adi_matched"):
            step_color = "#0284c7"
        elif field_info.get("_pymupdf_bbox"):
            step_color = "#0284c7"
        else:
            step_color = "#7c3aed"

        adi_key  = field_info.get("_adi_matched_key", "")
        adi_conf = int(float(field_info.get("_adi_confidence", 0.0)) * 100)
        conf_str = f" · ADI conf {adi_conf}%" if adi_conf > 0 else ""
        key_str  = f" · ADI key: '{adi_key}'" if adi_key else ""

        return (
            f"<div style='display:flex;gap:12px;margin-bottom:10px;'>"
            f"{_step_circle(step_n, step_color)}"
            f"<div style='flex:1;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"margin-bottom:4px;'>"
            f"<span style='font-size:10px;font-weight:700;color:{step_color};"
            f"font-family:monospace;text-transform:uppercase;letter-spacing:.8px;'>"
            f"{icon} {label}</span>"
            f"<span style='font-size:9px;color:{_LBL};font-family:monospace;'>"
            f"⏱ {step1_ts} · {key_str}{conf_str}</span>"
            f"</div>"
            f"<div style='font-size:11px;color:{_LBL};font-family:monospace;"
            f"line-height:1.6;background:{_BG2};border:1px solid {_BORDER};"
            f"border-radius:4px;padding:6px 10px;'>{detail}</div>"
            f"</div></div>"
        )

    def _field_card(fname: str, finfo: dict) -> None:
        extracted = finfo.get("value", "")
        changes   = hist.get(fname, [])
        is_mod    = bool(changes)
        border    = "#fde68a" if is_mod else _BORDER
        bg        = "#fffbeb" if is_mod else _BG
        mod_badge = (
            f"<span style='margin-left:8px;font-size:9px;font-weight:700;"
            f"color:#b45309;background:#fef9c3;border:1px solid #fde047;"
            f"border-radius:10px;padding:2px 8px;font-family:monospace;'>"
            f"MODIFIED</span>"
            if is_mod else ""
        )
        src_page = finfo.get("source_page", "")
        src_text = finfo.get("source_text", "")
        step1_ts = session_start[:19].replace("T", " ") if session_start else now_str

        html = (
            f"<div style='background:{bg};border:1px solid {border};"
            f"border-radius:10px;padding:16px 18px;margin-bottom:12px;'>"
            f"<div style='font-size:12px;font-weight:700;color:{_TXT};"
            f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;"
            f"margin-bottom:14px;'>{fname}{mod_badge}</div>"

            # Step 1 — Azure DI / PDF parse
            f"<div style='display:flex;gap:12px;margin-bottom:10px;'>"
            f"{_step_circle(1,'#16a34a')}"
            f"<div style='flex:1;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"margin-bottom:4px;'>"
            f"<span style='font-size:10px;font-weight:700;color:#16a34a;"
            f"font-family:monospace;text-transform:uppercase;'>📄 Azure DI — PDF Parsed</span>"
            f"<span style='font-size:9px;color:{_LBL};font-family:monospace;'>"
            f"⏱ {step1_ts} </span>"
            f"</div>"
            f"<div style='font-size:11px;color:{_LBL};font-family:monospace;"
            f"margin-bottom:5px;'>Raw text and key-value pairs extracted from PDF."
            + (f" Source: page {src_page}." if src_page else "")
            + f"</div>"
            f"<div style='background:{_BG2};border:1px solid {_BORDER};border-radius:5px;"
            f"padding:8px 12px;font-size:12px;color:{_TXT};font-family:monospace;"
            f"word-break:break-word;min-height:32px;'>"
            f"{extracted if extracted else f'<span style=\"color:{_LBL2};\">—</span>'}"
            f"</div>"
            + (
                f"<div style='font-size:10px;color:{_LBL};font-family:monospace;"
                f"background:{_BG2};border-left:2px solid {_BORDER2};padding:4px 8px;"
                f"margin-top:5px;border-radius:0 4px 4px 0;font-style:italic;'>"
                f"📄 {src_text}</div>"
                if src_text else ""
            )
            + f"</div></div>"
        )

        # Step 2 — Actual extraction source (LLM / ADI / PyMuPDF / user)
        html += _source_step_html(2, finfo, step1_ts)

        # Step 3+ — User edits
        for i, ch in enumerate(changes):
            ts     = (ch.get("timestamp", "")[:19] or "").replace("T", " ")
            from_v = ch.get("from", "")
            to_v   = ch.get("to", "")
            html += (
                f"<div style='display:flex;gap:12px;margin-bottom:8px;'>"
                f"{_step_circle(i+3,'#ca8a04')}"
                f"<div style='flex:1;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"margin-bottom:6px;'>"
                f"<span style='font-size:10px;font-weight:700;color:#b45309;"
                f"font-family:monospace;text-transform:uppercase;'>✏️ User Edit #{i+1}</span>"
                f"<span style='font-size:9px;color:{_LBL};font-family:monospace;'>"
                f"⏱ {ts} · _sync_edit()</span>"
                f"</div>"
                f"<div style='display:flex;gap:10px;align-items:center;'>"
                f"<div style='flex:1;background:#fef2f2;border:1px solid #fecaca;"
                f"border-radius:5px;padding:7px 12px;font-size:12px;"
                f"color:#dc2626;font-family:monospace;word-break:break-word;'>"
                f"FROM: {from_v or '—'}</div>"
                f"<span style='font-size:16px;color:{_LBL};'>→</span>"
                f"<div style='flex:1;background:#f0fdf4;border:1px solid #bbf7d0;"
                f"border-radius:5px;padding:7px 12px;font-size:12px;"
                f"color:#16a34a;font-family:monospace;word-break:break-word;'>"
                f"TO: {to_v or '—'}</div>"
                f"</div></div></div>"
            )

        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    for fname, finfo in changed_fields:
        _field_card(fname, finfo)

    if unchanged_fields:
        with st.expander(f"📋 {len(unchanged_fields)} unchanged field(s)"):
            for fname, finfo in unchanged_fields:
                _field_card(fname, finfo)

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown(_section_header("Audit Log"), unsafe_allow_html=True)

    _EVENT_META = {
        "FILE_INGESTED":           {"color": "#16a34a", "icon": "📄"},
        "SHEET_PARSED":            {"color": "#2563eb", "icon": "🔍"},
        "SHEET_LOADED_FROM_CACHE": {"color": "#7c3aed", "icon": "💾"},
    }

    try:
        from modules.audit import _load_audit_log  # type: ignore[import]
        full_log = _load_audit_log()

        def _is_cur(e: dict) -> bool:
            ts = e.get("timestamp", "")
            return not ts or not session_start or ts >= session_start

        def _is_rel(e: dict) -> bool:
            return (
                uploaded_name in (e.get("filename") or "")
                or "PDF" in (e.get("event") or "").upper()
                or "pdf" in (e.get("sheet_type") or "").lower()
            )

        cur_log  = [e for e in full_log if _is_cur(e) and _is_rel(e)]
        hist_log = [e for e in full_log if not _is_cur(e) and _is_rel(e)]

        def _log_row(entry: dict, idx: int, prefix: str) -> None:
            ts    = (entry.get("timestamp", "")[:19] or "").replace("T", " ")
            event = entry.get("event", "UNKNOWN")
            em    = _EVENT_META.get(event, {"color": "#6b7280", "icon": "●"})
            c     = em["color"]
            parts = []
            if entry.get("sheet"):
                parts.append(entry["sheet"])
            if entry.get("sheet_type"):
                parts.append(entry["sheet_type"])
            if entry.get("claim_rows"):
                parts.append(f"{entry['claim_rows']} rows")
            detail = " · ".join(parts)
            st.markdown(
                f"<div style='background:{_BG2};border:1px solid {_BORDER};"
                f"border-left:3px solid {c};border-radius:6px;"
                f"padding:9px 14px;margin-bottom:4px;"
                f"display:flex;align-items:center;gap:12px;'>"
                f"<span style='font-size:9px;font-weight:700;color:{c};"
                f"font-family:monospace;background:{c}12;border:1px solid {c}30;"
                f"border-radius:4px;padding:2px 8px;white-space:nowrap;"
                f"text-transform:uppercase;'>{em['icon']} {event}</span>"
                f"<span style='font-size:10px;color:{_LBL};font-family:monospace;"
                f"white-space:nowrap;'>· {ts}</span>"
                f"<span style='font-size:11px;color:{_TXT2};font-family:monospace;'>"
                f"· {detail}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        if not cur_log:
            st.info("No log entries for this session.")
        else:
            for i, e in enumerate(reversed(cur_log[-30:])):
                _log_row(e, i, "cur")

        if hist_log:
            st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
            _hk = "_audit_show_hist"
            show_h = st.session_state.get(_hk, False)
            if st.button(
                "🕑 Hide previous history" if show_h else "🕑 View history",
                key="toggle_audit_hist",
            ):
                st.session_state[_hk] = not show_h
                st.rerun()
            if show_h:
                for i, e in enumerate(reversed(hist_log[-30:])):
                    _log_row(e, i, "hist")

    except Exception as exc:
        st.warning(f"Could not load audit log: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def _render_validation_dimension(icon: str, title: str, data: dict, color: str) -> None:
    score    = data.get("score",   0)
    verdict  = data.get("verdict", "Review")
    findings = data.get("findings", "")

    st.markdown(
        f"<div style='background:{_BG};border:1px solid {_BORDER};"
        f"border-left:4px solid {color};border-radius:10px;"
        f"padding:18px 20px;margin-bottom:14px;'>"
        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:4px;'>"
        f"<span style='font-size:20px;'>{icon}</span>"
        f"<span style='font-size:13px;font-weight:700;color:{_TXT};"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;'>{title}</span>"
        f"<div style='margin-left:auto;display:flex;align-items:center;gap:8px;'>"
        f"{_score_badge(score)}"
        f"{_verdict_badge(verdict)}"
        f"</div></div>"
        f"<div style='height:1px;background:{_BORDER};margin:10px 0;'></div>"
        f"<div style='font-size:13px;color:{_TXT2};line-height:1.8;'>{findings}</div>",
        unsafe_allow_html=True,
    )

    missed    = data.get("missed_fields") or data.get("missed_signals") or data.get("gaps") or []
    incorrect = data.get("incorrect_fields", [])
    false_pos = data.get("false_positives", [])

    if missed:
        items_html = "".join(
            f"<span style='background:#fef2f2;border:1px solid #fecaca;"
            f"border-radius:4px;padding:2px 8px;font-size:11px;"
            f"color:#dc2626;font-family:monospace;margin:2px;'>{m}</span>"
            for m in missed
        )
        st.markdown(
            f"<div style='margin-top:8px;'>"
            f"<div style='font-size:9px;font-weight:700;color:{_LBL};"
            f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;'>"
            f"Missing / Not Detected</div>"
            f"<div style='display:flex;flex-wrap:wrap;gap:4px;'>{items_html}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    if incorrect:
        rows = "".join(
            f"<div style='display:grid;grid-template-columns:140px 1fr auto 1fr;"
            f"gap:8px;padding:5px 0;border-bottom:1px solid {_BORDER};align-items:start;'>"
            f"<span style='font-size:11px;font-weight:600;color:{_TXT};"
            f"font-family:monospace;word-break:break-word;'>{item.get('field','')}</span>"
            f"<span style='font-size:11px;color:#dc2626;font-family:monospace;"
            f"word-break:break-word;text-decoration:line-through;'>{item.get('extracted','')}</span>"
            f"<span style='color:{_LBL};font-size:12px;'>→</span>"
            f"<span style='font-size:11px;color:#16a34a;font-family:monospace;"
            f"word-break:break-word;'>{item.get('expected','')}</span>"
            f"</div>"
            for item in incorrect
        )
        st.markdown(
            f"<div style='margin-top:10px;background:{_BG2};border:1px solid {_BORDER};"
            f"border-radius:6px;padding:10px 14px;'>"
            f"<div style='font-size:9px;font-weight:700;color:{_LBL};"
            f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;"
            f"margin-bottom:8px;'>Incorrect Extractions</div>"
            f"{rows}</div>",
            unsafe_allow_html=True,
        )

    if false_pos:
        items_html = "".join(
            f"<span style='background:#fffbeb;border:1px solid #fde68a;"
            f"border-radius:4px;padding:2px 8px;font-size:11px;"
            f"color:#b45309;font-family:monospace;margin:2px;'>{fp}</span>"
            for fp in false_pos
        )
        st.markdown(
            f"<div style='margin-top:8px;'>"
            f"<div style='font-size:9px;font-weight:700;color:{_LBL};"
            f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;'>"
            f"Potential False Positives</div>"
            f"<div style='display:flex;flex-wrap:wrap;gap:4px;'>{items_html}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_validation_tab(intelligence: dict, selected_sheet: str) -> None:
    st.markdown(_section_header("Document Validation"), unsafe_allow_html=True)

    st.markdown(
        f"<div style='background:#f0f9ff;border:1px solid #bae6fd;"
        f"border-left:4px solid #0284c7;border-radius:8px;"
        f"padding:14px 18px;margin-bottom:18px;'>"
        f"<div style='font-size:13px;font-weight:600;color:#0369a1;"
        f"margin-bottom:4px;'>✅ Deep Validation</div>"
        f"<div style='font-size:12px;color:#0c4a6e;line-height:1.7;'>"
        f"This validation evaluates extraction accuracy, signal credibility, and coverage "
        f"completeness using an enhanced reasoning pass over the extracted data. "
        f"Run on demand — results are cached for this session."
        f"</div></div>",
        unsafe_allow_html=True,
    )

    _VAL_KEY = "_pdf_validation_result"
    existing = st.session_state.get(_VAL_KEY)

    btn_label = "🔄 Re-run Validation" if existing else "▶ Run Validation"
    run_col, _ = st.columns([2, 5])
    with run_col:
        run_clicked = st.button(btn_label, key="_run_validation_btn",
                                use_container_width=True)

    if run_clicked:
        intel    = st.session_state.get("_pdf_intelligence", {})
        doc_type = intel.get("doc_type", "Legal")
        full_text = intel.get("full_text", "")
        analysis  = intel.get("analysis", {})
        extracted_entities = analysis.get("entities", {})
        detected_signals   = analysis.get("signals", [])
        azure_di_index     = intel.get("azure_di_index", {})

        if not full_text and not extracted_entities:
            st.error("No extracted data to validate. Run AI analysis first.")
            return

        with st.spinner("Running validation…"):
            try:
                from modules.pdf_intelligence import run_validation  # type: ignore[import]
                result = run_validation(
                    full_text=full_text,
                    doc_type=doc_type,
                    extracted_entities=extracted_entities,
                    detected_signals=detected_signals,
                    azure_di_fields=azure_di_index,
                )
                st.session_state[_VAL_KEY] = result
                existing = result
                st.toast("✅ Validation complete!")
            except ImportError:
                st.error("pdf_intelligence module not found. Cannot run validation.")
                return
            except Exception as exc:
                st.error(f"Validation failed: {exc}")
                return

    if not existing:
        st.markdown(
            f"<div style='background:{_BG2};border:1px solid {_BORDER};"
            f"border-radius:8px;padding:24px;text-align:center;"
            f"color:{_LBL};font-family:monospace;font-size:12px;'>"
            f"Click <strong>▶ Run Validation</strong> to start deep quality evaluation."
            f"</div>",
            unsafe_allow_html=True,
        )
        return

    overall    = existing.get("overall_validation", {})
    ov_score   = overall.get("score",   0)
    ov_verdict = overall.get("verdict", "Review")
    ov_summary = overall.get("summary", "")
    ov_color   = "#16a34a" if ov_score >= 80 else "#ca8a04" if ov_score >= 60 else "#dc2626"
    ov_bg      = "#f0fdf4" if ov_score >= 80 else "#fffbeb" if ov_score >= 60 else "#fef2f2"

    st.markdown(
        f"<div style='background:{ov_bg};border:2px solid {ov_color}30;"
        f"border-radius:12px;padding:20px 24px;margin-bottom:22px;'>"
        f"<div style='display:flex;align-items:center;gap:16px;margin-bottom:10px;'>"
        f"<div style='text-align:center;'>"
        f"<div style='font-size:42px;font-weight:900;color:{ov_color};"
        f"font-family:monospace;line-height:1;'>{ov_score}</div>"
        f"<div style='font-size:10px;color:{_LBL};font-family:monospace;'>/ 100</div>"
        f"</div>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'>"
        f"<span style='font-size:16px;font-weight:800;color:{_TXT};'>Overall Validation Score</span>"
        f"{_verdict_badge(ov_verdict)}"
        f"</div>"
        f"<div style='font-size:12px;color:{_TXT2};line-height:1.7;'>{ov_summary}</div>"
        f"</div></div>"
        f"<div style='height:6px;background:{_BORDER};border-radius:3px;overflow:hidden;'>"
        f"<div style='height:100%;width:{ov_score}%;background:{ov_color};"
        f"border-radius:3px;transition:width 0.5s;'></div></div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    dims = [
        ("extraction_accuracy", "🎯", "Extraction",  "#2563eb"),
        ("signal_credibility",  "⚡", "Signals",     "#7c3aed"),
        ("coverage_analysis",   "📋", "Coverage",    "#059669"),
    ]
    pills_html = ""
    for key, icon, label, color in dims:
        d  = existing.get(key, {})
        s  = d.get("score", 0)
        v  = d.get("verdict", "—")
        c2 = "#16a34a" if s >= 80 else "#ca8a04" if s >= 60 else "#dc2626"
        pills_html += (
            f"<div style='background:{_BG2};border:1px solid {_BORDER};"
            f"border-radius:8px;padding:12px 16px;flex:1;min-width:150px;'>"
            f"<div style='font-size:18px;margin-bottom:4px;'>{icon}</div>"
            f"<div style='font-size:10px;color:{_LBL};font-family:monospace;"
            f"text-transform:uppercase;letter-spacing:1px;'>{label}</div>"
            f"<div style='font-size:24px;font-weight:800;color:{c2};"
            f"font-family:monospace;margin:4px 0;'>{s}</div>"
            f"<div style='font-size:10px;color:{_LBL};font-family:monospace;'>{v}</div>"
            f"</div>"
        )

    st.markdown(
        f"<div style='display:flex;gap:12px;flex-wrap:wrap;margin-bottom:22px;'>"
        f"{pills_html}</div>",
        unsafe_allow_html=True,
    )

    st.markdown(_section_header("Dimension Details"), unsafe_allow_html=True)
    _render_validation_dimension("🎯", "Extraction Accuracy",
                                  existing.get("extraction_accuracy", {}), "#2563eb")
    _render_validation_dimension("⚡", "Signal Credibility",
                                  existing.get("signal_credibility", {}),  "#7c3aed")
    _render_validation_dimension("📋", "Coverage Analysis",
                                  existing.get("coverage_analysis", {}),   "#059669")

    actions = overall.get("recommended_actions", [])
    if actions:
        st.markdown(_section_header("Recommended Actions"), unsafe_allow_html=True)
        for i, action in enumerate(actions, 1):
            st.markdown(
                f"<div style='background:{_BG2};border:1px solid {_BORDER};"
                f"border-radius:6px;padding:10px 16px;margin-bottom:6px;"
                f"display:flex;gap:12px;align-items:flex-start;'>"
                f"<span style='font-size:11px;font-weight:700;color:#ffffff;"
                f"background:#0284c7;border-radius:50%;width:20px;height:20px;"
                f"display:flex;align-items:center;justify-content:center;"
                f"flex-shrink:0;font-family:monospace;'>{i}</span>"
                f"<span style='font-size:13px;color:{_TXT};line-height:1.6;'>{action}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    _, clr_col = st.columns([5, 2])
    with clr_col:
        if st.button("🗑 Clear validation results", key="_clear_validation_btn",
                     use_container_width=True):
            st.session_state.pop(_VAL_KEY, None)
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def render_pdf_analysis_panel(
    intelligence: dict,
    uploaded_name: str,
    selected_sheet: str,
) -> None:
    st.markdown(_UPLOADER_PLUS_CSS, unsafe_allow_html=True)

    doc_type = intelligence.get("doc_type", "Legal")
    meta     = _get_doc_type_meta(doc_type)
    subtype  = intelligence.get("analysis", {}).get("detected_subtype") or ""

    # ── Cache invalidation fingerprint ────────────────────────────────────────
    _intel_fp = (
        uploaded_name
        + "|" + str(intelligence.get("page_count", 0))
        + "|" + str(intelligence.get("doc_type", ""))
        + "|" + str(len(intelligence.get("full_text", "")))
        + "|" + intelligence.get("full_text", "")[:80]
    )
    _prev_fp = st.session_state.get("_pdf_analysis_intel_fp")
    if _prev_fp != _intel_fp:
        for _stale_key in (
            "_adi_lookup",
            "_adi_lookup_file",
            "_pdf_analysis_current_file",
            "_pdf_validation_result",
            "_pdf_summary_override",
            "_pdf_intel_debug",
            "_pdf_edits",
            "_pdf_edit_hist",
            "_pdf_edit_mode_fields",
        ):
            st.session_state.pop(_stale_key, None)
        st.session_state["_pdf_analysis_intel_fp"]     = _intel_fp
        st.session_state["_pdf_analysis_current_file"] = uploaded_name

    _tmpdir  = st.session_state.get("tmpdir", "")
    pdf_path: str | None = None
    if _tmpdir:
        for _ext in (".pdf", ".PDF"):
            _c = os.path.join(_tmpdir, f"input{_ext}")
            if os.path.exists(_c):
                pdf_path = _c
                break

    subtype_html = f"&nbsp;&nbsp;{_subtype_badge(subtype)}" if subtype else ""
    st.markdown(
        f"<div style='background:{meta['bg']};border:1px solid {meta['color']}30;"
        f"border-radius:10px;padding:13px 18px;margin-bottom:14px;'>"
        f"<div style='display:flex;align-items:center;gap:12px;'>"
        f"<span style='font-size:22px;'>{meta['icon']}</span>"
        f"<div>"
        f"<div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap;'>"
        f"<div style='font-size:14px;font-weight:700;color:{meta['color']};"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:1.5px;'>"
        f"{doc_type} Document Analysis</div>"
        f"{subtype_html}"
        f"</div>"
        f"<div style='font-size:11px;color:{_LBL};margin-top:3px;'>"
        f"📄 {uploaded_name} · {selected_sheet} · "
        f"{intelligence.get('page_count', 0)} page(s)</div>"
        f"</div></div></div>",
        unsafe_allow_html=True,
    )

    intel_fields    = _get_intelligence_entities(selected_sheet)
    _entities_count = len(intel_fields) if intel_fields else len(_get_raw_fields(selected_sheet))

    # Signal count includes synthesized signals for the tab badge
    _raw_signals   = intelligence.get("analysis", {}).get("signals", [])
    _synth_signals = _synthesize_signals_from_entities(intelligence) if not _raw_signals else []
    _signals_count = len(_raw_signals) if _raw_signals else len(_synth_signals)
    _signals_label = (
        f"⚡ Signals ({_signals_count}✦)"   # ✦ = synthesized
        if (not _raw_signals and _synth_signals) else
        f"⚡ Signals ({_signals_count})"
    )

    tabs = st.tabs([
        f"🔍 Entities ({_entities_count})",
        "📝 Summary",
        _signals_label,
        "📄 Raw JSON",
        "🔄 Transformation Journey",
        "✅ AI Assistant",
    ])

    with tabs[0]:
        _render_entities_tab(intelligence, selected_sheet, pdf_path)
    with tabs[1]:
        _render_summary_tab(intelligence, selected_sheet)
    with tabs[2]:
        _render_signals_tab(intelligence)
    with tabs[3]:
        _render_raw_json_tab(intelligence, selected_sheet)
    with tabs[4]:
        _render_journey_tab(intelligence, selected_sheet, uploaded_name)
    with tabs[5]:
        _render_validation_tab(intelligence, selected_sheet)