"""
Streamlit entry point for the Idea Generator for Designers.

Main app that orchestrates:
    - User input collection
    - OpenAI API calls (parallelized)
    - Real-time result streaming
    - Session persistence
    - Export functionality
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from utils.openai_helpers import generate_all
from utils.session_store import SessionStore
from utils.ui_helpers import create_export_text, format_hmw_for_display, format_layout_for_display

# Load environment variables
load_dotenv()

# Initialize session store
@st.cache_resource
def get_session_store():
    """Get cached session store instance."""
    return SessionStore()


def init_session_state() -> None:
    """Initialize keys used across the app to avoid KeyError."""
    defaults = {
        "challenge_text": "",
        "user_name": "",
        "user_email": "",
        "hmw_results": [],
        "sketch_results": [],
        "layout_results": [],
        "sketch_prompts": [],
        "image_urls": [],
        "is_generating": False,
        "error_message": "",
        "session_id": None,
        "generation_complete": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Generate session ID if not present
    if st.session_state["session_id"] is None:
        st.session_state["session_id"] = str(uuid.uuid4())


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
        
        if st.session_state.get("generation_complete"):
            st.markdown("---")
            st.subheader("Export")
            export_text = create_export_text(
                st.session_state["challenge_text"],
                st.session_state["hmw_results"],
                st.session_state["layout_results"],
                st.session_state.get("sketch_prompts"),
            )
            st.download_button(
                "Download Results (TXT)",
                export_text,
                file_name="idea_generator_results.txt",
                mime="text/plain",
            )
        
        st.markdown("---")
        st.caption("Tip: Be specific about your design challenge for better results.")


async def run_generation(challenge: str) -> None:
    """Run the full generation pipeline and update session state."""
    try:
        results = await generate_all(challenge)
        
        # Update session state
        st.session_state["hmw_results"] = results["hmw"]
        st.session_state["sketch_prompts"] = results["sketch_prompts"]
        st.session_state["layout_results"] = results["layouts"]
        st.session_state["image_urls"] = [img.get("url") for img in results["images"]]
        st.session_state["generation_complete"] = True
        st.session_state["error_message"] = ""
        
        # Persist to database
        store = get_session_store()
        session_id = st.session_state["session_id"]
        
        # Check if session exists, create if not
        existing_session = store.get_session(session_id)
        if not existing_session:
            store.create_session(
                session_id,
                challenge,
                st.session_state.get("user_name", ""),
                st.session_state.get("user_email", ""),
            )
        
        # Update session with results
        store.update_session(
            session_id,
            {
                "hmw_results": results["hmw"],
                "sketch_prompts": results["sketch_prompts"],
                "image_urls": [img.get("url") for img in results["images"]],
                "layout_results": results["layouts"],
            },
        )
    except Exception as e:
        error_msg = str(e)
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            st.session_state["error_message"] = (
                "Rate limit reached. Please wait a moment and try again."
            )
        elif "OPENAI_API_KEY" in error_msg:
            st.session_state["error_message"] = (
                "API key not configured. Please set OPENAI_API_KEY in your .env file."
            )
        else:
            st.session_state["error_message"] = f"Error: {error_msg}"
        st.session_state["is_generating"] = False
        st.session_state["generation_complete"] = False


def render_main() -> None:
    """Render the main UI layout."""
    st.title("Idea Generator for Designers")
    st.write("Turn a single design challenge into reframes, sketches, and layouts — in seconds.")

    st.markdown("### 1. Design Challenge")
    challenge = st.text_area(
        "What challenge are you solving?",
        key="challenge_text",
        height=120,
        placeholder="Improve the bus stop experience for commuters during winter storms.",
    )

    col_submit, col_reset = st.columns([2, 1], gap="small")
    with col_submit:
        generate_clicked = st.button(
            "Generate Concepts",
            type="primary",
            disabled=st.session_state["is_generating"] or not challenge.strip(),
        )
    with col_reset:
        if st.button("Reset"):
            for key in ["hmw_results", "sketch_results", "layout_results", "sketch_prompts", "image_urls", "generation_complete"]:
                st.session_state[key] = [] if isinstance(st.session_state.get(key), list) else False
            st.session_state["challenge_text"] = ""
            st.session_state["session_id"] = None
            init_session_state()
            st.rerun()

    # Handle generation
    if generate_clicked and challenge.strip() and not st.session_state["is_generating"]:
        st.session_state["is_generating"] = True
        st.session_state["generation_complete"] = False
        st.session_state["error_message"] = ""
        # Run async generation (blocks UI, which is acceptable for this use case)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_generation(challenge))
            loop.close()
        except Exception as e:
            st.session_state["error_message"] = f"Generation failed: {str(e)}"
        finally:
            st.session_state["is_generating"] = False
            st.rerun()

    st.markdown("---")
    st.markdown("### 2. Results Overview")

    # Show error if any
    if st.session_state.get("error_message"):
        st.error(st.session_state["error_message"])

    # Show loading state
    if st.session_state["is_generating"]:
        st.info("Generating ideas... This may take 30-60 seconds.")
        st.spinner("Working on it...")

    # Show results
    if st.session_state.get("generation_complete") or (
        st.session_state.get("hmw_results") and not st.session_state["is_generating"]
    ):
        col_hmw, col_sketch, col_layout = st.columns(3, gap="large")

        with col_hmw:
            st.subheader("HMW Reframes")
            hmw_results = st.session_state.get("hmw_results", [])
            if hmw_results:
                for i, stmt in enumerate(hmw_results, 1):
                    with st.container():
                        st.markdown(f"**{i}.** {stmt}")
                        st.code(stmt, language=None)
                # Copy all button - using code block for easy selection
                all_hmw = "\n".join(f"{i+1}. {stmt}" for i, stmt in enumerate(hmw_results))
                with st.expander("Copy All HMW Statements"):
                    st.code(all_hmw, language=None)
            else:
                st.info("No reframes generated yet.")

        with col_sketch:
            st.subheader("Concept Sketches")
            image_urls = st.session_state.get("image_urls", [])
            sketch_prompts = st.session_state.get("sketch_prompts", [])
            if image_urls:
                for i, (url, prompt) in enumerate(zip(image_urls, sketch_prompts), 1):
                    if url:
                        st.image(url, caption=f"Sketch {i}", width='stretch')
                        with st.expander(f"View prompt {i}"):
                            st.code(prompt, language=None)
                    else:
                        st.warning(f"Image {i} failed to generate")
            else:
                st.info("Sketches will appear here after generation.")

        with col_layout:
            st.subheader("Layout Ideas")
            layout_results = st.session_state.get("layout_results", [])
            if layout_results:
                for i, layout in enumerate(layout_results, 1):
                    with st.container():
                        title = layout.get("title", f"Layout {i}")
                        desc = layout.get("description", "")
                        st.markdown(f"**{i}. {title}**")
                        st.write(desc)
                        st.code(desc, language=None)
            else:
                st.info("Layout suggestions will appear here after generation.")
    else:
        # Placeholder state
        col_hmw, col_sketch, col_layout = st.columns(3, gap="large")
        with col_hmw:
            st.subheader("HMW Reframes")
            st.info("Enter a challenge above and click Generate.")
        with col_sketch:
            st.subheader("Concept Sketches")
            st.info("DALL·E images will appear here.")
        with col_layout:
            st.subheader("Layout Ideas")
            st.info("UI layout suggestions will render here.")


def main() -> None:
    """Main entry point."""
    init_session_state()
    render_sidebar()
    render_main()
    
    # Purge old sessions on startup (runs once per session)
    if "purged_sessions" not in st.session_state:
        try:
            store = get_session_store()
            deleted = store.purge_expired_sessions()
            if deleted > 0:
                st.session_state["purged_sessions"] = True
        except Exception:
            pass  # Fail silently on purge errors


if __name__ == "__main__":
    main()
