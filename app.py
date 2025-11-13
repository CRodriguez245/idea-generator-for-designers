"""
Streamlit entry point for the Idea Generator for Designers.

This skeleton establishes the primary layout regions and placeholders for:
    - Problem input form
    - Loading indicators
    - Output columns for reframes, sketches, and layout suggestions

Implementation to follow plan.md Phase 1 deliverables.
"""

from __future__ import annotations

import streamlit as st


def init_session_state() -> None:
    """Initialize keys used across the app to avoid KeyError."""
    defaults = {
        "challenge_text": "",
        "user_name": "",
        "user_email": "",
        "hmw_results": [],
        "sketch_results": [],
        "layout_results": [],
        "is_generating": False,
        "error_message": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar() -> None:
    """Render sidebar controls and contextual info."""
    with st.sidebar:
        st.title("Idea Generator")
        st.caption(
            "Rapid ideation assistant for designers. "
            "Provide a design challenge to generate reframes, sketches, and layouts."
        )
        st.markdown("---")
        st.subheader("Session")
        st.text_input("Name (optional)", key="user_name")
        st.text_input("Email (optional)", key="user_email")
        st.markdown(
            "> ⚠️ Prototype: results are stored locally and may be cleared as the app evolves."
        )
        st.markdown("---")
        st.write("Next up:")
        st.markdown(
            "- Integrate OpenAI helpers\n"
            "- Stream results in real-time\n"
            "- Persist sessions via SQLite"
        )


def render_main() -> None:
    """Render the main UI layout with placeholders."""
    st.title("💡 Idea Generator for Designers")
    st.write("Turn a single design challenge into reframes, sketches, and layouts.")

    st.markdown("### 1. Design Challenge")
    st.text_area(
        "What challenge are you solving?",
        key="challenge_text",
        height=120,
        placeholder="Improve the bus stop experience for commuters during winter storms.",
    )
    col_submit, col_reset = st.columns([2, 1], gap="small")
    with col_submit:
        st.button("Generate Concepts", type="primary", disabled=True)
    with col_reset:
        st.button("Reset", disabled=True)

    st.markdown("---")
    st.markdown("### 2. Results Overview")

    if st.session_state.get("error_message"):
        st.error(st.session_state["error_message"])

    col_hmw, col_sketch, col_layout = st.columns(3, gap="large")

    with col_hmw:
        st.subheader("HMW Reframes")
        st.info("Generation pipeline not connected yet.")
        for _ in range(3):
            st.write("• Placeholder reframe")

    with col_sketch:
        st.subheader("Concept Sketches")
        st.info("DALL·E images will appear here.")
        for idx in range(1, 4):
            st.image(
                "https://placehold.co/200x120?text=Sketch+%d" % idx,
                caption=f"Sketch concept {idx}",
                use_column_width=True,
            )

    with col_layout:
        st.subheader("Layout Ideas")
        st.info("UI layout suggestions will render here.")
        for idx in range(1, 4):
            st.markdown(f"**Layout concept {idx}**")
            st.write("Placeholder layout description.")


def main() -> None:
    init_session_state()
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()

