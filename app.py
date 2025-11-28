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
from utils.ui_helpers import create_export_text, format_hmw_for_display, format_layout_for_display, render_visual_carousel, render_loading_carousel

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
        "current_section": 0,  # 0=HMW, 1=Sketches, 2=Layouts
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
        # Clear any previous errors
        st.session_state["error_message"] = ""
        
        results = await generate_all(challenge)
        
        # Update session state
        st.session_state["hmw_results"] = results["hmw"]
        st.session_state["sketch_prompts"] = results["sketch_prompts"]
        st.session_state["layout_results"] = results["layouts"]
        st.session_state["image_urls"] = [img.get("url") for img in results["images"]]
        st.session_state["generation_complete"] = True
        st.session_state["is_generating"] = False  # Clear generating flag on success
        st.session_state["error_message"] = ""
        
        # Persist to database
        try:
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
        except Exception as db_error:
            # Don't fail generation if database save fails
            print(f"Warning: Failed to save to database: {db_error}")
        
    except Exception as e:
        error_msg = str(e)
        import traceback
        print(f"Generation error: {error_msg}")
        print(traceback.format_exc())
        
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            st.session_state["error_message"] = (
                "Rate limit reached. Please wait a moment and try again."
            )
        elif "OPENAI_API_KEY" in error_msg or "API key" in error_msg:
            st.session_state["error_message"] = (
                "API key not configured. Please set OPENAI_API_KEY in your .env file."
            )
        else:
            st.session_state["error_message"] = f"Error: {error_msg}"
        st.session_state["is_generating"] = False
        st.session_state["generation_complete"] = False
        raise  # Re-raise to be caught by outer handler


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
            # Clear all state including generation flags
            for key in ["hmw_results", "sketch_results", "layout_results", "sketch_prompts", "image_urls", "generation_complete", "is_generating", "error_message", "current_section"]:
                if key in st.session_state:
                    st.session_state[key] = [] if isinstance(st.session_state[key], list) else False
            # Don't modify challenge_text directly - it's bound to a widget
            # User can clear it manually or we use a separate reset mechanism
            st.session_state["session_id"] = None
            st.rerun()
    
    # Add a force reset button if stuck in generating state
    if st.session_state.get("is_generating"):
        if st.button("Cancel Generation", key="cancel_gen"):
            st.session_state["is_generating"] = False
            st.session_state["generation_complete"] = False
            st.session_state["error_message"] = "Generation was cancelled."
            st.rerun()

    # Handle generation
    if generate_clicked and challenge.strip() and not st.session_state["is_generating"]:
        st.session_state["is_generating"] = True
        st.session_state["generation_complete"] = False
        st.session_state["error_message"] = ""
        
        # Run async generation (blocks UI, which is acceptable for this use case)
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_generation(challenge))
        except Exception as e:
            error_msg = str(e)
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                st.session_state["error_message"] = "Rate limit reached. Please wait a moment and try again."
            elif "OPENAI_API_KEY" in error_msg:
                st.session_state["error_message"] = "API key not configured. Please set OPENAI_API_KEY in your .env file."
            else:
                st.session_state["error_message"] = f"Generation failed: {error_msg}"
            st.session_state["is_generating"] = False
            st.session_state["generation_complete"] = False
        finally:
            if loop:
                try:
                    loop.close()
                except Exception:
                    pass
            # Ensure is_generating is cleared if generation completed successfully
            if st.session_state.get("generation_complete"):
                st.session_state["is_generating"] = False
            # Always rerun to update UI
            st.rerun()

    st.markdown("---")
    st.markdown("### 2. Results Overview")

    # Show error if any
    if st.session_state.get("error_message"):
        st.error(st.session_state["error_message"])

    # Show loading state with placeholder carousel
    if st.session_state.get("is_generating") and not st.session_state.get("generation_complete"):
        st.info("Generating ideas... This may take 30-60 seconds. Please be patient.")
        st.warning("If this takes longer than 2 minutes, click 'Cancel Generation' and try again.")
        # Show placeholder carousel during loading
        section_names = ["HMW Reframes", "Concept Sketches", "Layout Ideas"]
        render_loading_carousel(section_names)
        st.markdown("---")
        return  # Don't show results while loading

    # Show results with carousel navigation (if generation is complete OR we have results and not generating)
    has_results = (
        st.session_state.get("generation_complete") or 
        (st.session_state.get("hmw_results") and not st.session_state.get("is_generating"))
    )
    
    if has_results:
        # Navigation for three sections
        section_names = ["HMW Reframes", "Concept Sketches", "Layout Ideas"]
        current_section = st.session_state.get("current_section", 0)
        
        # Prepare preview data for carousel
        preview_data = {
            "hmw_results": st.session_state.get("hmw_results", []),
            "image_urls": st.session_state.get("image_urls", []),
            "layout_results": st.session_state.get("layout_results", []),
        }
        
        # Render visual carousel with previews
        new_section = render_visual_carousel(section_names, current_section, "section_nav", preview_data)
        if new_section != current_section:
            st.session_state["current_section"] = new_section
            st.rerun()
        
        st.markdown("---")
        
        # Display current section content
        if current_section == 0:  # HMW Reframes
            st.subheader("HMW Reframes")
            hmw_results = st.session_state.get("hmw_results", [])
            if hmw_results:
                for i, stmt in enumerate(hmw_results, 1):
                    st.markdown(f"**{i}.** {stmt}")
                    st.code(stmt, language=None)
                    if i < len(hmw_results):
                        st.markdown("---")
                # Copy all button - using code block for easy selection
                all_hmw = "\n".join(f"{i+1}. {stmt}" for i, stmt in enumerate(hmw_results))
                with st.expander("Copy All HMW Statements"):
                    st.code(all_hmw, language=None)
            else:
                st.info("No reframes generated yet.")
        
        elif current_section == 1:  # Concept Sketches
            st.subheader("Concept Sketches")
            image_urls = st.session_state.get("image_urls", [])
            sketch_prompts = st.session_state.get("sketch_prompts", [])
            if image_urls:
                for i, (url, prompt) in enumerate(zip(image_urls, sketch_prompts), 1):
                    if url:
                        st.image(url, caption=f"Sketch {i}", width='stretch')
                        with st.expander(f"View prompt {i}"):
                            st.code(prompt, language=None)
                        if i < len(image_urls):
                            st.markdown("---")
                    else:
                        st.warning(f"Image {i} failed to generate")
            else:
                st.info("Sketches will appear here after generation.")
        
        elif current_section == 2:  # Layout Ideas
            st.subheader("Layout Ideas")
            layout_results = st.session_state.get("layout_results", [])
            if layout_results:
                for i, layout in enumerate(layout_results, 1):
                    title = layout.get("title", f"Layout {i}")
                    desc = layout.get("description", "")
                    st.markdown(f"**{i}. {title}**")
                    st.write(desc)
                    with st.expander(f"View full description {i}"):
                        st.code(desc, language=None)
                    if i < len(layout_results):
                        st.markdown("---")
            else:
                st.info("Layout suggestions will appear here after generation.")
    else:
        # Placeholder state
        st.info("Enter a challenge above and click Generate to see results.")


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
