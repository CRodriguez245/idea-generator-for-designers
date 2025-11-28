"""
UI formatting and layout helpers for Streamlit.

Provides:
    - Copy-to-clipboard functionality
    - Formatted display of results
    - Export utilities
    - Carousel component for displaying results
"""

from __future__ import annotations

import streamlit as st
from typing import Any, Dict, List


def format_hmw_for_display(statements: List[str]) -> str:
    """Format HMW statements for display."""
    if not statements:
        return "No reframes generated yet."
    return "\n\n".join(f"**{i+1}.** {stmt}" for i, stmt in enumerate(statements))


def format_layout_for_display(layouts: List[Dict[str, str]]) -> str:
    """Format layout suggestions for display."""
    if not layouts:
        return "No layouts generated yet."
    parts = []
    for i, layout in enumerate(layouts):
        title = layout.get("title", f"Layout {i+1}")
        desc = layout.get("description", "")
        parts.append(f"**{i+1}. {title}**\n\n{desc}")
    return "\n\n---\n\n".join(parts)


def create_export_text(
    challenge: str,
    hmw: List[str],
    layouts: List[Dict[str, str]],
    sketch_prompts: List[str] | None = None,
) -> str:
    """Create a plain text export of all results."""
    lines = [
        "# Idea Generator Results",
        "",
        f"## Design Challenge\n{challenge}",
        "",
        "## How Might We Statements",
    ]
    for i, stmt in enumerate(hmw, 1):
        lines.append(f"{i}. {stmt}")
    lines.append("")
    lines.append("## Layout Suggestions")
    for i, layout in enumerate(layouts, 1):
        lines.append(f"\n### {i}. {layout.get('title', f'Layout {i}')}")
        lines.append(layout.get("description", ""))
    if sketch_prompts:
        lines.append("")
        lines.append("## Sketch Prompts")
        for i, prompt in enumerate(sketch_prompts, 1):
            lines.append(f"{i}. {prompt}")
    return "\n".join(lines)


def render_carousel_navigation(current_index: int, total_items: int, key_prefix: str) -> int:
    """
    Render carousel navigation buttons and return the selected index.
    
    Args:
        current_index: Current active item index (0-based)
        total_items: Total number of items in carousel
        key_prefix: Unique prefix for button keys
    
    Returns:
        Selected index after navigation
    """
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("◀ Previous", key=f"{key_prefix}_prev", disabled=current_index == 0):
            return max(0, current_index - 1)
    
    with col2:
        st.markdown(
            f"<div style='text-align: center; padding: 10px;'>"
            f"<span style='font-size: 14px; color: #666;'>"
            f"{current_index + 1} of {total_items}"
            f"</span></div>",
            unsafe_allow_html=True,
        )
        # Pagination dots
        dots_html = "<div style='text-align: center; margin-top: 5px;'>"
        for i in range(total_items):
            if i == current_index:
                dots_html += "● "
            else:
                dots_html += "○ "
        dots_html += "</div>"
        st.markdown(dots_html, unsafe_allow_html=True)
    
    with col3:
        if st.button("Next ▶", key=f"{key_prefix}_next", disabled=current_index >= total_items - 1):
            return min(total_items - 1, current_index + 1)
    
    return current_index


def render_loading_carousel(section_names: List[str]) -> None:
    """Render a loading state carousel."""
    carousel_html = """
    <style>
        .carousel-container {
            position: relative;
            width: 100%;
            max-width: 1200px;
            margin: 20px auto;
            perspective: 1000px;
        }
        .carousel-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            padding: 20px 0;
        }
        .carousel-card {
            transition: all 0.4s ease;
            border-radius: 12px;
            padding: 30px;
            background: linear-gradient(135deg, #e0e0e0 0%, #bdbdbd 100%);
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            color: #666;
            text-align: center;
            min-height: 200px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            opacity: 0.6;
        }
        .carousel-card.loading-active {
            opacity: 1;
            background: linear-gradient(135deg, #f0f0f0 0%, #d0d0d0 100%);
            animation: pulse 1.5s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 0.8; }
            50% { opacity: 1; }
        }
        .carousel-card.prev, .carousel-card.next {
            transform: scale(0.7);
            opacity: 0.3;
        }
        .carousel-card.prev {
            margin-right: -150px;
        }
        .carousel-card.next {
            margin-left: -150px;
        }
        .card-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        }
    </style>
    <div class="carousel-container">
        <div class="carousel-wrapper">
    """
    
    for i, name in enumerate(section_names):
        card_class = "carousel-card"
        if i == 0:
            card_class += " loading-active"
        elif i == 1:
            card_class += " next"
        elif i == 2:
            card_class += " next"
        
        carousel_html += f"""
            <div class="{card_class}">
                <div class="card-title">{name}</div>
                <div style="font-size: 14px; margin-top: 10px;">Loading...</div>
            </div>
        """
    
    carousel_html += """
        </div>
    </div>
    """
    
    st.markdown(carousel_html, unsafe_allow_html=True)


def get_preview_content(section_index: int, preview_data: Dict[str, Any] | None) -> str:
    """Get preview content for a section - return empty string to hide previews."""
    # Return empty string to keep carousel simple without preview text
    return ""


def render_visual_carousel(section_names: List[str], current_index: int, key_prefix: str, preview_data: Dict[str, Any] | None = None) -> int:
    """
    Render a simple navigation for sections using Streamlit native components.
    
    Args:
        section_names: List of section names
        current_index: Current active section index
        key_prefix: Unique prefix for button keys
        preview_data: Optional dict (not used, kept for compatibility)
    
    Returns:
        Selected index after navigation
    """
    # Simple navigation using buttons and indicators
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("◀ Previous", key=f"{key_prefix}_prev", disabled=current_index == 0):
            return max(0, current_index - 1)
    
    with col2:
        # Show current section name
        st.markdown(f"<div style='text-align: center; padding: 15px; font-size: 18px; font-weight: bold;'>{section_names[current_index]}</div>", unsafe_allow_html=True)
        # Pagination dots
        dots = " ".join(["●" if i == current_index else "○" for i in range(len(section_names))])
        st.markdown(f"<div style='text-align: center; margin-top: 5px;'>{dots}</div>", unsafe_allow_html=True)
    
    with col3:
        if st.button("Next ▶", key=f"{key_prefix}_next", disabled=current_index >= len(section_names) - 1):
            return min(len(section_names) - 1, current_index + 1)
    
    return current_index
