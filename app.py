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
        st.markdown(
            "<p style='font-size: 0.8125rem; color: #666666; line-height: 1.5; margin-top: -0.5rem; margin-bottom: 2rem;'>"
            "Rapid ideation assistant for designers. "
            "Provide a design challenge to generate reframes, sketches, and layouts."
            "</p>",
            unsafe_allow_html=True
        )
        st.markdown("---")
        st.markdown("#### Session")
        st.text_input("Name (optional)", key="user_name", placeholder="Name (optional)")
        st.text_input("Email (optional)", key="user_email", placeholder="Email (optional)")
        
        if st.session_state.get("generation_complete"):
            st.markdown("---")
            st.markdown("#### Export")
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
                use_container_width=True
            )
        
        st.markdown("---")
        st.markdown(
            "<p style='font-size: 0.8125rem; color: #666666; line-height: 1.5; font-style: italic;'>"
            "Tip: Be specific about your design challenge for better results."
            "</p>",
            unsafe_allow_html=True
        )


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
    st.markdown(
        "<p style='font-size: 1rem; color: #666666; margin-top: -0.5rem; margin-bottom: 2.5rem;'>"
        "Turn a single design challenge into reframes, sketches, and layouts — in seconds."
        "</p>",
        unsafe_allow_html=True
    )

    st.markdown("### 1. Design Challenge")
    challenge = st.text_area(
        "What challenge are you solving?",
        key="challenge_text",
        height=120,
        placeholder="Improve the bus stop experience for commuters during winter storms.",
        help="Be specific about the problem, context, and users you're designing for."
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
        st.markdown("<br>", unsafe_allow_html=True)

    # Check if we have results first - if yes, show them even if is_generating is True (might be stale)
    has_results = (
        st.session_state.get("generation_complete") or 
        bool(st.session_state.get("hmw_results"))
    )
    
    # Show loading state only if generating AND no results yet
    if st.session_state.get("is_generating") and not has_results:
        st.info("Generating ideas... This may take 30-60 seconds. Please be patient.")
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
            hmw_results = st.session_state.get("hmw_results", [])
            if hmw_results:
                for i, stmt in enumerate(hmw_results, 1):
                    st.markdown(f"<p style='margin: 1.5rem 0; line-height: 1.7;'><strong>{i}.</strong> {stmt}</p>", unsafe_allow_html=True)
                    if i < len(hmw_results):
                        st.markdown("<div style='border-top: 1px solid #e8e8e8; margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
            else:
                st.info("No reframes generated yet.")
        
        elif current_section == 1:  # Concept Sketches
            image_urls = st.session_state.get("image_urls", [])
            if image_urls:
                for i, url in enumerate(image_urls, 1):
                    if url:
                        st.image(url, caption=f"Sketch {i}", width='stretch')
                        if i < len(image_urls):
                            st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)
                    else:
                        st.warning(f"Image {i} failed to generate")
            else:
                st.info("Sketches will appear here after generation.")
        
        elif current_section == 2:  # Layout Ideas
            layout_results = st.session_state.get("layout_results", [])
            if layout_results:
                for i, layout in enumerate(layout_results, 1):
                    title = layout.get("title", f"Layout {i}")
                    desc = layout.get("description", "")
                    st.markdown(f"<h4 style='margin-top: 2rem; margin-bottom: 0.75rem;'>{i}. {title}</h4>", unsafe_allow_html=True)
                    st.markdown(f"<p style='line-height: 1.7; color: #4a4a4a;'>{desc}</p>", unsafe_allow_html=True)
                    if i < len(layout_results):
                        st.markdown("<div style='border-top: 1px solid #e8e8e8; margin: 2rem 0;'></div>", unsafe_allow_html=True)
            else:
                st.info("Layout suggestions will appear here after generation.")
    else:
        # Placeholder state
        st.markdown("<br>", unsafe_allow_html=True)
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

/* Base typography */
body {{
    font-family: 'Helvetica', 'Helvetica Neue', Arial, sans-serif !important;
    color: #1a1a1a !important;
    line-height: 1.6 !important;
    letter-spacing: -0.01em !important;
}}

/* Apply Nuosu SIL font to headers */
h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stSubheader {{
    font-family: 'Nuosu SIL', 'Noto Serif Yi', 'Times New Roman', serif !important;
    color: #000000 !important;
    font-weight: 400 !important;
    letter-spacing: -0.02em !important;
    line-height: 1.3 !important;
}}

h1 {{
    font-size: 2.25rem !important;
    margin-bottom: 0.5rem !important;
    margin-top: 0 !important;
}}

h2, .stMarkdown h2 {{
    font-size: 1.75rem !important;
    margin-top: 2rem !important;
    margin-bottom: 1rem !important;
}}

h3, .stMarkdown h3 {{
    font-size: 1.25rem !important;
    margin-top: 1.5rem !important;
    margin-bottom: 0.75rem !important;
    font-weight: 400 !important;
}}

/* Apply Helvetica to body text */
.stMarkdown, .stText, p, div, span, label {{
    font-family: 'Helvetica', 'Helvetica Neue', Arial, sans-serif !important;
    color: #1a1a1a !important;
    line-height: 1.6 !important;
}}

.stTextInput > div > div > input, .stTextArea > div > div > textarea {{
    font-family: 'Helvetica', 'Helvetica Neue', Arial, sans-serif !important;
}}

/* Ensure white background */
.stApp {{
    background-color: #ffffff !important;
}}

/* Style main content area */
.main .block-container {{
    background-color: #ffffff !important;
    color: #1a1a1a !important;
    padding-top: 3rem !important;
    padding-bottom: 4rem !important;
    max-width: 900px !important;
}}

/* Style sidebar */
.css-1d391kg, [data-testid="stSidebar"] {{
    background-color: #fafafa !important;
    border-right: 1px solid #e8e8e8 !important;
}}

[data-testid="stSidebar"] .stMarkdown {{
    color: #4a4a4a !important;
}}

/* Subtle dividers */
hr {{
    border: none !important;
    border-top: 1px solid #e8e8e8 !important;
    margin: 2rem 0 !important;
}}

.stMarkdown hr {{
    border-top: 1px solid #e8e8e8 !important;
    margin: 2.5rem 0 !important;
}}

/* Style buttons - subtle and refined */
.stButton > button {{
    background-color: #000000 !important;
    color: #ffffff !important;
    border: 1px solid #000000 !important;
    font-weight: 400 !important;
    font-size: 0.9375rem !important;
    padding: 0.625rem 1.75rem !important;
    border-radius: 2px !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.01em !important;
    box-shadow: none !important;
}}

.stButton > button:hover {{
    background-color: #1a1a1a !important;
    border-color: #1a1a1a !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
    transform: translateY(-1px) !important;
}}

.stButton > button:active {{
    transform: translateY(0) !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06) !important;
}}

.stButton > button:disabled {{
    background-color: #f0f0f0 !important;
    color: #999999 !important;
    border-color: #e0e0e0 !important;
    cursor: not-allowed !important;
    opacity: 0.6 !important;
}}

/* Style text inputs - subtle borders */
.stTextInput > div > div > input, .stTextArea > div > div > textarea {{
    background-color: #ffffff !important;
    color: #1a1a1a !important;
    border: 1px solid #d0d0d0 !important;
    border-radius: 2px !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.9375rem !important;
    line-height: 1.5 !important;
    transition: all 0.2s ease !important;
}}

.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {{
    border-color: #666666 !important;
    box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.04) !important;
    outline: none !important;
}}

.stTextArea > div > div > textarea {{
    min-height: 120px !important;
}}

/* Improve spacing for labels */
label {{
    font-size: 0.875rem !important;
    color: #4a4a4a !important;
    font-weight: 400 !important;
    margin-bottom: 0.5rem !important;
    letter-spacing: 0.01em !important;
}}

/* Info and error messages - subtle styling */
.stInfo, .stSuccess, .stWarning, .stError {{
    border-radius: 2px !important;
    border-left: 3px solid !important;
    padding: 1rem 1.25rem !important;
    font-size: 0.9375rem !important;
    line-height: 1.6 !important;
}}

.stInfo {{
    background-color: #f8f9fa !important;
    border-left-color: #666666 !important;
    color: #4a4a4a !important;
}}

.stError {{
    background-color: #fafafa !important;
    border-left-color: #d32f2f !important;
    color: #4a4a4a !important;
}}

.stWarning {{
    background-color: #fafafa !important;
    border-left-color: #ff9800 !important;
    color: #4a4a4a !important;
}}

/* Image styling */
.stImage > img {{
    border-radius: 2px !important;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04) !important;
    margin: 1rem 0 !important;
}}

/* Caption styling */
.stImage > div {{
    font-size: 0.8125rem !important;
    color: #666666 !important;
    margin-top: 0.5rem !important;
    font-style: italic !important;
}}

/* List styling */
.stMarkdown ul, .stMarkdown ol {{
    margin: 1rem 0 !important;
    padding-left: 1.5rem !important;
}}

.stMarkdown li {{
    margin: 0.5rem 0 !important;
    line-height: 1.6 !important;
}}

/* Better spacing for results sections */
.stMarkdown p {{
    margin: 1rem 0 !important;
}}

/* Sidebar improvements */
[data-testid="stSidebar"] .stMarkdown h1 {{
    font-size: 1.5rem !important;
    margin-bottom: 0.25rem !important;
}}

[data-testid="stSidebar"] .stMarkdown .stCaption {{
    color: #666666 !important;
    font-size: 0.8125rem !important;
    line-height: 1.5 !important;
}}

[data-testid="stSidebar"] hr {{
    margin: 1.5rem 0 !important;
}}

/* Carousel navigation - subtle styling */
button[kind="secondary"] {{
    background-color: transparent !important;
    color: #1a1a1a !important;
    border: 1px solid #d0d0d0 !important;
    font-weight: 400 !important;
}}

button[kind="secondary"]:hover:not(:disabled) {{
    background-color: #f8f8f8 !important;
    border-color: #999999 !important;
    color: #000000 !important;
}}

button[kind="secondary"]:disabled {{
    opacity: 0.4 !important;
    cursor: not-allowed !important;
}}

/* Improve spacing between sections */
.element-container {{
    margin-bottom: 1.5rem !important;
}}

/* Subtle link styling */
.stMarkdown a {{
    color: #1a1a1a !important;
    text-decoration: underline !important;
    text-decoration-color: #999999 !important;
    text-underline-offset: 2px !important;
    transition: all 0.2s ease !important;
}}

.stMarkdown a:hover {{
    color: #000000 !important;
    text-decoration-color: #000000 !important;
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
