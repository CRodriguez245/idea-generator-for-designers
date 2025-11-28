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
    # Sidebar hidden - ResearchBridge style has everything at top
    pass


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
        '<p class="section-description">Turn a single design challenge into reframes, sketches, and layouts — in seconds.</p>',
        unsafe_allow_html=True
    )

    # Design Challenge Card - use JavaScript wrapper approach
    st.markdown(
        '<div class="section-card" id="card-design-challenge">',
        unsafe_allow_html=True
    )
    st.markdown("### Design Challenge")
    st.markdown(
        '<p class="section-description">Choose what you want to do. Enter your design challenge below to generate ideas.</p>',
        unsafe_allow_html=True
    )
    
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
    st.markdown('</div>', unsafe_allow_html=True)

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

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Results Overview Card - use JavaScript wrapper approach
    st.markdown(
        '<div class="section-card" id="card-results-overview">',
        unsafe_allow_html=True
    )
    st.markdown("### Results Overview")
    st.markdown(
        '<p class="section-description">Review the generated reframes, sketches, and layout ideas below.</p>',
        unsafe_allow_html=True
    )

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
        st.markdown('</div>', unsafe_allow_html=True)
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
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Display current section content - ResearchBridge style structure
        if current_section == 0:  # HMW Reframes
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            hmw_results = st.session_state.get("hmw_results", [])
            if hmw_results:
                st.markdown('<div class="result-heading">How Might We Statements:</div>', unsafe_allow_html=True)
                for i, stmt in enumerate(hmw_results, 1):
                    st.markdown(f'<div class="result-content"><strong>{i}.</strong> {stmt}</div>', unsafe_allow_html=True)
                    if i < len(hmw_results):
                        st.markdown("<div style='margin: 1.5rem 0; border-top: 1px solid #e0e0e0;'></div>", unsafe_allow_html=True)
            else:
                st.info("No reframes generated yet.")
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif current_section == 1:  # Concept Sketches
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.markdown('<div class="result-heading">Concept Sketches:</div>', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif current_section == 2:  # Layout Ideas
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.markdown('<div class="result-heading">Layout Ideas:</div>', unsafe_allow_html=True)
            layout_results = st.session_state.get("layout_results", [])
            if layout_results:
                for i, layout in enumerate(layout_results, 1):
                    title = layout.get("title", f"Layout {i}")
                    desc = layout.get("description", "")
                    st.markdown(f'<h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem;">{i}. {title}</h4>', unsafe_allow_html=True)
                    st.markdown(f'<div class="result-content">{desc}</div>', unsafe_allow_html=True)
                    if i < len(layout_results):
                        st.markdown("<div style='margin: 2rem 0; border-top: 1px solid #e0e0e0;'></div>", unsafe_allow_html=True)
            else:
                st.info("Layout suggestions will appear here after generation.")
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Placeholder state
        st.info("Enter a challenge above and click Generate to see results.")
    
    st.markdown('</div>', unsafe_allow_html=True)


def inject_custom_css() -> None:
    """Inject custom CSS matching ResearchBridge styling."""
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
    
    # ResearchBridge-inspired styling: clean, professional, blue accents
    css = f"""<style>
{font_declaration}

/* Base typography - Futura and Helvetica */
body {{
    font-family: 'Helvetica', 'Helvetica Neue', -apple-system, BlinkMacSystemFont, Arial, sans-serif !important;
    color: #1a1a1a !important;
    line-height: 1.6 !important;
}}

/* Headers - Futura font family */
h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
    font-family: 'Futura', 'Futura PT', 'Century Gothic', 'Trebuchet MS', 'Helvetica', Arial, sans-serif !important;
    color: #000000 !important;
    font-weight: 400 !important;
    margin-bottom: 0.5rem !important;
    margin-top: 0 !important;
    letter-spacing: -0.02em !important;
}}

h1, .stMarkdown h1 {{
    font-size: 2rem !important;
    margin-bottom: 0.25rem !important;
}}

h2, .stMarkdown h2 {{
    font-size: 1.5rem !important;
    margin-top: 2rem !important;
    margin-bottom: 0.5rem !important;
}}

h3, .stMarkdown h3 {{
    font-size: 1.25rem !important;
    margin-top: 1.5rem !important;
    margin-bottom: 0.5rem !important;
}}

h4, .stMarkdown h4 {{
    font-size: 1.1rem !important;
    font-weight: 400 !important;
    margin-top: 1.25rem !important;
    margin-bottom: 0.5rem !important;
}}

/* Body text - Helvetica */
.stMarkdown, .stText, p, div, span {{
    font-family: 'Helvetica', 'Helvetica Neue', -apple-system, BlinkMacSystemFont, Arial, sans-serif !important;
    color: #1a1a1a !important;
    line-height: 1.6 !important;
}}

/* White background */
.stApp {{
    background-color: #ffffff !important;
}}

/* Main content area */
.main .block-container {{
    background-color: #ffffff !important;
    color: #1a1a1a !important;
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1000px !important;
    margin-top: 1rem !important;
}}

/* Sidebar - light gray like ResearchBridge with depth */
[data-testid="stSidebar"] {{
    background-color: #f5f5f5 !important;
    border-right: 1px solid #e0e0e0 !important;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04) !important;
}}

[data-testid="stSidebar"] .stMarkdown {{
    color: #4a4a4a !important;
}}

/* Section descriptions - subtle gray text */
.section-description {{
    color: #666666 !important;
    font-size: 0.9375rem !important;
    margin-top: -0.5rem !important;
    margin-bottom: 1.5rem !important;
}}

/* Section card wrappers - ResearchBridge style cards */
/* Section cards - will be styled via JavaScript wrapping */
.section-card {{
    background-color: #ffffff !important;
    padding: 2rem 2.5rem !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08) !important;
    border: 2px solid #c0c0c0 !important;
    margin: 1.5rem 0 2rem 0 !important;
    display: block !important;
    width: 100% !important;
    box-sizing: border-box !important;
    position: relative !important;
    overflow: visible !important;
}}

.section-card h3,
.section-card .stMarkdown h3 {{
    margin-top: 0 !important;
    padding-top: 0 !important;
}}

/* Primary buttons - blue with depth and shadows */
.stButton > button[data-baseweb="button"][kind="primary"], 
.stButton > button:has-text("Generate"),
.stButton > button[type="primary"] {{
    background-color: #1976d2 !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 500 !important;
    padding: 0.625rem 1.5rem !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
    font-size: 0.9375rem !important;
    box-shadow: 0 2px 8px rgba(25, 118, 210, 0.25), 0 1px 3px rgba(0, 0, 0, 0.12) !important;
    font-family: 'Helvetica', 'Helvetica Neue', Arial, sans-serif !important;
}}

.stButton > button[data-baseweb="button"][kind="primary"]:hover,
.stButton > button:has-text("Generate"):hover,
.stButton > button[type="primary"]:hover {{
    background-color: #1565c0 !important;
    box-shadow: 0 4px 12px rgba(25, 118, 210, 0.35), 0 2px 6px rgba(0, 0, 0, 0.15) !important;
    transform: translateY(-1px) !important;
}}

.stButton > button[data-baseweb="button"][kind="primary"]:active,
.stButton > button:has-text("Generate"):active,
.stButton > button[type="primary"]:active {{
    transform: translateY(0) !important;
    box-shadow: 0 2px 6px rgba(25, 118, 210, 0.25), 0 1px 2px rgba(0, 0, 0, 0.12) !important;
}}

/* Secondary buttons - outline style with depth */
.stButton > button[kind="secondary"],
.stButton > button:not([kind="primary"]):not([type="primary"]) {{
    background-color: #ffffff !important;
    color: #1976d2 !important;
    border: 1px solid #1976d2 !important;
    font-weight: 500 !important;
    padding: 0.625rem 1.5rem !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06) !important;
    font-family: 'Helvetica', 'Helvetica Neue', Arial, sans-serif !important;
}}

.stButton > button[kind="secondary"]:hover,
.stButton > button:not([kind="primary"]):not([type="primary"]):hover {{
    background-color: #e3f2fd !important;
    border-color: #1565c0 !important;
    color: #1565c0 !important;
    box-shadow: 0 2px 8px rgba(25, 118, 210, 0.15), 0 2px 4px rgba(0, 0, 0, 0.1) !important;
    transform: translateY(-1px) !important;
}}

.stButton > button[kind="secondary"]:active,
.stButton > button:not([kind="primary"]):not([type="primary"]):active {{
    transform: translateY(0) !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08) !important;
}}

/* Disabled buttons */
.stButton > button:disabled {{
    background-color: #e0e0e0 !important;
    color: #9e9e9e !important;
    border-color: #e0e0e0 !important;
    cursor: not-allowed !important;
    opacity: 0.6 !important;
}}

/* Text inputs - clean borders with depth */
.stTextInput > div > div > input, .stTextArea > div > div > textarea {{
    background-color: #ffffff !important;
    color: #1a1a1a !important;
    border: 1px solid #bdbdbd !important;
    border-radius: 6px !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.9375rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), inset 0 1px 2px rgba(0, 0, 0, 0.02) !important;
    font-family: 'Helvetica', 'Helvetica Neue', Arial, sans-serif !important;
}}

.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {{
    border-color: #1976d2 !important;
    box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.1), 0 2px 6px rgba(0, 0, 0, 0.08) !important;
    outline: none !important;
}}

.stTextArea > div > div > textarea {{
    min-height: 100px !important;
    line-height: 1.6 !important;
}}

/* Labels - Helvetica */
label {{
    font-size: 0.875rem !important;
    color: #424242 !important;
    font-weight: 500 !important;
    margin-bottom: 0.5rem !important;
    font-family: 'Helvetica', 'Helvetica Neue', Arial, sans-serif !important;
}}

/* Hide sidebar completely - ResearchBridge has everything at top */
section[data-testid="stSidebar"],
.css-1d391kg,
.css-1lcbmhc,
[data-testid="stSidebar"] {{
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    min-width: 0 !important;
}}

/* Make main content full width */
.block-container,
.main .block-container {{
    max-width: 100% !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}}

/* Remove ALL dividers completely - aggressive removal */
hr,
hr[style],
.stMarkdown hr,
.stMarkdown > hr,
[data-testid="stHorizontalBlock"] hr,
.element-container hr,
div[data-testid="stHorizontalBlock"] hr,
div[data-testid*="stHorizontalBlock"] hr,
.block-container hr,
.main hr,
[class*="block-container"] hr,
div:has(> hr),
div hr,
* hr,
* > hr {{
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    opacity: 0 !important;
    position: absolute !important;
    width: 0 !important;
    overflow: hidden !important;
    clip: rect(0, 0, 0, 0) !important;
}}

/* Info/Warning/Error messages - with depth */
.stInfo {{
    background-color: #e3f2fd !important;
    border-left: 4px solid #1976d2 !important;
    color: #1a1a1a !important;
    padding: 1rem 1.25rem !important;
    border-radius: 6px !important;
    box-shadow: 0 2px 6px rgba(25, 118, 210, 0.12), 0 1px 3px rgba(0, 0, 0, 0.06) !important;
}}

.stError {{
    background-color: #ffebee !important;
    border-left: 4px solid #d32f2f !important;
    color: #1a1a1a !important;
    padding: 1rem 1.25rem !important;
    border-radius: 6px !important;
    box-shadow: 0 2px 6px rgba(211, 47, 47, 0.12), 0 1px 3px rgba(0, 0, 0, 0.06) !important;
}}

.stWarning {{
    background-color: #fff3e0 !important;
    border-left: 4px solid #f57c00 !important;
    color: #1a1a1a !important;
    padding: 1rem 1.25rem !important;
    border-radius: 6px !important;
    box-shadow: 0 2px 6px rgba(245, 124, 0, 0.12), 0 1px 3px rgba(0, 0, 0, 0.06) !important;
}}

/* Result sections - structured like ResearchBridge with depth */
.result-section {{
    margin-top: 2rem !important;
    margin-bottom: 2rem !important;
    background-color: #ffffff !important;
    padding: 1.5rem !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    border: 1px solid #f0f0f0 !important;
}}

.result-heading {{
    font-size: 1rem !important;
    font-weight: 400 !important;
    color: #000000 !important;
    margin-top: 0 !important;
    margin-bottom: 0.75rem !important;
    font-family: 'Futura', 'Futura PT', 'Century Gothic', 'Helvetica', Arial, sans-serif !important;
    letter-spacing: -0.01em !important;
}}

.result-content {{
    color: #1a1a1a !important;
    line-height: 1.7 !important;
    margin-bottom: 1rem !important;
    font-family: 'Helvetica', 'Helvetica Neue', Arial, sans-serif !important;
}}

/* Images - enhanced depth */
.stImage > img {{
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12), 0 2px 6px rgba(0, 0, 0, 0.08) !important;
    margin: 1rem 0 !important;
    border: 1px solid #f0f0f0 !important;
}}

.stImage > div {{
    font-size: 0.875rem !important;
    color: #666666 !important;
    margin-top: 0.5rem !important;
    font-style: italic !important;
}}

/* Lists */
.stMarkdown ul, .stMarkdown ol {{
    margin: 1rem 0 !important;
    padding-left: 1.5rem !important;
}}

.stMarkdown li {{
    margin: 0.5rem 0 !important;
    line-height: 1.7 !important;
}}

/* Caption styling */
.stCaption {{
    color: #666666 !important;
    font-size: 0.875rem !important;
    line-height: 1.5 !important;
}}

/* Button groups - for mode selection style */
.button-group {{
    display: flex !important;
    gap: 0.75rem !important;
    margin-top: 1rem !important;
    margin-bottom: 1.5rem !important;
}}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0.5rem !important;
    border-bottom: 1px solid #e0e0e0 !important;
}}

.stTabs [data-baseweb="tab"] {{
    color: #666666 !important;
    padding: 0.75rem 1.5rem !important;
    font-weight: 500 !important;
}}

.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: #1976d2 !important;
    border-bottom: 2px solid #1976d2 !important;
}}
</style>"""
    st.markdown(css, unsafe_allow_html=True)
    
    # Inject JavaScript to remove dividers and wrap sections in cards
    st.markdown("""
    <script>
    (function() {
        function removeAllDividers() {
            // Remove ALL hr elements aggressively
            document.querySelectorAll('hr, * hr, * > hr').forEach(function(hr) {
                hr.style.display = 'none';
                hr.style.visibility = 'hidden';
                hr.style.height = '0';
                hr.style.margin = '0';
                hr.style.padding = '0';
                hr.style.border = 'none';
                hr.remove();
            });
            // Remove any horizontal rules created by markdown
            document.querySelectorAll('.stMarkdown hr, [class*="hr"], [data-testid*="horizontal"]').forEach(function(hr) {
                hr.remove();
            });
            // Remove Streamlit's divider elements
            document.querySelectorAll('[class*="divider"], [class*="separator"], [data-testid*="horizontal"]').forEach(function(div) {
                if (div.tagName === 'HR' || div.querySelector('hr')) {
                    div.remove();
                }
            });
        }
        
        function wrapSectionCards() {
            const designCard = document.getElementById('card-design-challenge');
            const resultsCard = document.getElementById('card-results-overview');
            
            [designCard, resultsCard].forEach(function(card) {
                if (!card || card.dataset.wrapped) return;
                
                let next = card.nextElementSibling;
                const elementsToMove = [];
                const stopAt = card === designCard ? 'card-results-overview' : null;
                
                while (next && (!stopAt || next.id !== stopAt)) {
                    if (next.nodeType === 1 && next.id !== 'card-results-overview') {
                        if (next.classList.contains('element-container') || 
                            next.hasAttribute('data-testid') || 
                            (next.tagName === 'DIV' && !next.classList.contains('section-card'))) {
                            elementsToMove.push(next);
                        }
                    }
                    const temp = next.nextElementSibling;
                    if (next.id === stopAt) break;
                    next = temp;
                }
                
                elementsToMove.forEach(function(el) {
                    card.appendChild(el);
                });
                
                card.dataset.wrapped = 'true';
            });
        }
        
        function init() {
            removeAllDividers();
            wrapSectionCards();
        }
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
        
        const observer = new MutationObserver(function() {
            removeAllDividers();
            wrapSectionCards();
        });
        
        observer.observe(document.body, { childList: true, subtree: true });
        
        setTimeout(init, 100);
        setTimeout(init, 500);
        setTimeout(init, 1500);
    })();
    </script>
    """, unsafe_allow_html=True)


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
