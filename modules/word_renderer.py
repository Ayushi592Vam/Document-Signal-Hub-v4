"""
ui/word_analysis.py  — v2

Word Document Analysis Panel

Architecture:
  • Classifies document type (Insurance Policy / Claims Report / Legal / Medical / etc.)
    using keyword-signal matching from word_parser.classify_word_document()
  • Renders 5 tabs matching the PDF analysis panel aesthetic:
      1. 🔍 Fields (N)            — extracted key-value pairs + source context + edit
      2. 📝 Summary               — classification badge + auto summary + annotations
      3. 📄 Raw JSON              — all fields as JSON, download
      4. 🔄 Transformation Journey — pipeline trace + per-field edit audit log
      5. ✅ Validation             — deep AI quality evaluation (on demand)

Design language:
  • Light theme (white background, dark text) — mirrors pdf_analysis.py exactly
  • Same colour tokens, badge helpers, card helpers, section headers
  • Model names never surfaced in UI

v2 changes:
  • Eye button now shows a bounding-box visualisation with confidence score,
    structural location (paragraph / table / row / column) and surrounding
    document context — rendered as an inline "document viewer" panel.
"""

from __future__ import annotations

import datetime
import html
import json
import os
import re

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS — document type metadata (extends word_parser classifications)
# ─────────────────────────────────────────────────────────────────────────────

_DOC_TYPE_META = {
    "Insurance Policy":          {"icon": "🛡️",  "color": "#0369a1", "bg": "rgba(3,105,161,0.06)"},
    "Claims Report":             {"icon": "🚨",  "color": "#dc2626", "bg": "rgba(220,38,38,0.06)"},
    "Loss Run Report":           {"icon": "📊",  "color": "#059669", "bg": "rgba(5,150,105,0.06)"},
    "Medical Report":            {"icon": "🏥",  "color": "#2563eb", "bg": "rgba(37,99,235,0.06)"},
    "Legal Document":            {"icon": "⚖️",  "color": "#7c3aed", "bg": "rgba(124,58,237,0.06)"},
    "Invoice / Bill":            {"icon": "🧾",  "color": "#b45309", "bg": "rgba(180,83,9,0.06)"},
    "Certificate of Insurance":  {"icon": "📜",  "color": "#0891b2", "bg": "rgba(8,145,178,0.06)"},
    "Correspondence / Letter":   {"icon": "✉️",  "color": "#6b7280", "bg": "rgba(107,114,128,0.06)"},
    "Contract / Agreement":      {"icon": "📋",  "color": "#7c3aed", "bg": "rgba(124,58,237,0.06)"},
    "Financial Statement":       {"icon": "💰",  "color": "#059669", "bg": "rgba(5,150,105,0.06)"},
    "General Document":          {"icon": "📄",  "color": "#475569", "bg": "rgba(71,85,105,0.06)"},
}

# ── Light-theme colour tokens (identical to pdf_analysis.py) ─────────────────
_BG      = "#ffffff"
_BG2     = "#f8f9fa"
_BG3     = "#f1f3f5"
_BORDER  = "#e2e8f0"
_BORDER2 = "#cbd5e1"
_TXT     = "#0f172a"
_TXT2    = "#1e293b"
_LBL     = "#64748b"
_LBL2    = "#94a3b8"


# ─────────────────────────────────────────────────────────────────────────────
# STYLE HELPERS  (mirrors pdf_analysis.py exactly)
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
        "Pass":           ("#16a34a", "#f0fdf4"),
        "Validated":      ("#16a34a", "#f0fdf4"),
        "Adequate":       ("#16a34a", "#f0fdf4"),
        "Fail":           ("#dc2626", "#fef2f2"),
        "Failed":         ("#dc2626", "#fef2f2"),
        "Unsupported":    ("#dc2626", "#fef2f2"),
        "Critical Gaps":  ("#dc2626", "#fef2f2"),
        "Review":         ("#ca8a04", "#fefce8"),
        "Needs Review":   ("#ca8a04", "#fefce8"),
        "Questionable":   ("#ca8a04", "#fefce8"),
        "Gaps Identified":("#ca8a04", "#fefce8"),
    }
    c, bg = vmap.get(verdict, ("#64748b", "#f8fafc"))
    return (
        f"<span style='background:{bg};border:1px solid {c}40;border-radius:6px;"
        f"padding:3px 12px;font-size:11px;color:{c};font-weight:700;"
        f"font-family:monospace;'>{verdict}</span>"
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


# ─────────────────────────────────────────────────────────────────────────────
# SESSION-STATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _wa_key(uploaded_name: str, suffix: str) -> str:
    """Namespaced session-state key for this panel."""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", uploaded_name)
    return f"_wa_{safe}_{suffix}"


def _edits(uploaded_name: str) -> dict:
    k = _wa_key(uploaded_name, "edits")
    if k not in st.session_state:
        st.session_state[k] = {}
    return st.session_state[k]


def _edit_history(uploaded_name: str) -> dict:
    k = _wa_key(uploaded_name, "edit_hist")
    if k not in st.session_state:
        st.session_state[k] = {}
    return st.session_state[k]


def _sync_edit(field_name: str, new_value: str, uploaded_name: str) -> None:
    eds  = _edits(uploaded_name)
    hist = _edit_history(uploaded_name)
    old  = eds.get(field_name, "")
    eds[field_name] = new_value
    if field_name not in hist:
        hist[field_name] = []
    if not hist[field_name] or hist[field_name][-1]["to"] != new_value:
        hist[field_name].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "from":      old,
            "to":        new_value,
        })


# ─────────────────────────────────────────────────────────────────────────────
# BOUNDING BOX VISUALISATION  (new in v2)
# ─────────────────────────────────────────────────────────────────────────────

def _conf_color(conf: float) -> tuple[str, str, str]:
    """Return (border_color, bg_color, label_color) based on confidence."""
    pct = int(conf * 100)
    if pct >= 80:
        return "#16a34a", "#f0fdf4", "#15803d"
    elif pct >= 60:
        return "#ca8a04", "#fefce8", "#92400e"
    else:
        return "#dc2626", "#fef2f2", "#991b1b"


def _build_location_breadcrumb(field: dict) -> str:
    """Build a breadcrumb string for the field's structural location."""
    parts = []
    if field.get("source_table") is not None:
        parts.append(f"Table {field['source_table'] + 1}")
        if field.get("source_row") is not None:
            parts.append(f"Row {field['source_row'] + 1}")
        if field.get("source_col") is not None:
            parts.append(f"Col {field['source_col'] + 1}")
    elif field.get("source_para") is not None:
        parts.append(f"Paragraph {field['source_para'] + 1}")
    return " › ".join(parts) if parts else "Document Body"


def _render_bounding_box_panel(
    file_path:     str,
    field:         dict,
    current_val:   str,
    uploaded_name: str,
    radius: int = 3,
) -> str:
    """
    Render an HTML bounding-box visualisation panel that shows:
      1. A "document viewer" strip of surrounding blocks, with the matched
         block highlighted inside a glowing bounding box.
      2. A confidence gauge and structural metadata sidebar.

    Returns raw HTML string for st.markdown(unsafe_allow_html=True).
    """
    try:
        from modules.word_parser import extract_word_blocks
        blocks = extract_word_blocks(file_path)
    except Exception:
        blocks = []

    fname      = field.get("field_name", "")
    orig_val   = field.get("value", current_val)
    conf       = float(field.get("confidence", 0.9))
    src_block  = field.get("source_block")
    conf_pct   = int(conf * 100)
    border_c, conf_bg, label_c = _conf_color(conf)
    breadcrumb = _build_location_breadcrumb(field)
    block_type = "Table Cell" if field.get("source_table") is not None else "Paragraph"

    # ── find hit block ────────────────────────────────────────────────────────
    hit = None
    if src_block is not None:
        for i, b in enumerate(blocks):
            if b.get("block_id") == src_block:
                hit = i
                break
    if hit is None and orig_val:
        for i, b in enumerate(blocks):
            if orig_val.lower() in b.get("text", "").lower():
                hit = i
                break
    if hit is None:
        hit = 0

    start = max(0, hit - radius)
    end   = min(len(blocks), hit + radius + 1)

    # ── confidence ring SVG ───────────────────────────────────────────────────
    r          = 28
    circum     = 2 * 3.14159 * r
    dash_val   = circum * conf_pct / 100
    dash_gap   = circum - dash_val
    ring_color = border_c

    conf_ring_svg = (
        f"<svg width='72' height='72' viewBox='0 0 72 72'>"
        f"<circle cx='36' cy='36' r='{r}' fill='none' stroke='#e2e8f0' stroke-width='6'/>"
        f"<circle cx='36' cy='36' r='{r}' fill='none' stroke='{ring_color}' stroke-width='6'"
        f" stroke-dasharray='{dash_val:.1f} {dash_gap:.1f}'"
        f" stroke-linecap='round' transform='rotate(-90 36 36)'/>"
        f"<text x='36' y='40' text-anchor='middle' font-size='14' font-weight='800'"
        f" font-family='monospace' fill='{ring_color}'>{conf_pct}%</text>"
        f"</svg>"
    )

    # ── document context blocks ───────────────────────────────────────────────
    doc_blocks_html = ""
    for j, b in enumerate(blocks[start:end]):
        is_hit   = (start + j) == hit
        txt      = b.get("text", "")
        esc_txt  = html.escape(txt)

        if is_hit and orig_val:
            needle  = html.escape(orig_val.strip())
            pat     = re.compile(re.escape(needle), re.IGNORECASE)
            esc_txt = pat.sub(
                lambda m: (
                    f"<mark style='background:#fde047;color:#111827;"
                    f"padding:1px 3px;border-radius:3px;font-weight:700;'>"
                    f"{m.group(0)}</mark>"
                ),
                esc_txt,
            )

        # meta label for this block
        meta_bits = []
        if b.get("para_index")  is not None: meta_bits.append(f"§ {b['para_index'] + 1}")
        if b.get("table_index") is not None: meta_bits.append(f"T{b['table_index'] + 1}")
        if b.get("row_index")   is not None: meta_bits.append(f"R{b['row_index'] + 1}")
        if b.get("col_index")   is not None: meta_bits.append(f"C{b['col_index'] + 1}")
        meta_label = " · ".join(meta_bits) or b.get("block_type", "block").replace("_", " ").title()

        if is_hit:
            # ── THE BOUNDING BOX ──────────────────────────────────────────────
            # outer glow container
            doc_blocks_html += (
                f"<div style='"
                f"position:relative;"
                f"margin:8px 0 12px 0;"
                f"border-radius:8px;"
                f"box-shadow:0 0 0 2px {border_c}, 0 0 16px {border_c}40;"
                f"'>"
                # corner-pin label  TOP-LEFT
                f"<div style='"
                f"position:absolute;top:-11px;left:10px;"
                f"background:{border_c};color:#fff;"
                f"font-size:9px;font-weight:700;font-family:monospace;"
                f"padding:1px 7px;border-radius:4px;"
                f"text-transform:uppercase;letter-spacing:1px;"
                f"white-space:nowrap;'>"
                f"📍 {html.escape(fname)} · {meta_label}"
                f"</div>"
                # corner-pin label  TOP-RIGHT  (confidence)
                f"<div style='"
                f"position:absolute;top:-11px;right:10px;"
                f"background:{conf_bg};border:1px solid {border_c}60;"
                f"color:{label_c};"
                f"font-size:9px;font-weight:700;font-family:monospace;"
                f"padding:1px 7px;border-radius:4px;"
                f"white-space:nowrap;'>"
                f"conf {conf_pct}%"
                f"</div>"
                # dashed inner box
                f"<div style='"
                f"border:2px dashed {border_c};"
                f"border-radius:8px;"
                f"padding:12px 14px;"
                f"background:{conf_bg};"
                f"'>"
                f"<div style='"
                f"font-size:9px;font-weight:700;color:{label_c};"
                f"font-family:monospace;text-transform:uppercase;"
                f"letter-spacing:1.2px;margin-bottom:6px;'>"
                f"MATCHED BLOCK</div>"
                f"<div style='"
                f"font-size:12.5px;font-family:monospace;color:{_TXT};"
                f"line-height:1.6;white-space:pre-wrap;word-break:break-word;'>"
                f"{esc_txt}</div>"
                f"</div>"
                f"</div>"
            )
        else:
            # surrounding context block (dimmed)
            doc_blocks_html += (
                f"<div style='"
                f"margin:4px 0;"
                f"padding:8px 12px;"
                f"border:1px solid {_BORDER};"
                f"border-radius:6px;"
                f"background:{_BG2};"
                f"opacity:0.7;"
                f"'>"
                f"<div style='"
                f"font-size:9px;color:{_LBL2};font-family:monospace;"
                f"text-transform:uppercase;letter-spacing:1px;"
                f"margin-bottom:3px;'>{meta_label}</div>"
                f"<div style='"
                f"font-size:11.5px;font-family:monospace;color:{_LBL};"
                f"line-height:1.5;white-space:pre-wrap;word-break:break-word;'>"
                f"{esc_txt}</div>"
                f"</div>"
            )

    # ── metadata sidebar items ────────────────────────────────────────────────
    def _meta_row(label: str, value: str, value_color: str = _TXT) -> str:
        return (
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:flex-start;padding:5px 0;"
            f"border-bottom:1px solid {_BORDER};gap:8px;'>"
            f"<span style='font-size:9px;font-weight:700;color:{_LBL};"
            f"font-family:monospace;text-transform:uppercase;"
            f"letter-spacing:.8px;white-space:nowrap;'>{label}</span>"
            f"<span style='font-size:10px;color:{value_color};"
            f"font-family:monospace;text-align:right;word-break:break-all;'>"
            f"{html.escape(str(value))}</span>"
            f"</div>"
        )

    source_type   = "Table Cell" if field.get("source_table") is not None else "Paragraph"
    block_id_str  = str(src_block) if src_block is not None else "—"
    val_display   = (current_val or orig_val or "—")[:40]
    if len(current_val or orig_val or "") > 40:
        val_display += "…"

    meta_sidebar = (
        _meta_row("Field",       fname,        label_c)
        + _meta_row("Value",     val_display,  _TXT)
        + _meta_row("Conf.",     f"{conf_pct}%", label_c)
        + _meta_row("Source",    source_type)
        + _meta_row("Location",  breadcrumb)
        + _meta_row("Block ID",  block_id_str)
    )

    # ── assemble final panel ──────────────────────────────────────────────────
    panel = (
        f"<div style='"
        f"background:{_BG};"
        f"border:1px solid {_BORDER2};"
        f"border-left:4px solid {border_c};"
        f"border-radius:10px;"
        f"margin:2px 0 8px 0;"
        f"overflow:hidden;"
        f"'>"

        # ── header bar ────────────────────────────────────────────────────────
        f"<div style='"
        f"background:{conf_bg};"
        f"border-bottom:1px solid {border_c}30;"
        f"padding:10px 16px;"
        f"display:flex;align-items:center;gap:12px;"
        f"'>"
        f"<span style='font-size:14px;'>📦</span>"
        f"<div style='"
        f"font-size:11px;font-weight:700;color:{label_c};"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:1.5px;'>"
        f"Bounding Box · {html.escape(fname)}"
        f"</div>"
        f"<div style='margin-left:auto;display:flex;align-items:center;gap:8px;'>"
        f"{conf_ring_svg}"
        f"</div>"
        f"</div>"

        # ── body: two-column layout ───────────────────────────────────────────
        f"<div style='"
        f"display:grid;"
        f"grid-template-columns:1fr 180px;"
        f"gap:0;"
        f"'>"

        # left: document context viewer
        f"<div style='"
        f"padding:14px 16px;"
        f"border-right:1px solid {_BORDER};"
        f"min-height:120px;"
        f"'>"
        f"<div style='"
        f"font-size:9px;font-weight:700;color:{_LBL};"
        f"font-family:monospace;text-transform:uppercase;"
        f"letter-spacing:1.5px;margin-bottom:10px;'>"
        f"Document Context"
        f"</div>"
        f"{doc_blocks_html}"
        f"</div>"

        # right: metadata sidebar
        f"<div style='"
        f"padding:14px 14px;"
        f"background:{_BG2};"
        f"'>"
        f"<div style='"
        f"font-size:9px;font-weight:700;color:{_LBL};"
        f"font-family:monospace;text-transform:uppercase;"
        f"letter-spacing:1.5px;margin-bottom:10px;'>"
        f"Field Metadata"
        f"</div>"
        f"{meta_sidebar}"

        # confidence bar at the bottom of sidebar
        f"<div style='margin-top:14px;'>"
        f"<div style='"
        f"font-size:9px;font-weight:700;color:{_LBL};"
        f"font-family:monospace;text-transform:uppercase;"
        f"letter-spacing:.8px;margin-bottom:5px;'>"
        f"Confidence</div>"
        f"<div style='"
        f"height:8px;"
        f"background:{_BORDER};"
        f"border-radius:4px;"
        f"overflow:hidden;"
        f"'>"
        f"<div style='"
        f"height:100%;"
        f"width:{conf_pct}%;"
        f"background:linear-gradient(90deg,{border_c}99,{border_c});"
        f"border-radius:4px;"
        f"transition:width .4s ease;"
        f"'></div>"
        f"</div>"
        f"<div style='"
        f"font-size:11px;font-weight:800;color:{label_c};"
        f"font-family:monospace;margin-top:4px;'>"
        f"{conf_pct}%</div>"
        f"</div>"

        f"</div>"  # end sidebar
        f"</div>"  # end body grid
        f"</div>"  # end panel
    )

    return panel


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE CONTEXT RENDERER  (kept for other callers / journey tab)
# ─────────────────────────────────────────────────────────────────────────────

def _render_source_context(
    file_path: str,
    field: dict,
    current_val: str,
    radius: int = 2,
) -> str:
    """Return HTML for source context with value highlighted."""
    try:
        from modules.word_parser import extract_word_blocks
        blocks = extract_word_blocks(file_path)
    except Exception:
        blocks = []

    if not blocks:
        return (
            f"<div style='color:{_LBL};font-family:monospace;font-size:11px;'>"
            f"No readable blocks found in document.</div>"
        )

    orig_val  = field.get("value", current_val)
    src_block = field.get("source_block")
    hit = None

    if src_block is not None:
        for i, b in enumerate(blocks):
            if b.get("block_id") == src_block:
                hit = i
                break

    if hit is None and orig_val:
        for i, b in enumerate(blocks):
            if orig_val.lower() in b.get("text", "").lower():
                hit = i
                break

    if hit is None:
        hit = 0

    start = max(0, hit - radius)
    end   = min(len(blocks), hit + radius + 1)

    parts = []
    for j, b in enumerate(blocks[start:end]):
        is_hit  = (start + j) == hit
        txt     = b.get("text", "")
        esc_txt = html.escape(txt)

        if is_hit and orig_val:
            esc_needle = html.escape(orig_val.strip())
            pat = re.compile(re.escape(esc_needle), re.IGNORECASE)
            esc_txt = pat.sub(
                lambda m: (
                    f"<mark style='background:#fde047;color:#111827;"
                    f"padding:0 2px;border-radius:3px;'>{m.group(0)}</mark>"
                ),
                esc_txt,
            )

        meta_bits = []
        if b.get("para_index")  is not None: meta_bits.append(f"§ {b['para_index'] + 1}")
        if b.get("table_index") is not None: meta_bits.append(f"Table {b['table_index'] + 1}")
        if b.get("row_index")   is not None: meta_bits.append(f"Row {b['row_index'] + 1}")
        meta = " · ".join(meta_bits) or b.get("block_type", "block").replace("_", " ").title()

        border_c = f"2px solid #ca8a04" if is_hit else f"1px solid {_BORDER}"
        bg_c     = "#fffbeb"            if is_hit else _BG2

        parts.append(
            f"<div style='margin-bottom:6px;padding:8px 12px;"
            f"border:{border_c};border-radius:6px;background:{bg_c};'>"
            f"<div style='font-size:9px;color:{_LBL};font-family:monospace;"
            f"text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;'>{meta}</div>"
            f"<div style='font-size:12px;font-family:monospace;color:{_TXT};"
            f"line-height:1.55;white-space:pre-wrap;word-break:break-word;'>"
            f"{esc_txt}</div></div>"
        )

    return "".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — FIELDS
# ─────────────────────────────────────────────────────────────────────────────

def _render_fields_tab(
    fields:        list[dict],
    word_result:   dict,
    uploaded_name: str,
    file_path:     str,
) -> None:
    eds = _edits(uploaded_name)

    if not fields:
        st.markdown(
            _card(
                f"<div style='color:{_LBL};font-size:13px;font-family:monospace;'>"
                f"⚠ No fields could be extracted from this document.</div>",
                border_color="#fde68a", bg="#fffbeb",
            ),
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        _section_header(
            "Extracted Fields",
            f"{len(fields)} field(s) extracted · edit or inspect source below",
        ),
        unsafe_allow_html=True,
    )

    _HDR = (
        f"font-size:10px;font-weight:700;font-family:monospace;"
        f"text-transform:uppercase;letter-spacing:1.5px;"
        f"padding:6px 4px;border-bottom:1px solid {_BORDER};"
    )
    h1, h2, h3, h4 = st.columns([2.5, 3.5, 3.5, 1.0])
    h1.markdown(f"<div style='{_HDR}color:{_LBL};'>Field Name</div>",     unsafe_allow_html=True)
    h2.markdown(f"<div style='{_HDR}color:#059669;'>Extracted</div>",     unsafe_allow_html=True)
    h3.markdown(f"<div style='{_HDR}color:#2563eb;'>Modified</div>",      unsafe_allow_html=True)
    h4.markdown(f"<div style='{_HDR}color:{_LBL};text-align:center;'>Actions</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

    _EM_KEY = _wa_key(uploaded_name, "edit_mode")
    if _EM_KEY not in st.session_state:
        st.session_state[_EM_KEY] = set()

    _EY_KEY = _wa_key(uploaded_name, "eye_open")
    if _EY_KEY not in st.session_state:
        st.session_state[_EY_KEY] = set()

    for idx, field in enumerate(fields):
        fname     = field.get("field_name", f"Field_{idx}")
        extracted = field.get("value", "")
        conf      = float(field.get("confidence", 0.9))
        modified  = eds.get(fname, extracted)
        in_edit   = fname in st.session_state[_EM_KEY]
        eye_open  = fname in st.session_state[_EY_KEY]
        is_changed = modified != extracted

        c1, c2, c3, c4 = st.columns([2.5, 3.5, 3.5, 1.0])

        with c1:
            st.markdown(
                f"<div style='font-size:12px;font-weight:600;color:{_TXT};"
                f"font-family:monospace;padding:6px 4px 2px 4px;line-height:1.4;"
                f"word-break:break-word;'>{html.escape(fname)}</div>"
                f"<div style='padding:0 4px 6px 4px;'>{_conf_badge(conf)}</div>",
                unsafe_allow_html=True,
            )

        with c2:
            st.markdown(
                f"<div style='font-size:12px;color:{_TXT};font-family:monospace;"
                f"background:{_BG2};border:1px solid {_BORDER};"
                f"padding:7px 10px;border-radius:5px;min-height:34px;"
                f"line-height:1.5;white-space:pre-wrap;word-break:break-word;'>"
                f"{html.escape(extracted) if extracted else f'<span style=\"color:{_LBL2};\">—</span>'}"
                f"</div>",
                unsafe_allow_html=True,
            )

        with c3:
            if in_edit:
                st.text_input(
                    "modified_value", value=modified,
                    key=f"_wamv_{idx}_{fname}",
                    label_visibility="collapsed",
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
                    f"{html.escape(modified) if modified else f'<span style=\"color:{_LBL2};\">—</span>'}"
                    f"{_badge}</div>",
                    unsafe_allow_html=True,
                )

        with c4:
            be, beye = st.columns(2)
            with be:
                lbl = "💾" if in_edit else "✏️"
                if st.button(lbl, key=f"_wabtn_edit_{idx}",
                             help="Save" if in_edit else "Edit",
                             use_container_width=True):
                    if in_edit:
                        saved = st.session_state.get(f"_wamv_{idx}_{fname}", modified)
                        _sync_edit(fname, saved, uploaded_name)
                        st.session_state[_EM_KEY].discard(fname)
                    else:
                        st.session_state[_EM_KEY].add(fname)
                    st.rerun()

            with beye:
                eye_label = "✕" if eye_open else "👁"
                eye_help  = "Hide bounding box" if eye_open else "Show bounding box & confidence"
                if st.button(eye_label, key=f"_wabtn_eye_{idx}",
                             help=eye_help, use_container_width=True):
                    if eye_open:
                        st.session_state[_EY_KEY].discard(fname)
                    else:
                        st.session_state[_EY_KEY].add(fname)
                        st.session_state[_EM_KEY].discard(fname)
                    st.rerun()

        # ── Bounding box panel (new in v2) ────────────────────────────────────
        if eye_open and file_path and os.path.exists(file_path):
            bbox_html = _render_bounding_box_panel(
                file_path=file_path,
                field=field,
                current_val=modified,
                uploaded_name=uploaded_name,
                radius=3,
            )
            st.markdown(bbox_html, unsafe_allow_html=True)

        st.markdown(
            f"<div style='height:1px;background:{_BORDER};margin:2px 0 4px 0;'></div>",
            unsafe_allow_html=True,
        )

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

    _ANF_KEY = _wa_key(uploaded_name, "add_field_open")
    if _ANF_KEY not in st.session_state:
        st.session_state[_ANF_KEY] = False

    if not st.session_state[_ANF_KEY]:
        anf_col, _ = st.columns([2, 5])
        with anf_col:
            if st.button("＋  Add New Field", key=f"_wa_anf_open_{uploaded_name}",
                         help="Manually add a custom field",
                         use_container_width=True):
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
        nf_c1, nf_c2 = st.columns([1, 1])
        with nf_c1:
            st.markdown(
                f"<div style='font-size:10px;font-weight:700;color:{_LBL};"
                f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;"
                f"margin-bottom:4px;'>Field Name</div>", unsafe_allow_html=True,
            )
            new_fname = st.text_input(
                "nf_name", value="", placeholder="e.g. Policy Number",
                key=f"_wa_anf_name_{uploaded_name}", label_visibility="collapsed",
            )
        with nf_c2:
            st.markdown(
                f"<div style='font-size:10px;font-weight:700;color:{_LBL};"
                f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;"
                f"margin-bottom:4px;'>Field Value</div>", unsafe_allow_html=True,
            )
            new_fval = st.text_input(
                "nf_val", value="", placeholder="e.g. POL-2024-00123",
                key=f"_wa_anf_val_{uploaded_name}", label_visibility="collapsed",
            )
        st.markdown("</div>", unsafe_allow_html=True)

        btn_save, btn_cancel, _ = st.columns([1.2, 1, 4.8])
        with btn_save:
            if st.button("💾 Save Field", key=f"_wa_anf_save_{uploaded_name}",
                         use_container_width=True):
                fname = (new_fname or "").strip()
                fval  = (new_fval  or "").strip()
                existing_names = {f.get("field_name", "") for f in fields}
                if not fname:
                    st.error("Field name cannot be empty.")
                elif fname in existing_names:
                    st.error(f'Field "{fname}" already exists.')
                else:
                    _word_key = _wa_key(uploaded_name, "extra_fields")
                    if _word_key not in st.session_state:
                        st.session_state[_word_key] = []
                    st.session_state[_word_key].append({
                        "field_name":   fname,
                        "value":        fval,
                        "confidence":   1.0,
                        "source_block": None,
                        "source_text":  fval,
                        "source_para":  None,
                        "source_table": None,
                        "source_row":   None,
                        "source_col":   None,
                        "_user_added":  True,
                    })
                    _sync_edit(fname, fval, uploaded_name)
                    st.session_state[_ANF_KEY] = False
                    st.session_state.pop(f"_wa_anf_name_{uploaded_name}", None)
                    st.session_state.pop(f"_wa_anf_val_{uploaded_name}",  None)
                    st.toast(f'✅ Field "{fname}" added!')
                    st.rerun()

        with btn_cancel:
            if st.button("✕ Cancel", key=f"_wa_anf_cancel_{uploaded_name}",
                         use_container_width=True):
                st.session_state[_ANF_KEY] = False
                st.session_state.pop(f"_wa_anf_name_{uploaded_name}", None)
                st.session_state.pop(f"_wa_anf_val_{uploaded_name}",  None)
                st.rerun()


def _location_label(field: dict) -> str:
    if field.get("source_table") is not None:
        lbl = f"Table {field['source_table'] + 1}"
        if field.get("source_row") is not None:
            lbl += f", Row {field['source_row'] + 1}"
        return lbl
    if field.get("source_para") is not None:
        return f"Paragraph {field['source_para'] + 1}"
    return "Document"


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _build_field_kv(fields: list[dict], uploaded_name: str) -> dict[str, str]:
    eds = _edits(uploaded_name)
    return {
        f.get("field_name", ""): eds.get(
            f.get("field_name", ""), f.get("value", "")
        )
        for f in fields
        if f.get("field_name")
    }


def _regenerate_summary(
    fields:        list[dict],
    doc_label:     str,
    raw_text:      str,
    uploaded_name: str,
) -> str | None:
    kv        = _build_field_kv(fields, uploaded_name)
    eds       = _edits(uploaded_name)
    hist      = _edit_history(uploaded_name)

    field_lines = []
    for fname, val in kv.items():
        orig = ""
        if fname in hist and hist[fname]:
            orig = hist[fname][0].get("from", "")
        if orig and orig != val:
            field_lines.append(f"  {fname}: {val}  [was: {orig}]")
        else:
            field_lines.append(f"  {fname}: {val}")

    fields_block = "\n".join(field_lines) or "(no fields extracted)"

    system_prompt = (
        f"You are a senior document analyst specialising in insurance and legal documents. "
        f"Generate a concise factual summary (max 200 words) of this {doc_label} document "
        f"reflecting CURRENT field values. Write natural prose — no field names. "
        f"Return ONLY the summary text with no preamble."
    )
    user_prompt = (
        f"Document type: {doc_label}\n\n"
        f"CURRENT FIELD VALUES:\n{fields_block}\n\n"
        f"DOCUMENT TEXT (context):\n{raw_text[:4000]}"
        + ("\n[... truncated ...]" if len(raw_text) > 4000 else "")
    )

    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=os.environ.get("OPENAI_DEPLOYMENT_ENDPOINT", ""),
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            api_version=os.environ.get("OPENAI_API_VERSION", "2024-12-01-preview"),
        )
        deployment = os.environ.get("OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
        response = client.chat.completions.create(
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


def _auto_summarise(
    fields:    list[dict],
    doc_label: str,
    raw_text:  str,
) -> str:
    kv = {f.get("field_name", ""): f.get("value", "") for f in fields if f.get("field_name")}
    if not kv and not raw_text:
        return ""

    parts: list[str] = [f"This is a **{doc_label}**."]

    priority_fields = [
        ("Claim Number", "claim number"),
        ("Policy Number", "policy number"),
        ("Insured",       "insured party"),
        ("Claimant Name", "claimant"),
        ("Carrier",       "carrier"),
        ("Loss Date",     "loss date"),
        ("Status",        "status"),
        ("Effective Date","effective date"),
    ]

    for fname, label in priority_fields:
        if fname in kv and kv[fname]:
            parts.append(f"The {label} is **{kv[fname]}**.")

    if raw_text and len(parts) < 3:
        snippet = " ".join(raw_text.split()[:60])
        parts.append(f"Excerpt: {snippet}…")

    return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def _render_summary_tab(
    word_result:   dict,
    fields:        list[dict],
    uploaded_name: str,
) -> None:
    clf        = word_result.get("doc_classification", {})
    doc_label  = clf.get("doc_type_label", "General Document")
    doc_conf   = float(clf.get("confidence", 0.0))
    signals    = clf.get("matched_signals", [])
    raw_text   = word_result.get("raw_text", "")
    meta       = _DOC_TYPE_META.get(doc_label, _DOC_TYPE_META["General Document"])

    _SUMM_KEY  = _wa_key(uploaded_name, "summary_override")
    summary    = st.session_state.get(_SUMM_KEY) or _auto_summarise(fields, doc_label, raw_text)

    eds  = _edits(uploaded_name)
    hist = _edit_history(uploaded_name)

    st.markdown(
        f"<div style='background:{meta['bg']};border:1px solid {meta['color']}30;"
        f"border-left:4px solid {meta['color']};border-radius:8px;"
        f"padding:14px 18px;margin-bottom:16px;'>"
        f"<div style='display:flex;align-items:center;gap:12px;'>"
        f"<span style='font-size:28px;'>{meta['icon']}</span>"
        f"<div>"
        f"<div style='font-size:20px;font-weight:800;color:{meta['color']};"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:2px;'>{doc_label}</div>"
        f"<div style='font-size:11px;color:{_LBL};margin-top:2px;'>"
        f"Classification confidence: {_conf_badge(doc_conf)}</div>"
        f"</div></div></div>",
        unsafe_allow_html=True,
    )

    if signals:
        chips = "".join(
            f"<span style='background:{_BG2};border:1px solid {_BORDER2};"
            f"border-radius:4px;padding:2px 8px;font-size:10px;color:{_LBL};"
            f"font-family:monospace;'>{s}</span> "
            for s in signals
        )
        st.markdown(
            f"<div style='margin-bottom:14px;'>"
            f"<span style='font-size:9px;font-weight:700;color:{_LBL};"
            f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;'>Signals: </span>"
            f"{chips}</div>",
            unsafe_allow_html=True,
        )

    changed = [(fn, h) for fn, h in hist.items() if h]
    is_regenerated = bool(st.session_state.get(_SUMM_KEY))

    btn_col, status_col = st.columns([2, 6])
    with btn_col:
        regen_lbl = "🔄 Re-regenerate Summary" if is_regenerated else "🔄 Regenerate with Edits"
        if st.button(
            regen_lbl,
            key=f"_wa_regen_summary_{uploaded_name}",
            help="Regenerate summary using edited field values" if changed else "Make edits in the Fields tab first",
            disabled=not changed,
            use_container_width=True,
        ):
            with st.spinner("Regenerating summary…"):
                new_sum = _regenerate_summary(fields, doc_label, raw_text, uploaded_name)
            if new_sum:
                st.session_state[_SUMM_KEY] = new_sum
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
                f"padding-top:8px;'>⚠ {len(changed)} field(s) edited — click Regenerate to update</div>",
                unsafe_allow_html=True,
            )

    if is_regenerated:
        if st.button("↩ Reset to original summary", key=f"_wa_reset_sum_{uploaded_name}"):
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
                        f"title='Edited from: {html.escape(old_val)}'>{html.escape(new_val)}</span>",
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
                    f"font-family:monospace;'>{html.escape(fname)}</span>"
                    f"<span style='font-size:11px;color:{_LBL};font-family:monospace;"
                    f"text-decoration:line-through;word-break:break-word;'>{html.escape(old_v)}</span>"
                    f"<span style='font-size:13px;color:{_LBL};'>→</span>"
                    f"<span style='font-size:11px;color:#2563eb;font-family:monospace;"
                    f"font-weight:600;word-break:break-word;'>{html.escape(new_v)}</span>"
                    f"</div>"
                )
            st.markdown(
                f"<div style='background:#fffbeb;border:1px solid #fde68a;"
                f"border-radius:8px;padding:12px 16px;margin-top:12px;'>"
                f"<div style='font-size:10px;font-weight:700;color:#b45309;"
                f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;"
                f"margin-bottom:6px;'>⚠ {len(changed)} Pending Edit(s)</div>"
                f"<div style='font-size:9px;color:{_LBL};font-family:monospace;"
                f"margin-bottom:8px;'>Click Regenerate with Edits to update the summary.</div>"
                f"{rows_html}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No summary available.")

    word_count = len(raw_text.split())
    char_count = len(raw_text)
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
                ("Fields",     len(fields)),
                ("Words",      word_count),
                ("Characters", char_count),
                ("Doc Type",   doc_label),
            ]
        )
        + "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — RAW JSON
# ─────────────────────────────────────────────────────────────────────────────

def _render_raw_json_tab(
    fields:        list[dict],
    word_result:   dict,
    uploaded_name: str,
) -> None:
    eds  = _edits(uploaded_name)
    hist = _edit_history(uploaded_name)
    clf  = word_result.get("doc_classification", {})

    kv = _build_field_kv(fields, uploaded_name)

    st.markdown(
        _section_header(
            "Extracted Key-Value Pairs",
            f"{len(kv)} fields · modifications applied",
        ),
        unsafe_allow_html=True,
    )

    if not kv:
        st.info("No extracted fields available.")
        return

    edited_count = sum(
        1 for fname, val in kv.items()
        if fname in eds and eds[fname] != next(
            (f.get("value", "") for f in fields if f.get("field_name") == fname), ""
        )
    )

    if edited_count:
        st.markdown(
            f"<div style='background:#eff6ff;border:1px solid #bfdbfe;"
            f"border-radius:6px;padding:8px 14px;margin-bottom:12px;"
            f"font-size:11px;font-family:monospace;color:#2563eb;'>"
            f"✏ {edited_count} field(s) show modified values below</div>",
            unsafe_allow_html=True,
        )

    st.code(json.dumps(kv, indent=2, ensure_ascii=False), language="json")

    changed = [(fn, h) for fn, h in hist.items() if h and fn in kv]
    if changed:
        rows_html = ""
        for fname, fchanges in changed:
            orig    = fchanges[0].get("from", "—")
            current = eds.get(fname, fchanges[-1].get("to", "—"))
            rows_html += (
                f"<div style='display:grid;grid-template-columns:180px 1fr auto 1fr;"
                f"gap:8px;padding:6px 0;border-bottom:1px solid {_BORDER};align-items:center;'>"
                f"<span style='font-size:11px;font-weight:600;color:{_TXT};"
                f"font-family:monospace;'>{html.escape(fname)}</span>"
                f"<span style='font-size:11px;color:{_LBL};font-family:monospace;"
                f"text-decoration:line-through;word-break:break-word;'>{html.escape(orig)}</span>"
                f"<span style='font-size:13px;color:{_LBL};'>→</span>"
                f"<span style='font-size:11px;color:#16a34a;font-family:monospace;"
                f"font-weight:600;word-break:break-word;'>{html.escape(current)}</span>"
                f"</div>"
            )
        with st.expander(f"📋 {len(changed)} modified field(s)"):
            st.markdown(
                f"<div style='background:{_BG};border:1px solid {_BORDER};"
                f"border-radius:8px;padding:12px 16px;'>"
                f"<div style='display:grid;grid-template-columns:180px 1fr auto 1fr;"
                f"gap:8px;padding-bottom:6px;border-bottom:1px solid {_BORDER};"
                f"margin-bottom:4px;'>"
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

    full_payload = {
        "file_name":       uploaded_name,
        "doc_type":        clf.get("doc_type_label", "General Document"),
        "confidence":      clf.get("confidence", 0.0),
        "matched_signals": clf.get("matched_signals", []),
        "fields":          kv,
    }
    full_json_str = json.dumps(full_payload, indent=2, ensure_ascii=False)

    st.markdown(
        f"<div style='font-size:11px;color:{_LBL};font-family:monospace;margin:10px 0;'>"
        f"⬇ {len(kv)} fields · modified values included</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "📥 Download JSON",
            data=full_json_str,
            file_name=f"{os.path.splitext(uploaded_name)[0]}_fields.json",
            mime="application/json",
            use_container_width=True,
        )
    with c2:
        if st.button("📋 Copy to clipboard", use_container_width=True,
                     key=f"_wa_copy_json_{uploaded_name}"):
            st.toast("Copied!")

    raw_text = word_result.get("raw_text", "")
    if raw_text:
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        with st.expander("📄 Full extracted text"):
            st.text_area("wa_raw_text", value=raw_text, height=300,
                         label_visibility="collapsed")
            st.download_button(
                "📥 Download raw text", data=raw_text,
                file_name=f"{os.path.splitext(uploaded_name)[0]}_text.txt",
                mime="text/plain", use_container_width=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — TRANSFORMATION JOURNEY
# ─────────────────────────────────────────────────────────────────────────────

def _render_journey_tab(
    fields:        list[dict],
    uploaded_name: str,
) -> None:
    eds           = _edits(uploaded_name)
    hist          = _edit_history(uploaded_name)
    session_start = st.session_state.get("_session_start", "")
    now_str       = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    changed_fields   = [(f, hist[f.get("field_name","")]) for f in fields
                        if f.get("field_name","") in hist and hist[f.get("field_name","")]]
    unchanged_fields = [f for f in fields
                        if f.get("field_name","") not in hist or not hist.get(f.get("field_name",""), [])]
    edit_count = len(changed_fields)

    last_edit_ts = ""
    if edit_count:
        all_ts = [ch["timestamp"]
                  for fn, changes in hist.items()
                  for ch in changes
                  if ch.get("timestamp")]
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
        f"font-family:monospace;text-transform:uppercase;letter-spacing:.8px;'>📄 FILE PARSED</span>"
        f"<span style='font-size:11px;color:{_TXT2};font-family:monospace;'>"
        f"→ Fields extracted from Word document &nbsp;"
        f"<span style='color:{_LBL};'>{session_start[:19].replace('T',' ') if session_start else now_str}</span>"
        f"</span></div>"
        f"<div style='display:grid;grid-template-columns:160px 1fr;gap:8px;"
        f"padding:8px 0;align-items:start;'>"
        f"<span style='font-size:10px;font-weight:700;color:#2563eb;"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:.8px;'>✏️ USER EDITS</span>"
        f"<span style='font-size:11px;color:{_TXT2};font-family:monospace;'>"
        + (
            f"→ {edit_count} field(s) manually updated &nbsp;"
            f"<span style='color:{_LBL};'>{last_edit_ts}</span>"
            if edit_count else
            f"→ <span style='color:{_LBL};'>No edits made this session</span>"
        )
        + "</span></div></div>",
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

    def _field_journey_card(field: dict, fchanges: list) -> None:
        fname     = field.get("field_name", "")
        extracted = field.get("value", "")
        is_mod    = bool(fchanges)
        border    = "#fde68a" if is_mod else _BORDER
        bg        = "#fffbeb" if is_mod else _BG
        mod_badge = (
            f"<span style='margin-left:8px;font-size:9px;font-weight:700;"
            f"color:#b45309;background:#fef9c3;border:1px solid #fde047;"
            f"border-radius:10px;padding:2px 8px;font-family:monospace;'>"
            f"MODIFIED</span>"
            if is_mod else ""
        )
        step1_ts  = session_start[:19].replace("T", " ") if session_start else now_str
        loc_label = _location_label(field)

        html_parts = [
            f"<div style='background:{bg};border:1px solid {border};"
            f"border-radius:10px;padding:16px 18px;margin-bottom:12px;'>"
            f"<div style='font-size:12px;font-weight:700;color:{_TXT};"
            f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;"
            f"margin-bottom:14px;'>{html.escape(fname)}{mod_badge}</div>"

            f"<div style='display:flex;gap:12px;margin-bottom:10px;'>"
            f"{_step_circle(1,'#16a34a')}"
            f"<div style='flex:1;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"margin-bottom:4px;'>"
            f"<span style='font-size:10px;font-weight:700;color:#16a34a;"
            f"font-family:monospace;text-transform:uppercase;'>Extracted from Document</span>"
            f"<span style='font-size:9px;color:{_LBL};font-family:monospace;'>"
            f"⏱ {step1_ts} · word_parser</span>"
            f"</div>"
            f"<div style='font-size:11px;color:{_LBL};font-family:monospace;"
            f"margin-bottom:5px;'>{loc_label}</div>"
            f"<div style='background:{_BG2};border:1px solid {_BORDER};border-radius:5px;"
            f"padding:8px 12px;font-size:12px;color:{_TXT};font-family:monospace;"
            f"word-break:break-word;min-height:32px;'>"
            f"{html.escape(extracted) if extracted else f'<span style=\"color:{_LBL2};\">—</span>'}"
            f"</div>"
            + (
                f"<div style='font-size:10px;color:{_LBL};font-family:monospace;"
                f"background:{_BG2};border-left:2px solid {_BORDER2};padding:4px 8px;"
                f"margin-top:5px;border-radius:0 4px 4px 0;font-style:italic;'>"
                f"📄 {html.escape(field.get('source_text', ''))}</div>"
                if field.get("source_text") else ""
            )
            + "</div></div>"

            f"<div style='display:flex;gap:12px;margin-bottom:10px;'>"
            f"{_step_circle(2,'#2563eb')}"
            f"<div style='flex:1;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"margin-bottom:4px;'>"
            f"<span style='font-size:10px;font-weight:700;color:#2563eb;"
            f"font-family:monospace;text-transform:uppercase;'>→ Rule-based Field Parser</span>"
            f"<span style='font-size:9px;color:{_LBL};font-family:monospace;'>"
            f"⏱ {step1_ts} · extract_word_fields_from_blocks</span>"
            f"</div>"
            f"<div style='font-size:11px;color:{_LBL};font-family:monospace;'>"
            f"Confidence: {int(float(field.get('confidence', 0.9)) * 100)}% · "
            f"Pass: {'inline' if field.get('source_para') is not None else 'table'} extraction</div>"
            f"</div></div>"
        ]

        for i, ch in enumerate(fchanges):
            ts     = (ch.get("timestamp", "")[:19] or "").replace("T", " ")
            from_v = ch.get("from", "")
            to_v   = ch.get("to", "")
            html_parts.append(
                f"<div style='display:flex;gap:12px;margin-bottom:8px;'>"
                f"{_step_circle(i+3,'#ca8a04')}"
                f"<div style='flex:1;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"margin-bottom:6px;'>"
                f"<span style='font-size:10px;font-weight:700;color:#b45309;"
                f"font-family:monospace;text-transform:uppercase;'>→ User Edit</span>"
                f"<span style='font-size:9px;color:{_LBL};font-family:monospace;'>"
                f"⏱ {ts} · _sync_edit()</span>"
                f"</div>"
                f"<div style='display:flex;gap:10px;align-items:center;'>"
                f"<div style='flex:1;background:#fef2f2;border:1px solid #fecaca;"
                f"border-radius:5px;padding:7px 12px;font-size:12px;"
                f"color:#dc2626;font-family:monospace;word-break:break-word;'>"
                f"FROM: {html.escape(from_v or '—')}</div>"
                f"<span style='font-size:16px;color:{_LBL};'>→</span>"
                f"<div style='flex:1;background:#f0fdf4;border:1px solid #bbf7d0;"
                f"border-radius:5px;padding:7px 12px;font-size:12px;"
                f"color:#16a34a;font-family:monospace;word-break:break-word;'>"
                f"TO: {html.escape(to_v or '—')}</div>"
                f"</div></div></div>"
            )

        html_parts.append("</div>")
        st.markdown("".join(html_parts), unsafe_allow_html=True)

    for field, fchanges in changed_fields:
        _field_journey_card(field, fchanges)

    if unchanged_fields:
        with st.expander(f"📋 {len(unchanged_fields)} unchanged field(s)"):
            for field in unchanged_fields:
                fname = field.get("field_name", "")
                _field_journey_card(field, hist.get(fname, []))


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def _run_word_validation(
    fields:    list[dict],
    doc_label: str,
    raw_text:  str,
    uploaded_name: str,
) -> dict | None:
    kv = _build_field_kv(fields, uploaded_name)
    fields_block = "\n".join(f"  {k}: {v}" for k, v in kv.items()) or "(no fields)"

    system_prompt = (
        "You are a document quality evaluator. Analyse the extracted fields from a "
        f"{doc_label} Word document and return ONLY a JSON object with this structure:\n"
        '{\n'
        '  "overall_validation": {\n'
        '    "score": <int 0-100>,\n'
        '    "verdict": "<Pass|Review|Fail>",\n'
        '    "confidence": <float 0-1>,\n'
        '    "summary": "<2-3 sentence summary>",\n'
        '    "recommended_actions": ["<action1>", ...]\n'
        '  },\n'
        '  "extraction_accuracy": {\n'
        '    "score": <int>,\n'
        '    "verdict": "<Validated|Needs Review|Failed>",\n'
        '    "findings": "<text>",\n'
        '    "incorrect_fields": [{"field": "...", "extracted": "...", "expected": "..."}],\n'
        '    "missed_fields": ["..."]\n'
        '  },\n'
        '  "completeness": {\n'
        '    "score": <int>,\n'
        '    "verdict": "<Adequate|Gaps Identified|Critical Gaps>",\n'
        '    "findings": "<text>",\n'
        '    "gaps": ["..."]\n'
        '  },\n'
        '  "document_quality": {\n'
        '    "score": <int>,\n'
        '    "verdict": "<Pass|Review|Fail>",\n'
        '    "findings": "<text>"\n'
        '  }\n'
        '}\n'
        'Return ONLY the JSON. No preamble, no markdown fences.'
    )
    user_prompt = (
        f"Document type: {doc_label}\n\n"
        f"Extracted fields:\n{fields_block}\n\n"
        f"Document text excerpt:\n{raw_text[:3000]}"
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
            max_tokens=1200,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(raw)
    except Exception:
        return None


def _render_val_dimension(
    icon:    str,
    title:   str,
    data:    dict,
    color:   str,
) -> None:
    score    = data.get("score", 0)
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
        f"{_score_badge(score)}{_verdict_badge(verdict)}"
        f"</div></div>"
        f"<div style='height:1px;background:{_BORDER};margin:10px 0;'></div>"
        f"<div style='font-size:13px;color:{_TXT2};line-height:1.8;'>{findings}</div>",
        unsafe_allow_html=True,
    )

    missed    = data.get("missed_fields") or data.get("gaps") or []
    incorrect = data.get("incorrect_fields", [])

    if missed:
        items_html = "".join(
            f"<span style='background:#fef2f2;border:1px solid #fecaca;"
            f"border-radius:4px;padding:2px 8px;font-size:11px;"
            f"color:#dc2626;font-family:monospace;margin:2px;'>{html.escape(str(m))}</span>"
            for m in missed
        )
        st.markdown(
            f"<div style='margin-top:8px;'>"
            f"<div style='font-size:9px;font-weight:700;color:{_LBL};"
            f"font-family:monospace;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;'>"
            f"Missing / Gaps</div>"
            f"<div style='display:flex;flex-wrap:wrap;gap:4px;'>{items_html}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    if incorrect:
        rows = "".join(
            f"<div style='display:grid;grid-template-columns:140px 1fr auto 1fr;"
            f"gap:8px;padding:5px 0;border-bottom:1px solid {_BORDER};align-items:start;'>"
            f"<span style='font-size:11px;font-weight:600;color:{_TXT};"
            f"font-family:monospace;'>{html.escape(str(item.get('field','')))}</span>"
            f"<span style='font-size:11px;color:#dc2626;font-family:monospace;"
            f"text-decoration:line-through;'>{html.escape(str(item.get('extracted','')))}</span>"
            f"<span style='color:{_LBL};font-size:12px;'>→</span>"
            f"<span style='font-size:11px;color:#16a34a;font-family:monospace;'>"
            f"{html.escape(str(item.get('expected','')))}</span>"
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

    st.markdown("</div>", unsafe_allow_html=True)


def _render_validation_tab(
    fields:        list[dict],
    word_result:   dict,
    uploaded_name: str,
) -> None:
    st.markdown(_section_header("Document Validation"), unsafe_allow_html=True)

    clf       = word_result.get("doc_classification", {})
    doc_label = clf.get("doc_type_label", "General Document")
    raw_text  = word_result.get("raw_text", "")

    st.markdown(
        f"<div style='background:#f0f9ff;border:1px solid #bae6fd;"
        f"border-left:4px solid #0284c7;border-radius:8px;"
        f"padding:14px 18px;margin-bottom:18px;'>"
        f"<div style='font-size:13px;font-weight:600;color:#0369a1;margin-bottom:4px;'>"
        f"✅ Deep Validation</div>"
        f"<div style='font-size:12px;color:#0c4a6e;line-height:1.7;'>"
        f"Evaluates extraction accuracy, field completeness, and document quality "
        f"using an AI reasoning pass. Run on demand — results are cached for this session."
        f"</div></div>",
        unsafe_allow_html=True,
    )

    _VAL_KEY = _wa_key(uploaded_name, "validation_result")
    existing = st.session_state.get(_VAL_KEY)

    btn_label = "🔄 Re-run Validation" if existing else "▶ Run Validation"
    run_col, _ = st.columns([2, 5])
    with run_col:
        run_clicked = st.button(btn_label, key=f"_wa_run_val_{uploaded_name}",
                                use_container_width=True)

    if run_clicked:
        if not fields:
            st.error("No extracted fields to validate.")
            return
        with st.spinner("Running validation…"):
            result = _run_word_validation(fields, doc_label, raw_text, uploaded_name)
        if result:
            st.session_state[_VAL_KEY] = result
            existing = result
            st.toast("✅ Validation complete!")
        else:
            st.error("Validation failed — LLM unavailable or returned invalid JSON.")
            return

    if not existing:
        st.markdown(
            f"<div style='background:{_BG2};border:1px solid {_BORDER};"
            f"border-radius:8px;padding:24px;text-align:center;"
            f"color:{_LBL};font-family:monospace;font-size:12px;'>"
            f"Click <strong>▶ Run Validation</strong> to start quality evaluation."
            f"</div>",
            unsafe_allow_html=True,
        )
        return

    overall    = existing.get("overall_validation", {})
    ov_score   = overall.get("score", 0)
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
        f"border-radius:3px;'></div></div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    dims = [
        ("extraction_accuracy", "🎯", "Extraction",  "#2563eb"),
        ("completeness",        "📋", "Completeness","#059669"),
        ("document_quality",    "⭐", "Quality",     "#7c3aed"),
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
    _render_val_dimension("🎯", "Extraction Accuracy",  existing.get("extraction_accuracy", {}), "#2563eb")
    _render_val_dimension("📋", "Completeness",         existing.get("completeness",         {}), "#059669")
    _render_val_dimension("⭐", "Document Quality",     existing.get("document_quality",     {}), "#7c3aed")

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

    _, clr_col = st.columns([5, 2])
    with clr_col:
        if st.button("🗑 Clear results", key=f"_wa_clr_val_{uploaded_name}",
                     use_container_width=True):
            st.session_state.pop(_VAL_KEY, None)
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def render_word_analysis_panel(
    word_result:   dict,
    uploaded_name: str,
    file_path:     str,
) -> None:
    """
    Render the full Word document analysis panel.

    Parameters
    ----------
    word_result   : output of modules.word_parser.parse_word()
    uploaded_name : display name of the uploaded file
    file_path     : absolute path to the .docx on disk (for source-context rendering)
    """
    _fp = (
        uploaded_name
        + "|" + str(len(word_result.get("fields", [])))
        + "|" + str(len(word_result.get("raw_text", "")))
    )
    _prev_fp = st.session_state.get("_wa_panel_fp")
    if _prev_fp != _fp:
        for _k in list(st.session_state.keys()):
            if _k.startswith(_wa_key(uploaded_name, "")):
                st.session_state.pop(_k, None)
        st.session_state["_wa_panel_fp"] = _fp

    clf       = word_result.get("doc_classification", {})
    doc_label = clf.get("doc_type_label", "General Document")
    doc_conf  = float(clf.get("confidence", 0.0))
    meta      = _DOC_TYPE_META.get(doc_label, _DOC_TYPE_META["General Document"])

    fields: list[dict] = list(word_result.get("fields", []))
    _extra_key = _wa_key(uploaded_name, "extra_fields")
    extra_fields = st.session_state.get(_extra_key, [])
    existing_names = {f.get("field_name", "") for f in fields}
    for ef in extra_fields:
        if ef.get("field_name") not in existing_names:
            fields.append(ef)

    raw_text   = word_result.get("raw_text", "")
    page_count = len([b for b in word_result.get("blocks", [])
                      if b.get("block_type") == "paragraph"])

    st.markdown(
        f"<div style='background:{meta['bg']};border:1px solid {meta['color']}30;"
        f"border-radius:10px;padding:13px 18px;margin-bottom:14px;'>"
        f"<div style='display:flex;align-items:center;gap:12px;'>"
        f"<span style='font-size:22px;'>{meta['icon']}</span>"
        f"<div>"
        f"<div style='font-size:14px;font-weight:700;color:{meta['color']};"
        f"font-family:monospace;text-transform:uppercase;letter-spacing:1.5px;'>"
        f"{doc_label}</div>"
        f"<div style='font-size:11px;color:{_LBL};margin-top:3px;'>"
        f"📄 {html.escape(uploaded_name)} · {len(fields)} field(s) extracted · "
        f"{len(raw_text.split())} words · Confidence: {_conf_badge(doc_conf)}"
        f"</div>"
        f"</div></div></div>",
        unsafe_allow_html=True,
    )

    _fields_count = len(fields)

    tabs = st.tabs([
        f"🔍 Fields ({_fields_count})",
        "📝 Summary",
        "📄 Raw JSON",
        "🔄 Transformation Journey",
        "✅ AI Assistant",
    ])

    with tabs[0]:
        _render_fields_tab(fields, word_result, uploaded_name, file_path)
    with tabs[1]:
        _render_summary_tab(word_result, fields, uploaded_name)
    with tabs[2]:
        _render_raw_json_tab(fields, word_result, uploaded_name)
    with tabs[3]:
        _render_journey_tab(fields, uploaded_name)
    with tabs[4]:
        _render_validation_tab(fields, word_result, uploaded_name)