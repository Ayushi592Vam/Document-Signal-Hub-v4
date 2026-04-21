"""
ui/topbar.py — light-theme version
Top navigation bar:
  LEFT   → Signal Hub LOGO
  CENTER → "Document Signal Hub" title + subtitle + schema badge
  RIGHT  → ValueMomentum badge logo
  FAR-R  → cache 🗑 + settings ⚙ buttons
"""

import streamlit as st
from modules.logo import logo_img_tag, LOGO_B64, LOGO_MIME, BADGE_LOGO_B64, BADGE_LOGO_MIME


# ── Signal Hub right-side badge ───────────────────────────────────────────────

def _signal_hub_badge_html() -> str:
    """Right badge — bare ValueMomentum logo, no box."""
    if BADGE_LOGO_B64:
        mime = BADGE_LOGO_MIME or "image/png"
        return (
            f'<img src="data:{mime};base64,{BADGE_LOGO_B64}" '
            f'style="height:44px;width:auto;display:inline-block;'
            f'vertical-align:middle;flex-shrink:0;" />'
        )
    return '<span style="font-size:20px;vertical-align:middle;"></span>'


def _schema_badge_html(active_schema: str | None, schemas: dict) -> str:
    if not active_schema or active_schema not in schemas:
        return ""
    sc = schemas[active_schema]
    return (
        f'<span style="'
        f'display:inline-flex;align-items:center;gap:6px;'
        f'border-radius:6px;padding:4px 14px;'
        f'font-size:12px;font-weight:700;font-family:monospace;'
        f'border:1px solid {sc["color"]}55;'
        f'color:{sc["color"]};background:{sc["color"]}12;'
        f'white-space:nowrap;letter-spacing:0.3px;margin-left:16px;">'
        f'{sc["icon"]} {active_schema} &nbsp;&middot;&nbsp; {sc["version"]}</span>'
    )


def render_topbar(schemas: dict, config_load_status: dict) -> bool:
    """
    Renders the top bar.
    Returns True if the settings gear was clicked (caller should open dialog).
    """
    active_schema = st.session_state.get("active_schema", None)
    _vm_logo      = logo_img_tag(height=48)
    _schema_badge = _schema_badge_html(active_schema, schemas)
    _sh_badge     = _signal_hub_badge_html()

    col_title, col_cache, col_gear = st.columns([10, 1, 1])

    with col_title:
        st.markdown(
            '<div style="'
            'display:flex;align-items:center;'
            'padding:8px 0 6px 0;min-height:60px;gap:0;'
            '">'

            # VM logo — left anchor
            + _vm_logo +

            # Title + subtitle
            '<div style="'
            'display:flex;flex-direction:column;'
            'justify-content:center;gap:2px;'
            'margin-left:8px;'
            '">'
            '<span style="'
            'font-size:17px;font-weight:700;color:#0f1117;'
            'font-family:\'Segoe UI\',\'Helvetica Neue\',Arial,sans-serif;'
            'letter-spacing:-0.3px;line-height:1.2;white-space:nowrap;'
            '">&nbsp;&nbsp;&nbsp;Document Signal Hub</span>'
            '<span style="'
            'font-size:12px;font-weight:400;color:#007BFF;'
            'font-family:\'JetBrains Mono\',\'Cascadia Code\',\'Consolas\',monospace;'
            'letter-spacing:0.5px;white-space:nowrap;'
            '"> &nbsp;  Turning Insurance Documents into Decision-Ready Signals </span>'
            '</div>'

            # Schema badge
            + (_schema_badge if _schema_badge else '') +

            # Flex spacer
            '<div style="flex:1;min-width:16px;"></div>'

            # Signal Hub badge — right anchor
            + _sh_badge +

            '</div>',
            unsafe_allow_html=True,
        )

    with col_cache:
        st.markdown("<div style='padding-top:16px;'>", unsafe_allow_html=True)
        cache_clicked = st.button(
            "🗑", key="open_cache_btn",
            help="Clear app cache",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_gear:
        st.markdown("<div style='padding-top:16px;'>", unsafe_allow_html=True)
        clicked = st.button(
            "⚙", key="open_settings",
            help="Settings",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Cache clear confirmation ──────────────────────────────────────────────
    if cache_clicked:
        st.session_state["_show_cache_confirm"] = True

    if st.session_state.get("_show_cache_confirm"):
        st.markdown(
            "<div style='background:#fff8f0;border:1px solid #e8c4a0;"
            "border-left:3px solid #d64040;border-radius:8px;"
            "padding:14px 18px;margin:6px 0 10px 0;'>"
            "<div style='font-size:14px;font-weight:700;color:#0f1117;"
            "margin-bottom:6px;'>Clear Caches</div>"
            "<div style='font-size:13px;color:#4a5578;margin-bottom:14px;'>"
            "This will clear parsed sheet data, file duplicate memory, "
            "claim duplicate history, and UI session state.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        _c1, _c2, _spacer = st.columns([1, 1, 5])
        with _c1:
            if st.button("Cancel", key="cache_cancel_btn", use_container_width=True):
                st.session_state["_show_cache_confirm"] = False
        with _c2:
            if st.button(
                "Clear caches", key="cache_confirm_btn",
                type="primary", use_container_width=True,
            ):
                from modules.cache_manager import (
                    clear_parsed_cache, clear_hash_store, clear_claim_dup_store,
                )
                clear_parsed_cache()
                clear_hash_store()
                clear_claim_dup_store()

                st.session_state["is_duplicate_file"]    = False
                st.session_state["duplicate_first_seen"] = None
                st.session_state["duplicate_orig_name"]  = None
                st.session_state["sheet_dup_info"]       = {
                    sn: None for sn in st.session_state.get("sheet_names", [])
                }
                st.session_state["current_file_hash"]    = ""
                st.session_state["last_uploaded"]        = None
                st.session_state["_show_cache_confirm"]  = False

                keys_to_keep = {
                    "tmpdir", "sheet_names", "sheet_cache",
                    "selected_idx", "focus_field",
                    "sheet_hashes",
                    "conf_threshold", "use_conf_threshold", "active_schema",
                    "schema_popup_target", "schema_popup_tab",
                    "claim_dup_migrated_v2",
                    "is_duplicate_file", "duplicate_first_seen",
                    "duplicate_orig_name", "sheet_dup_info",
                    "current_file_hash", "last_uploaded",
                }
                for k in [
                    key for key in list(st.session_state.keys())
                    if key not in keys_to_keep
                    and not key.startswith("custom_fields_")
                ]:
                    del st.session_state[k]

                st.toast("✅ Cache cleared — file will appear as new on next upload", icon="🗑")
                st.rerun()

    st.markdown(
        '<hr style="border:none;border-top:1px solid #d0d6e8;margin:2px 0 18px 0;">',
        unsafe_allow_html=True,
    )
    return clicked