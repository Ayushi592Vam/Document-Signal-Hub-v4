"""
ui/nav_panel.py
Left-panel claim navigator: search box + scrollable claim cards.
Returns the newly selected index (or None if unchanged).
"""

import streamlit as st
from modules.schema_mapping import detect_claim_id, get_val


def render_nav_panel(data: list, selected_sheet: str) -> int | None:
    """
    Renders the claim list navigator inside a fixed-height container.
    Returns the index the user clicked, or None if nothing was clicked.
    """
    new_idx: int | None = None

    with st.container(height=700, border=False):
        st.markdown("<p class='section-lbl'>Claim Records</p>", unsafe_allow_html=True)

        _search_k = f"search_{selected_sheet}"
        _search_q = st.text_input(
            "",
            key=_search_k,
            placeholder="🔍 Filter claims…",
            label_visibility="collapsed",
        )
        _q_lower = _search_q.strip().lower()

        if _q_lower:
            _hit_indices = [
                i
                for i, row in enumerate(data)
                if any(
                    _q_lower in str(v.get("modified", v.get("value", ""))).lower()
                    for v in row.values()
                )
            ]
            st.markdown(
                f"<div style='font-size:var(--sz-xs);color:var(--green);"
                f"font-family:var(--mono);margin:3px 0 6px;'>"
                f"● {len(_hit_indices)} match{'es' if len(_hit_indices) != 1 else ''}</div>",
                unsafe_allow_html=True,
            )
        else:
            _hit_indices = list(range(len(data)))

        for i in _hit_indices:
            row_data = data[i]
            is_sel   = "selected-card" if st.session_state.selected_idx == i else ""
            c_id     = detect_claim_id(row_data, i)
            c_name   = get_val(
                row_data,
                [
                    "Insured Name", "Claimant Name", "Claimant", "Name",
                    "Company", "TPA_NAME", "insured", "claimant",
                    "injured party", "employee name", "driver name",
                ],
                "Unknown Entity",
            )
            raw_st   = get_val(
                row_data,
                ["Status", "Claim Status", "CLAIM_STATUS", "current status", "file status"],
                "",
            )
            c_status = raw_st or (
                "Yet to Review" if i == 0 else "In Progress" if i == 1 else "Submitted"
            )
            s_cls = (
                "status-progress"
                if "progress" in c_status.lower() or c_status.lower() == "open"
                else "status-text"
            )

            st.markdown(
                f"""<div class="claim-card {is_sel}">
                    <div style="font-weight:700;color:var(--t0);font-size:var(--sz-body);
                         font-family:var(--font-head);">{c_id}</div>
                    <div style="color:var(--t1);font-size:var(--sz-xs);margin-top:3px;
                         font-family:var(--font);">{c_name}</div>
                    <div class="{s_cls}">{c_status}</div>
                </div>""",
                unsafe_allow_html=True,
            )

            if st.button(
                "Select",
                key=f"sel_{selected_sheet}_{i}",
                use_container_width=True,
            ):
                new_idx = i

    return new_idx
