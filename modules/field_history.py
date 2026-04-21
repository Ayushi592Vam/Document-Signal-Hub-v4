"""
modules/field_history.py
Per-field edit history stored in Streamlit session state.
"""

import datetime
import streamlit as st


def _record_field_history(sheet: str, claim_id: str, field: str, old_val: str, new_val: str) -> None:
    hk = f"_fhist_{sheet}_{claim_id}_{field}"
    if hk not in st.session_state:
        st.session_state[hk] = []
    st.session_state[hk].append({
        "ts":     datetime.datetime.now().strftime("%H:%M:%S"),
        "from":   old_val,
        "to":     new_val,
        "source": "user",
    })


def _get_field_history(sheet: str, claim_id: str, field: str) -> list:
    return st.session_state.get(f"_fhist_{sheet}_{claim_id}_{field}", [])
