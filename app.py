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
import base64
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

    # Check if we have results first - if yes, show them even if is_generating is True (might be stale)
    has_results = (
        st.session_state.get("generation_complete") or 
        bool(st.session_state.get("hmw_results"))
    )
    
    # Show loading state only if generating AND no results yet
    if st.session_state.get("is_generating") and not has_results:
        st.info("Generating ideas... This may take 30-60 seconds. Please be patient.")
        st.warning("If this takes longer than 2 minutes, click 'Cancel Generation' and try again.")
        # Show placeholder carousel during loading
        section_names = ["HMW Reframes", "Concept Sketches", "Layout Ideas"]
        render_loading_carousel(section_names)
        st.markdown("---")
        return  # Don't show results while loading
    
    # Show results with carousel navigation
    if has_results:
        # Clear is_generating flag if we have results (might be stale)
        if st.session_state.get("is_generating"):
            st.session_state["is_generating"] = False
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
                    if i < len(hmw_results):
                        st.markdown("---")
            else:
                st.info("No reframes generated yet.")
        
        elif current_section == 1:  # Concept Sketches
            st.subheader("Concept Sketches")
            image_urls = st.session_state.get("image_urls", [])
            if image_urls:
                for i, url in enumerate(image_urls, 1):
                    if url:
                        st.image(url, caption=f"Sketch {i}", width='stretch')
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
                    if i < len(layout_results):
                        st.markdown("---")
            else:
                st.info("Layout suggestions will appear here after generation.")
    else:
        # Placeholder state
        st.info("Enter a challenge above and click Generate to see results.")


def inject_custom_css() -> None:
    """Inject custom CSS for fonts and styling."""
    # Check if local font file exists
    font_path = Path(__file__).parent / "assets" / "fonts" / "NuosuSIL-Regular.ttf"
    
    # Build font declaration
    if font_path.exists():
        # Use local font file - encode to base64
        encoded_font = _encode_font_file(font_path)
        font_declaration = f"""@font-face {{
    font-family: 'Nuosu SIL';
    src: url('data:font/truetype;charset=utf-8;base64,{encoded_font}') format('truetype');
    font-weight: normal;
    font-style: normal;
}}"""
    else:
        # Fallback to web font
        font_declaration = "@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+Yi:wght@400;600;700&display=swap');"
    
    # Build CSS string - use regular string concatenation to avoid f-string issues
    css = f"""<style>
{font_declaration}

/* Apply Nuosu SIL font to headers */
h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stSubheader {{
    font-family: 'Nuosu SIL', 'Noto Serif Yi', 'Times New Roman', serif !important;
    color: #000000 !important;
    font-weight: 400 !important;
}}

/* Apply Helvetica to body text */
body, .stMarkdown, .stText, .stTextInput, .stTextArea, p, div, span, label {{
    font-family: 'Helvetica', 'Helvetica Neue', Arial, sans-serif !important;
    color: #000000 !important;
}}

/* Ensure white background */
.stApp {{
    background-color: #ffffff !important;
}}

/* Style main content area */
.main .block-container {{
    background-color: #ffffff !important;
    color: #000000 !important;
}}

/* Style sidebar */
.css-1d391kg, [data-testid="stSidebar"] {{
    background-color: #f8f9fa !important;
}}

/* Style buttons - make them readable with white text on black */
.stButton > button {{
    background-color: #000000 !important;
    color: #ffffff !important;
    border: 2px solid #000000 !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.5rem !important;
    border-radius: 4px !important;
    transition: all 0.2s ease !important;
}}

.stButton > button:hover {{
    background-color: #333333 !important;
    border-color: #333333 !important;
    color: #ffffff !important;
}}

.stButton > button:disabled {{
    background-color: #cccccc !important;
    color: #666666 !important;
    border-color: #cccccc !important;
    cursor: not-allowed !important;
}}

/* Style text inputs */
.stTextInput > div > div > input, .stTextArea > div > div > textarea {{
    background-color: #ffffff !important;
    color: #000000 !important;
    border: 1px solid #cccccc !important;
}}

.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {{
    border-color: #000000 !important;
    box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.1) !important;
}}
</style>"""
    st.markdown(css, unsafe_allow_html=True)


def _encode_font_file(font_path: Path) -> str:
    """Encode font file to base64 for embedding in CSS."""
    with open(font_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def main() -> None:
    """Main entry point."""
    inject_custom_css()
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
