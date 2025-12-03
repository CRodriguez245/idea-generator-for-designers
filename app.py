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
        "hmw_results": {},  # Dict[str, List[str]] - thematically organized
        "feature_ideas": {},  # Dict[str, List[Dict[str, str]]] - thematically organized
        "user_context": [],  # List[Dict[str, Any]] - user segments with personas and scenarios
        "sketch_results": [],
        "layout_results": {},  # Dict[str, List[Dict[str, str]]] - thematically organized
        "sketch_prompts": [],
        "sketch_concepts": [],  # Conceptual explanations for each sketch
        "image_urls": [],
        "is_generating": False,
        "error_message": "",
        "session_id": None,
        "generation_complete": False,
        "history_stack": [],  # Stack of previous states for back navigation
        "current_refinement": None,  # Currently selected idea being refined
        "original_challenge": "",  # Original challenge text
        "selected_ideas": [],  # List of selected ideas to build upon
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


def save_state_to_history() -> None:
    """Save current state to history stack for back navigation."""
    history_entry = {
        "hmw_results": st.session_state.get("hmw_results", {}),
        "feature_ideas": st.session_state.get("feature_ideas", {}),
        "user_context": st.session_state.get("user_context", []),
        "sketch_prompts": st.session_state.get("sketch_prompts", []),
        "sketch_concepts": st.session_state.get("sketch_concepts", []),
        "layout_results": st.session_state.get("layout_results", {}),
        "image_urls": st.session_state.get("image_urls", []),
        "current_refinement": st.session_state.get("current_refinement"),
        "challenge_text": st.session_state.get("challenge_text", ""),
    }
    
    if "history_stack" not in st.session_state:
        st.session_state["history_stack"] = []
    
    st.session_state["history_stack"].append(history_entry)


def restore_state_from_history() -> None:
    """Restore previous state from history stack."""
    if not st.session_state.get("history_stack"):
        return
    
    previous_state = st.session_state["history_stack"].pop()
    
    st.session_state["hmw_results"] = previous_state.get("hmw_results", {})
    st.session_state["feature_ideas"] = previous_state.get("feature_ideas", {})
    st.session_state["user_context"] = previous_state.get("user_context", [])
    st.session_state["sketch_prompts"] = previous_state.get("sketch_prompts", [])
    st.session_state["sketch_concepts"] = previous_state.get("sketch_concepts", [])
    st.session_state["layout_results"] = previous_state.get("layout_results", {})
    st.session_state["image_urls"] = previous_state.get("image_urls", [])
    st.session_state["current_refinement"] = previous_state.get("current_refinement")
    st.session_state["challenge_text"] = previous_state.get("challenge_text", "")
    st.session_state["generation_complete"] = True


async def build_on_selected_ideas(selected_idea_ids: list[str]) -> None:
    """Build upon selected ideas."""
    try:
        if not selected_idea_ids:
            raise ValueError("No ideas selected")
        
        # Get the actual idea texts from session state
        selected_idea_texts = []
        for idea_id in selected_idea_ids:
            idea_text = st.session_state.get(f"idea_{idea_id}", "")
            if idea_text:
                selected_idea_texts.append(idea_text)
        
        if not selected_idea_texts:
            raise ValueError("No valid ideas found in selection")
        
        # Save current state to history before refining
        save_state_to_history()
        
        # Use original challenge if available
        original_challenge = st.session_state.get("original_challenge") or st.session_state.get("challenge_text", "")
        if not original_challenge:
            raise ValueError("No challenge found for refinement")
        
        # Combine selected ideas into a single refinement context
        ideas_text = "\n".join([f"- {idea}" for idea in selected_idea_texts])
        combined_refinement = f"Build upon and expand these ideas:\n{ideas_text}"
        
        # Clear any previous errors
        st.session_state["error_message"] = ""
        st.session_state["is_generating"] = True
        
        # Run refinement generation
        await run_generation(original_challenge, refine_from=combined_refinement)
        
        # Clear selected ideas after building
        st.session_state["selected_ideas"] = []
        
    except Exception as e:
        error_msg = str(e)
        import traceback
        print(f"Refinement error: {error_msg}")
        print(traceback.format_exc())
        
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            st.session_state["error_message"] = (
                "Rate limit reached. Please wait a moment and try again."
            )
        else:
            st.session_state["error_message"] = f"Refinement failed: {error_msg}"
        st.session_state["is_generating"] = False
        st.session_state["generation_complete"] = False
        raise


async def run_generation(challenge: str, refine_from: str | None = None) -> None:
    """Run the full generation pipeline and update session state.
    
    Args:
        challenge: The design challenge text
        refine_from: Optional selected idea to refine/build upon
    """
    try:
        # Clear any previous errors
        st.session_state["error_message"] = ""
        
        # If refining, add context to challenge
        if refine_from:
            # Extract original challenge if we're in a refinement state
            original = st.session_state.get("original_challenge") or challenge
            refined_challenge = f"{original}\n\nBuild upon and refine this specific idea: {refine_from}\n\nGenerate new ideas that expand and deepen this concept, exploring it from different angles and contexts."
        else:
            refined_challenge = challenge
        
        results = await generate_all(refined_challenge)
        
        # Update session state
        st.session_state["hmw_results"] = results["hmw"]
        st.session_state["feature_ideas"] = results.get("feature_ideas", {})
        st.session_state["user_context"] = results.get("user_context", [])
        st.session_state["sketch_prompts"] = results["sketch_prompts"]
        st.session_state["sketch_concepts"] = results.get("sketch_concepts", results["sketch_prompts"])
        st.session_state["layout_results"] = results["layouts"]
        st.session_state["image_urls"] = [img.get("url") for img in results["images"]]
        st.session_state["generation_complete"] = True
        st.session_state["is_generating"] = False  # Clear generating flag on success
        st.session_state["error_message"] = ""
        if refine_from:
            st.session_state["current_refinement"] = refine_from
        else:
            st.session_state["current_refinement"] = None
            # Save original challenge on first generation
            if not st.session_state.get("original_challenge"):
                st.session_state["original_challenge"] = challenge
        
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
    # Header with title and subtitle
    st.title("Idea Generator for Designers")
    st.markdown(
        '<p class="section-description">Turn a single design challenge into reframes, sketches, and layouts — in seconds.</p>',
        unsafe_allow_html=True
    )

    # Design Challenge Section
    st.markdown("### Design Challenge")
    st.markdown(
        '<p class="section-description">Choose what you want to do. Enter your design challenge below to generate ideas.</p>',
        unsafe_allow_html=True
    )
    
    challenge = st.text_area(
        "What challenge are you solving?",
        key="challenge_text",
        height=100,
        placeholder="Improve the bus stop experience for commuters during winter storms.",
        help="Be specific about the problem, context, and users you're designing for."
    )

    generate_clicked = st.button(
        "Generate Concepts",
        type="primary",
        disabled=st.session_state["is_generating"] or not challenge.strip(),
    )
    
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
        # Clear history and refinement on new generation
        st.session_state["history_stack"] = []
        st.session_state["current_refinement"] = None
        st.session_state["original_challenge"] = challenge
        st.session_state["selected_ideas"] = []  # Clear selections on new generation
        
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

    # Subtle gray hairline divider between sections
    st.markdown('<div style="margin: 2rem 0; border-top: 1px solid #e0e0e0;"></div>', unsafe_allow_html=True)
    
    # Results Overview Section
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
        return  # Don't show results while loading
    
    # Show results with tabular navigation
    if has_results:
        # Clear is_generating flag if we have results (might be stale)
        if st.session_state.get("is_generating"):
            st.session_state["is_generating"] = False
        
        # Show back button and refinement indicator if we have history
        if st.session_state.get("history_stack") or st.session_state.get("current_refinement"):
            col_back, col_ref = st.columns([1, 4])
            with col_back:
                if st.button("← Back", key="back_button", disabled=not st.session_state.get("history_stack")):
                    restore_state_from_history()
                    st.rerun()
            with col_ref:
                if st.session_state.get("current_refinement"):
                    st.info(f"Currently building on: {st.session_state['current_refinement'][:100]}...")
            st.markdown("<br>", unsafe_allow_html=True)
        
        # Show "Build on" button if any ideas are selected
        selected_ideas = st.session_state.get("selected_ideas", [])
        if selected_ideas:
            col_build, col_clear = st.columns([2, 1])
            with col_build:
                if st.button("Build on Selected Ideas", key="build_on_button", type="primary", disabled=st.session_state.get("is_generating")):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(build_on_selected_ideas(selected_ideas))
                    finally:
                        loop.close()
                    st.rerun()
            with col_clear:
                if st.button("Clear Selection", key="clear_selection"):
                    st.session_state["selected_ideas"] = []
                    st.rerun()
            st.markdown(f"<p style='color: #666666; font-size: 0.875rem; margin-top: 0.5rem;'>{len(selected_ideas)} idea(s) selected</p>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
        
        # Create tabs for the five sections
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["HMW Reframes", "Feature Ideas", "Concept Sketches", "User Context", "Layout Ideas"])
        
        # Display HMW Reframes in first tab
        with tab1:
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            hmw_results = st.session_state.get("hmw_results", {})
            
            # Handle backward compatibility: old format was List[str], new format is Dict[str, List[str]]
            if isinstance(hmw_results, list):
                # Old format - convert to new format
                hmw_results = {"Design Exploration": hmw_results}
            
            if hmw_results and isinstance(hmw_results, dict):
                st.markdown('<div class="result-heading">How Might We Statements:</div>', unsafe_allow_html=True)
                theme_count = 0
                for theme_name, statements in hmw_results.items():
                    if statements:  # Only show themes with statements
                        theme_count += 1
                        st.markdown(f'<h3 style="margin-top: 2rem; margin-bottom: 1rem; color: #1976d2; font-weight: 500;">{theme_name}</h3>', unsafe_allow_html=True)
                        for i, stmt in enumerate(statements, 1):
                            idea_id = f"hmw_{theme_name}_{i}"
                            idea_text = stmt
                            
                            # Initialize selected_ideas if needed
                            if "selected_ideas" not in st.session_state:
                                st.session_state["selected_ideas"] = []
                            
                            is_selected = idea_id in st.session_state["selected_ideas"]
                            
                            # Make the element clickable - use button styled as text
                            button_key = f"select_{idea_id}"
                            if st.button(f"{i}. {stmt}", key=button_key, use_container_width=True):
                                # Toggle selection
                                if idea_id in st.session_state["selected_ideas"]:
                                    st.session_state["selected_ideas"].remove(idea_id)
                                    if f"idea_{idea_id}" in st.session_state:
                                        del st.session_state[f"idea_{idea_id}"]
                                else:
                                    st.session_state["selected_ideas"].append(idea_id)
                                    st.session_state[f"idea_{idea_id}"] = idea_text
                                st.rerun()
                            
                            # Apply visual styling for selected items via CSS
                            if is_selected:
                                st.markdown(f"""
                                    <style>
                                        button[key="{button_key}"] {{
                                            background-color: #e3f2fd !important;
                                            border-left: 3px solid #1976d2 !important;
                                            border-radius: 4px !important;
                                        }}
                                    </style>
                                """, unsafe_allow_html=True)
                            
                            if i < len(statements):
                                st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
                        if theme_count < len(hmw_results):
                            st.markdown("<div style='margin: 2rem 0; border-top: 1px solid #e0e0e0;'></div>", unsafe_allow_html=True)
            else:
                st.info("No reframes generated yet.")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Display Feature Ideas in second tab
        with tab2:
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            feature_ideas = st.session_state.get("feature_ideas", {})
            
            if feature_ideas and isinstance(feature_ideas, dict):
                st.markdown('<div class="result-heading">Feature Ideas:</div>', unsafe_allow_html=True)
                theme_count = 0
                for theme_name, features in feature_ideas.items():
                    if features:  # Only show themes with features
                        theme_count += 1
                        st.markdown(f'<h3 style="margin-top: 2rem; margin-bottom: 1rem; color: #1976d2; font-weight: 500;">{theme_name}</h3>', unsafe_allow_html=True)
                        for i, feature_data in enumerate(features, 1):
                            if isinstance(feature_data, dict):
                                feature = feature_data.get("feature", f"Feature {i}")
                                rationale = feature_data.get("rationale", "")
                            else:
                                feature = str(feature_data)
                                rationale = ""
                            
                            idea_id = f"feature_{theme_name}_{i}"
                            idea_text = f"{feature}. {rationale}" if rationale else feature
                            
                            # Initialize selected_ideas if needed
                            if "selected_ideas" not in st.session_state:
                                st.session_state["selected_ideas"] = []
                            
                            is_selected = idea_id in st.session_state["selected_ideas"]
                            
                            # Make the feature clickable
                            button_key = f"select_{idea_id}"
                            button_text = f"{i}. {feature}"
                            if st.button(button_text, key=button_key, use_container_width=True):
                                # Toggle selection
                                if idea_id in st.session_state["selected_ideas"]:
                                    st.session_state["selected_ideas"].remove(idea_id)
                                    if f"idea_{idea_id}" in st.session_state:
                                        del st.session_state[f"idea_{idea_id}"]
                                else:
                                    st.session_state["selected_ideas"].append(idea_id)
                                    st.session_state[f"idea_{idea_id}"] = idea_text
                                st.rerun()
                            
                            # Apply visual styling for selected items via CSS
                            if is_selected:
                                st.markdown(f"""
                                    <style>
                                        button[key="{button_key}"] {{
                                            background-color: #e3f2fd !important;
                                            border-left: 3px solid #1976d2 !important;
                                            border-radius: 4px !important;
                                        }}
                                    </style>
                                """, unsafe_allow_html=True)
                            
                            if rationale:
                                st.markdown(f'<div style="margin-top: 0.5rem; margin-bottom: 1rem; color: #666666; font-size: 0.9375rem; font-style: italic;">{rationale}</div>', unsafe_allow_html=True)
                            if i < len(features):
                                st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
                        if theme_count < len(feature_ideas):
                            st.markdown("<div style='margin: 2rem 0; border-top: 1px solid #e0e0e0;'></div>", unsafe_allow_html=True)
            else:
                st.info("Feature ideas will appear here after generation.")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Display Concept Sketches in third tab
        with tab3:
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.markdown('<div class="result-heading">Concept Sketches:</div>', unsafe_allow_html=True)
            image_urls = st.session_state.get("image_urls", [])
            sketch_concepts = st.session_state.get("sketch_concepts", [])
            # Fallback to sketch_prompts if concepts not available
            if not sketch_concepts:
                sketch_concepts = st.session_state.get("sketch_prompts", [])
            if image_urls:
                for i, url in enumerate(image_urls, 1):
                    if url:
                        concept_text = sketch_concepts[i - 1] if i <= len(sketch_concepts) else ""
                        idea_id = f"sketch_{i}"
                        
                        # Initialize selected_ideas if needed
                        if "selected_ideas" not in st.session_state:
                            st.session_state["selected_ideas"] = []
                        
                        is_selected = idea_id in st.session_state["selected_ideas"]
                        
                        # Make the sketch clickable - wrap in a container
                        container_key = f"sketch_container_{i}"
                        with st.container():
                            button_key = f"select_{idea_id}"
                            if st.button(f"Sketch {i}", key=button_key, use_container_width=True):
                                # Toggle selection
                                if idea_id in st.session_state["selected_ideas"]:
                                    st.session_state["selected_ideas"].remove(idea_id)
                                    if f"idea_{idea_id}" in st.session_state:
                                        del st.session_state[f"idea_{idea_id}"]
                                else:
                                    st.session_state["selected_ideas"].append(idea_id)
                                    st.session_state[f"idea_{idea_id}"] = concept_text
                                st.rerun()
                            
                            # Apply visual styling for selected items via CSS
                            if is_selected:
                                st.markdown(f"""
                                    <style>
                                        button[key="{button_key}"] {{
                                            background-color: #e3f2fd !important;
                                            border-left: 3px solid #1976d2 !important;
                                            border-radius: 4px !important;
                                        }}
                                    </style>
                                """, unsafe_allow_html=True)
                            
                            # Display smaller image
                            st.image(url, width=400)
                            # Display conceptual explanation text below the image
                            if concept_text:
                                st.markdown(
                                    f'<p style="margin-top: 0.75rem; margin-bottom: 1.5rem; color: #666666; font-size: 0.9375rem; line-height: 1.6;">{concept_text}</p>',
                                    unsafe_allow_html=True
                                )
                        if i < len(image_urls):
                            st.markdown("<div style='margin: 2rem 0; border-top: 1px solid #e0e0e0;'></div>", unsafe_allow_html=True)
                    else:
                        st.warning(f"Image {i} failed to generate")
            else:
                st.info("Sketches will appear here after generation.")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Display User Context in fourth tab
        with tab4:
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.markdown('<div class="result-heading">User Context:</div>', unsafe_allow_html=True)
            user_context = st.session_state.get("user_context", [])
            
            if user_context and isinstance(user_context, list):
                for segment_idx, segment in enumerate(user_context, 1):
                    segment_name = segment.get("segment_name", f"User Segment {segment_idx}")
                    persona = segment.get("persona", {})
                    scenarios = segment.get("scenarios", [])
                    
                    st.markdown(f'<h3 style="margin-top: 2rem; margin-bottom: 1rem; color: #1976d2; font-weight: 500;">{segment_name}</h3>', unsafe_allow_html=True)
                    
                    if persona:
                        persona_name = persona.get("name", "User")
                        persona_desc = persona.get("description", "")
                        idea_id = f"persona_{segment_idx}"
                        idea_text = f"Persona: {persona_name}. {persona_desc}"
                        
                        # Initialize selected_ideas if needed
                        if "selected_ideas" not in st.session_state:
                            st.session_state["selected_ideas"] = []
                        
                        is_selected = idea_id in st.session_state["selected_ideas"]
                        
                        # Make the persona clickable
                        button_key = f"select_{idea_id}"
                        button_text = f"Persona: {persona_name}"
                        if st.button(button_text, key=button_key, use_container_width=True):
                            # Toggle selection
                            if idea_id in st.session_state["selected_ideas"]:
                                st.session_state["selected_ideas"].remove(idea_id)
                                if f"idea_{idea_id}" in st.session_state:
                                    del st.session_state[f"idea_{idea_id}"]
                            else:
                                st.session_state["selected_ideas"].append(idea_id)
                                st.session_state[f"idea_{idea_id}"] = idea_text
                            st.rerun()
                        
                        # Apply visual styling for selected items via CSS
                        if is_selected:
                            st.markdown(f"""
                                <style>
                                    button[key="{button_key}"] {{
                                        background-color: #e3f2fd !important;
                                        border-left: 3px solid #1976d2 !important;
                                        border-radius: 4px !important;
                                    }}
                                </style>
                            """, unsafe_allow_html=True)
                        
                        if persona_desc:
                            st.markdown(f'<div class="result-content">{persona_desc}</div>', unsafe_allow_html=True)
                    
                    if scenarios:
                        st.markdown('<h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem;">Key Scenarios:</h4>', unsafe_allow_html=True)
                        for i, scenario in enumerate(scenarios, 1):
                            idea_id = f"scenario_{segment_idx}_{i}"
                            idea_text = f"Persona: {persona_name if persona else 'User'}. Scenario: {scenario}"
                            
                            # Initialize selected_ideas if needed
                            if "selected_ideas" not in st.session_state:
                                st.session_state["selected_ideas"] = []
                            
                            is_selected = idea_id in st.session_state["selected_ideas"]
                            
                            # Make the scenario clickable
                            button_key = f"select_{idea_id}"
                            button_text = f"{i}. {scenario}"
                            if st.button(button_text, key=button_key, use_container_width=True):
                                # Toggle selection
                                if idea_id in st.session_state["selected_ideas"]:
                                    st.session_state["selected_ideas"].remove(idea_id)
                                    if f"idea_{idea_id}" in st.session_state:
                                        del st.session_state[f"idea_{idea_id}"]
                                else:
                                    st.session_state["selected_ideas"].append(idea_id)
                                    st.session_state[f"idea_{idea_id}"] = idea_text
                                st.rerun()
                            
                            # Apply visual styling for selected items via CSS
                            if is_selected:
                                st.markdown(f"""
                                    <style>
                                        button[key="{button_key}"] {{
                                            background-color: #e3f2fd !important;
                                            border-left: 3px solid #1976d2 !important;
                                            border-radius: 4px !important;
                                        }}
                                    </style>
                                """, unsafe_allow_html=True)
                            
                            if i < len(scenarios):
                                st.markdown("<div style='margin: 0.5rem 0;'></div>", unsafe_allow_html=True)
                    
                    if segment_idx < len(user_context):
                        st.markdown("<div style='margin: 2rem 0; border-top: 1px solid #e0e0e0;'></div>", unsafe_allow_html=True)
            else:
                st.info("User context will appear here after generation.")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Display Layout Ideas in fifth tab
        with tab5:
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.markdown('<div class="result-heading">Layout Ideas:</div>', unsafe_allow_html=True)
            layout_results = st.session_state.get("layout_results", {})
            
            # Handle backward compatibility: old format was List[Dict], new format is Dict[str, List[Dict]]
            if isinstance(layout_results, list):
                # Old format - convert to new format
                layout_results = {"Layout Directions": layout_results}
            
            if layout_results and isinstance(layout_results, dict):
                theme_count = 0
                for theme_name, layouts in layout_results.items():
                    if layouts:  # Only show themes with layouts
                        theme_count += 1
                        st.markdown(f'<h3 style="margin-top: 2rem; margin-bottom: 1rem; color: #1976d2; font-weight: 500;">{theme_name}</h3>', unsafe_allow_html=True)
                        for i, layout in enumerate(layouts, 1):
                            if isinstance(layout, dict):
                                title = layout.get("title", f"Layout {i}")
                                desc = layout.get("description", "")
                            else:
                                # Fallback for unexpected format
                                title = f"Layout {i}"
                                desc = str(layout)
                            
                            idea_id = f"layout_{theme_name}_{i}"
                            idea_text = f"{title}: {desc}"
                            
                            # Initialize selected_ideas if needed
                            if "selected_ideas" not in st.session_state:
                                st.session_state["selected_ideas"] = []
                            
                            is_selected = idea_id in st.session_state["selected_ideas"]
                            
                            # Make the layout clickable
                            button_key = f"select_{idea_id}"
                            button_text = f"{i}. {title}"
                            if st.button(button_text, key=button_key, use_container_width=True):
                                # Toggle selection
                                if idea_id in st.session_state["selected_ideas"]:
                                    st.session_state["selected_ideas"].remove(idea_id)
                                    if f"idea_{idea_id}" in st.session_state:
                                        del st.session_state[f"idea_{idea_id}"]
                                else:
                                    st.session_state["selected_ideas"].append(idea_id)
                                    st.session_state[f"idea_{idea_id}"] = idea_text
                                st.rerun()
                            
                            # Apply visual styling for selected items via CSS
                            if is_selected:
                                st.markdown(f"""
                                    <style>
                                        button[key="{button_key}"] {{
                                            background-color: #e3f2fd !important;
                                            border-left: 3px solid #1976d2 !important;
                                            border-radius: 4px !important;
                                        }}
                                    </style>
                                """, unsafe_allow_html=True)
                            
                            st.markdown(f'<div class="result-content">{desc}</div>', unsafe_allow_html=True)
                            if i < len(layouts):
                                st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
                        if theme_count < len(layout_results):
                            st.markdown("<div style='margin: 2rem 0; border-top: 1px solid #e0e0e0;'></div>", unsafe_allow_html=True)
            else:
                st.info("Layout suggestions will appear here after generation.")
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Placeholder state
        st.info("Enter a challenge above and click Generate to see results.")


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
/* Style Streamlit containers as section cards using JavaScript class injection */
/* This will be handled by JavaScript - CSS here is just for when cards are properly wrapped */
.section-card-wrapper {{
    background-color: #ffffff !important;
    padding: 2rem 2.5rem !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08) !important;
    border: 2px solid #c0c0c0 !important;
    margin: 1.5rem 0 2rem 0 !important;
    position: relative !important;
    display: block !important;
    width: 100% !important;
    box-sizing: border-box !important;
}}

/* Hide ALL empty section-card divs and any empty containers with card styling */
.section-card,
div[id^="card-"],
div[class*="section-card"] {{
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    box-shadow: none !important;
    opacity: 0 !important;
}}

/* Hide empty divs but EXCLUDE Streamlit widget containers */
div:empty:not([class*="st"]):not([data-testid*="st"]) {{
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    opacity: 0 !important;
}}

/* Always show Streamlit widget containers - these contain inputs/textareas */
.stTextArea,
.stTextInput,
.element-container:has(textarea),
.element-container:has(input),
[class*="stTextArea"],
[class*="stTextInput"] {{
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
}}

/* Specifically target and hide empty divs with card-like styling */
div[style*="shadow"],
div[style*="border-radius"],
div[style*="rounded"] {{
    box-shadow: none !important;
    border: none !important;
}}

/* Hide Streamlit containers that are empty */
.stContainer:empty,
.element-container:empty,
div[data-testid]:empty {{
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    box-shadow: none !important;
    visibility: hidden !important;
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

/* Selection buttons - styled to look like regular text but legible */
.stButton > button[key^="select_"] {{
    background-color: #ffffff !important;
    color: #000000 !important;
    border: 1px solid #e0e0e0 !important;
    font-weight: normal !important;
    padding: 0.875rem 1rem !important;
    border-radius: 6px !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    text-align: left !important;
    font-family: 'Helvetica', 'Helvetica Neue', Arial, sans-serif !important;
    font-size: 1.0625rem !important;
    line-height: 1.6 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
    margin: 0.5rem 0 !important;
    white-space: normal !important;
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
    min-height: auto !important;
    height: auto !important;
    display: block !important;
}}

.stButton > button[key^="select_"]:hover {{
    background-color: #f5f5f5 !important;
    border-color: #1976d2 !important;
    border-width: 2px !important;
    box-shadow: 0 2px 4px rgba(25, 118, 210, 0.15) !important;
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
    min-height: 80px !important;
    line-height: 1.6 !important;
    resize: none !important;
    overflow-y: hidden !important;
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

/* Constrain main content width like ResearchBridge - narrow, centered */
.block-container,
.main .block-container,
[data-testid="stAppViewContainer"] > .main,
.stApp > .main {{
    max-width: 900px !important;
    margin-left: auto !important;
    margin-right: auto !important;
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

/* Hide empty white rectangle dividers/containers - but NOT widget containers */
[data-testid="stHorizontalBlock"]:empty,
div[class*="empty"]:empty,
input[type="text"]:not([value]):not(:focus),
input[type="text"][value=""]:not(:focus),
div[data-testid]:empty:not([class*="st"]) {{
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    opacity: 0 !important;
    border: none !important;
    box-shadow: none !important;
}}

/* DO NOT hide Streamlit widget containers even if they appear empty */
.stTextInput,
.stTextArea,
.element-container:has(textarea),
.element-container:has(input),
[class*="stTextArea"],
[class*="stTextInput"] {{
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    height: auto !important;
}}

/* Hide any Streamlit default spacing/padding elements that appear as white rectangles */
/* BUT preserve widget containers */
div[style*="white"]:empty:not([class*="st"]):not([data-testid*="st"]),
div[style*="background"]:empty:not([class*="st"]):not([data-testid*="st"]),
div[class*="block-container"]:empty:not(:has(.stTextArea)):not(:has(.stTextInput)) {{
    display: none !important;
}}

/* Hide empty containers with shadows/borders that look like dividers */
.element-container:not(:has(*)),
div[class*="element-container"]:not(:has(*)),
div[data-testid]:not(:has(*)) {{
    display: none !important;
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
            // Remove empty white rectangle input fields
            document.querySelectorAll('input[type="text"]:not([value]), input[type="text"][value=""], textarea:empty, .stTextInput:empty, .stTextArea:empty').forEach(function(el) {
                if (!el.closest('.section-card')) {
                    el.style.display = 'none';
                    el.remove();
                }
            });
            // Aggressively remove empty containers that appear as white rectangles
            document.querySelectorAll('div').forEach(function(el) {
                // Skip if it's inside a section card wrapper or has important content
                if (el.closest('.section-card-wrapper') || 
                    el.id === 'design-challenge-start' || 
                    el.id === 'design-challenge-end' ||
                    el.id === 'results-overview-start' ||
                    el.id === 'results-overview-end') {
                    return;
                }
                
                // Check if it's empty or only contains whitespace
                const hasContent = el.children.length > 0;
                const hasText = el.textContent && el.textContent.trim().length > 10;
                const hasInputs = el.querySelector('input, textarea, button, img, h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, iframe, canvas');
                
                const style = window.getComputedStyle(el);
                const hasShadow = style.boxShadow !== 'none';
                const hasBorder = style.border !== 'none' && style.borderWidth !== '0px' && style.borderStyle !== 'none';
                const hasBorderRadius = style.borderRadius !== '0px';
                const hasBackground = style.backgroundColor && style.backgroundColor !== 'rgba(0, 0, 0, 0)' && style.backgroundColor !== 'transparent';
                const hasPadding = style.paddingTop !== '0px' || style.paddingBottom !== '0px';
                
                // If empty and has card-like styling (shadow, border, rounded, padding, background), remove it
                if (!hasContent && !hasText && !hasInputs && 
                    (hasShadow || (hasBorder && hasBorderRadius && hasPadding && hasBackground))) {
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                    el.style.height = '0';
                    el.style.margin = '0';
                    el.style.padding = '0';
                    el.style.border = 'none';
                    el.style.boxShadow = 'none';
                    el.style.background = 'transparent';
                    el.remove();
                }
            });
        }
        
        function wrapCards() {
            // Find all section-card-wrapper divs and wrap their following siblings
            document.querySelectorAll('.section-card-wrapper').forEach(function(wrapper) {
                // Skip if already wrapped
                if (wrapper.dataset.wrapped === 'true') return;
                
                const elementsToWrap = [];
                let current = wrapper.nextSibling;
                
                // Find the closing </div> marker - it will be in a stMarkdown container
                let foundCloseMarker = false;
                let siblingCount = 0;
                const maxSiblings = 50; // Safety limit
                
                while (current && siblingCount < maxSiblings && !foundCloseMarker) {
                    // Check if this is a closing marker (empty div or markdown container with just </div>)
                    if (current.textContent && current.textContent.includes('</div>') && 
                        current.textContent.trim() === '</div>') {
                        foundCloseMarker = true;
                        current.remove(); // Remove the closing marker
                        break;
                    }
                    
                    // Collect Streamlit elements to wrap
                    if (current.nodeType === 1 && (
                        current.classList.contains('element-container') ||
                        current.hasAttribute('data-testid') ||
                        (current.tagName === 'DIV' && current.querySelector('[class*="st"]'))
                    )) {
                        elementsToWrap.push(current);
                    }
                    
                    const next = current.nextSibling;
                    current = next;
                    siblingCount++;
                }
                
                // Move all collected elements into the wrapper
                elementsToWrap.forEach(function(el) {
                    wrapper.appendChild(el);
                });
                
                wrapper.dataset.wrapped = 'true';
            });
        }
        
        function init() {
            removeAllDividers();
            wrapCards();
        }
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
        
        const observer = new MutationObserver(function() {
            removeAllDividers();
            wrapCards();
        });
        
        observer.observe(document.body, { childList: true, subtree: true });
        
        setTimeout(init, 100);
        setTimeout(init, 500);
        setTimeout(init, 1500);
        setTimeout(init, 2500);
        
        // Auto-resize textarea based on content
        function autoResizeTextarea() {
            const textareas = document.querySelectorAll('textarea[data-testid*="stTextArea"]');
            textareas.forEach(function(textarea) {
                function adjustHeight() {
                    textarea.style.height = 'auto';
                    textarea.style.height = Math.max(80, textarea.scrollHeight) + 'px';
                }
                
                // Set initial height
                adjustHeight();
                
                // Adjust on input
                textarea.addEventListener('input', adjustHeight);
                
                // Adjust on load (for existing content)
                if (textarea.value) {
                    setTimeout(adjustHeight, 100);
                }
            });
        }
        
        // Run auto-resize after DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', autoResizeTextarea);
        } else {
            autoResizeTextarea();
        }
        
        // Also run when new elements are added
        const resizeObserver = new MutationObserver(function() {
            autoResizeTextarea();
        });
        
        resizeObserver.observe(document.body, { childList: true, subtree: true });
        
        setTimeout(autoResizeTextarea, 100);
        setTimeout(autoResizeTextarea, 500);
        setTimeout(autoResizeTextarea, 1500);
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
