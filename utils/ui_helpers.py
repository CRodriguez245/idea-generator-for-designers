"""
UI formatting and layout helpers for Streamlit.

Provides:
    - Copy-to-clipboard functionality
    - Formatted display of results
    - Export utilities
"""

from __future__ import annotations

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
