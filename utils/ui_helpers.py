"""
UI helper utilities for Streamlit components.

Future responsibilities include:
    - Reusable card components for results
    - Copy-to-clipboard button builders
    - Loading skeleton helpers
"""

from __future__ import annotations

from typing import Iterable

import streamlit as st


def render_placeholder_list(items: Iterable[str], label: str) -> None:
    """Render a simple bullet list with a heading."""
    st.markdown(f"**{label}**")
    for item in items:
        st.write(f"• {item}")

