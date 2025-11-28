"""
OpenAI API integration for GPT-4 and DALL·E 3.

Handles:
    - Loading prompt templates and filling them with user input
    - Making parallel API calls for speed
    - Error handling and rate limit management
    - Structured response parsing
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List

from openai import AsyncOpenAI

# Initialize client lazily
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Get or create OpenAI client instance."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Set it in .env file or environment variables."
            )
        _client = AsyncOpenAI(api_key=api_key)
    return _client


def load_prompt_template(template_name: str) -> str:
    """Load prompt template from prompts/ directory."""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    template_path = prompts_dir / f"{template_name}_prompt.txt"
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def fill_template(template: str, challenge: str) -> str:
    """Replace {{challenge}} placeholder in template."""
    return template.replace("{{challenge}}", challenge)


async def generate_hmw_statements(challenge: str) -> Dict[str, List[str]]:
    """Generate thematically organized 'How Might We' statements using GPT-4."""
    client = get_client()
    template = load_prompt_template("hmw")
    prompt = fill_template(template, challenge)

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a design strategist. Return multiple 'How Might We' statements organized into 3-4 thematic categories. Format as 'Theme 1: [Name]' followed by numbered statements, then 'Theme 2: [Name]', etc.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=800,
        )
        content = response.choices[0].message.content or ""
        
        # Parse thematic groupings
        themes: Dict[str, List[str]] = {}
        current_theme = None
        lines = content.split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for theme header (Theme X: Name or just Name:)
            if line.lower().startswith("theme") and ":" in line:
                # Extract theme name after "Theme X:"
                parts = line.split(":", 1)
                if len(parts) == 2:
                    theme_name = parts[1].strip()
                    current_theme = theme_name
                    if current_theme not in themes:
                        themes[current_theme] = []
            elif ":" in line and not any(char.isdigit() for char in line.split(":")[0]):
                # Might be a theme name without "Theme" prefix
                potential_theme = line.split(":")[0].strip()
                if len(potential_theme) < 50:  # Reasonable theme name length
                    current_theme = potential_theme
                    if current_theme not in themes:
                        themes[current_theme] = []
            elif current_theme:
                # Parse HMW statement
                cleaned_stmt = line
                # Remove numbering
                for prefix in ["1.", "2.", "3.", "4.", "5.", "•", "-", "HMW", "How might we"]:
                    if cleaned_stmt.lower().startswith(prefix.lower()):
                        cleaned_stmt = cleaned_stmt[len(prefix) :].strip()
                        if cleaned_stmt.startswith(":"):
                            cleaned_stmt = cleaned_stmt[1:].strip()
                        break
                
                # Check if it looks like an HMW statement
                if cleaned_stmt and (cleaned_stmt.lower().startswith("how") or len(cleaned_stmt) > 10):
                    # Ensure it starts with "How might we"
                    if not cleaned_stmt.lower().startswith("how might we"):
                        cleaned_stmt = f"How might we {cleaned_stmt.lower()}"
                    themes[current_theme].append(cleaned_stmt)
        
        # If no themes found, create a default structure
        if not themes:
            # Fallback: try to parse as simple list
            statements = [
                line.strip()
                for line in content.split("\n")
                if line.strip() and (line.strip().startswith(("1", "2", "3", "4", "5", "•", "-", "HMW", "How")))
            ]
            cleaned = []
            for stmt in statements:
                cleaned_stmt = stmt
                for prefix in ["1.", "2.", "3.", "4.", "5.", "•", "-", "HMW", "How might we"]:
                    if cleaned_stmt.lower().startswith(prefix.lower()):
                        cleaned_stmt = cleaned_stmt[len(prefix) :].strip()
                        if cleaned_stmt.startswith(":"):
                            cleaned_stmt = cleaned_stmt[1:].strip()
                        break
                if cleaned_stmt:
                    if not cleaned_stmt.lower().startswith("how might we"):
                        cleaned_stmt = f"How might we {cleaned_stmt.lower()}"
                    cleaned.append(cleaned_stmt)
            
            if cleaned:
                # Group into themes (3-4 per theme)
                themes["Reframing"] = cleaned[:4] if len(cleaned) >= 4 else cleaned
                if len(cleaned) > 4:
                    themes["Exploration"] = cleaned[4:8] if len(cleaned) >= 8 else cleaned[4:]
                if len(cleaned) > 8:
                    themes["Innovation"] = cleaned[8:]
        
        # Ensure we have at least one theme with statements
        if not themes:
            themes["Design Exploration"] = [
                "How might we approach this challenge from a user-centered perspective?",
                "How might we leverage technology to solve this problem?",
                "How might we create sustainable solutions for this challenge?",
            ]
        
        return themes
    except Exception as e:
        raise RuntimeError(f"Failed to generate HMW statements: {e}") from e


async def generate_sketch_prompts(challenge: str) -> List[str]:
    """Generate 3 visual sketch prompts using GPT-4."""
    client = get_client()
    template = load_prompt_template("visual")
    prompt = fill_template(template, challenge)

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a concept artist. Return exactly 3 visual prompt descriptions for DALL·E, one per line, numbered 1-3.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
            max_tokens=400,
        )
        content = response.choices[0].message.content or ""
        prompts = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith(("•", "-")))
        ]
        cleaned = []
        for p in prompts[:3]:
            for prefix in ["1.", "2.", "3.", "•", "-"]:
                if p.startswith(prefix):
                    p = p[len(prefix) :].strip()
                    break
            if p:
                cleaned.append(p)
        return cleaned[:3] if cleaned else ["sketch prompt 1", "sketch prompt 2", "sketch prompt 3"]
    except Exception as e:
        raise RuntimeError(f"Failed to generate sketch prompts: {e}") from e


async def generate_layout_suggestions(challenge: str) -> Dict[str, List[Dict[str, str]]]:
    """Generate thematically organized UI layout suggestions using GPT-4."""
    client = get_client()
    template = load_prompt_template("layout")
    prompt = fill_template(template, challenge)

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a product designer. Return multiple layout suggestions organized into 3-4 thematic categories. Format as 'Theme 1: [Name]' followed by numbered layouts with titles and descriptions, then 'Theme 2: [Name]', etc.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=1200,
        )
        content = response.choices[0].message.content or ""
        
        # Parse thematic groupings
        themes: Dict[str, List[Dict[str, str]]] = {}
        current_theme = None
        current_layout: Dict[str, str] | None = None
        lines = content.split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line might separate layouts
                if current_layout and current_theme:
                    if current_layout.get("title"):
                        themes[current_theme].append(current_layout)
                    current_layout = None
                continue
            
            # Check for theme header
            if line.lower().startswith("theme") and ":" in line:
                # Save previous layout if exists
                if current_layout and current_theme and current_layout.get("title"):
                    if current_theme not in themes:
                        themes[current_theme] = []
                    themes[current_theme].append(current_layout)
                    current_layout = None
                
                # Extract theme name
                parts = line.split(":", 1)
                if len(parts) == 2:
                    theme_name = parts[1].strip()
                    current_theme = theme_name
                    if current_theme not in themes:
                        themes[current_theme] = []
            elif ":" in line and not any(char.isdigit() for char in line.split(":")[0][:10]):
                # Might be a theme name without "Theme" prefix
                potential_theme = line.split(":")[0].strip()
                if len(potential_theme) < 50 and current_theme is None:
                    current_theme = potential_theme
                    if current_theme not in themes:
                        themes[current_theme] = []
                elif current_theme and not current_layout:
                    # Might be a layout title
                    for prefix in ["1.", "2.", "3.", "4.", "5.", "•", "-"]:
                        if line.startswith(prefix):
                            line = line[len(prefix) :].strip()
                            break
                    current_layout = {"title": line, "description": ""}
                elif current_layout:
                    # Continue description
                    current_layout["description"] += (" " if current_layout["description"] else "") + line
            elif line[0].isdigit() or line.startswith(("•", "-")):
                # Numbered item - likely a layout title
                if current_layout and current_theme and current_layout.get("title"):
                    themes[current_theme].append(current_layout)
                
                # Start new layout
                for prefix in ["1.", "2.", "3.", "4.", "5.", "•", "-"]:
                    if line.startswith(prefix):
                        title = line[len(prefix) :].strip()
                        current_layout = {"title": title, "description": ""}
                        break
            elif current_layout:
                # Continue building current layout description
                current_layout["description"] += (" " if current_layout["description"] else "") + line
            elif current_theme:
                # Might be a layout title without number
                current_layout = {"title": line, "description": ""}
        
        # Save last layout
        if current_layout and current_theme and current_layout.get("title"):
            if current_theme not in themes:
                themes[current_theme] = []
            themes[current_theme].append(current_layout)
        
        # Fallback if no themes found - parse as simple list
        if not themes:
            sections = content.split("\n\n")
            layouts_list = []
            for section in sections:
                lines = [l.strip() for l in section.split("\n") if l.strip()]
                if lines:
                    title = lines[0]
                    for prefix in ["1.", "2.", "3.", "4.", "5.", "•", "-"]:
                        if title.startswith(prefix):
                            title = title[len(prefix) :].strip()
                            break
                    description = " ".join(lines[1:]) if len(lines) > 1 else "Layout description"
                    layouts_list.append({"title": title, "description": description})
            
            if layouts_list:
                # Group into themes (2-3 per theme)
                themes["Information Architecture"] = layouts_list[:3] if len(layouts_list) >= 3 else layouts_list
                if len(layouts_list) > 3:
                    themes["Interaction Patterns"] = layouts_list[3:6] if len(layouts_list) >= 6 else layouts_list[3:]
                if len(layouts_list) > 6:
                    themes["Content Strategy"] = layouts_list[6:]
        
        # Ensure we have at least one theme
        if not themes:
            themes["Layout Directions"] = [
                {"title": "Layout 1", "description": "Description 1"},
                {"title": "Layout 2", "description": "Description 2"},
                {"title": "Layout 3", "description": "Description 3"},
            ]
        
        return themes
    except Exception as e:
        raise RuntimeError(f"Failed to generate layout suggestions: {e}") from e


async def generate_images(prompts: List[str]) -> List[Dict[str, Any]]:
    """Generate images using DALL·E 3 for each prompt."""
    client = get_client()
    tasks = []
    for prompt in prompts[:3]:
        tasks.append(
            client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
        )
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        images = []
        for result in results:
            if isinstance(result, Exception):
                images.append({"url": None, "revised_prompt": None, "error": str(result)})
            elif result.data and len(result.data) > 0:
                images.append(
                    {
                        "url": result.data[0].url,
                        "revised_prompt": result.data[0].revised_prompt,
                    }
                )
            else:
                images.append({"url": None, "revised_prompt": None})
        return images
    except Exception as e:
        raise RuntimeError(f"Failed to generate images: {e}") from e


async def generate_sketch_concepts(challenge: str, sketch_prompts: List[str]) -> List[str]:
    """Generate conceptual explanations for each sketch idea that explain the design concept being conveyed."""
    client = get_client()
    
    # Create a prompt that asks for conceptual explanations of the design ideas
    concept_prompt = f"""Design challenge: {challenge}

Three visual sketch concepts have been created for this challenge. For each sketch concept below, provide a brief explanation (1-2 sentences) that describes the DESIGN IDEA or CONCEPT being explored—focus on what design approach or solution concept the image represents, not visual style details.

Sketch concepts:
1. {sketch_prompts[0] if len(sketch_prompts) > 0 else "N/A"}
2. {sketch_prompts[1] if len(sketch_prompts) > 1 else "N/A"}
3. {sketch_prompts[2] if len(sketch_prompts) > 2 else "N/A"}

For each, explain: What design idea or solution approach does this sketch concept explore? What problem does it address or what opportunity does it highlight?

Format as numbered explanations, one per line."""

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a design strategist. For each sketch concept, provide a clear explanation (1-2 sentences) of the DESIGN IDEA or SOLUTION APPROACH being explored. Focus on what the concept represents conceptually, not visual style. Explain what design problem it addresses or what opportunity it highlights.",
                },
                {"role": "user", "content": concept_prompt},
            ],
            temperature=0.7,
            max_tokens=400,
        )
        content = response.choices[0].message.content or ""
        
        # Parse numbered explanations - handle multi-line explanations
        lines = content.split("\n")
        explanations = []
        current_explanation = None
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_explanation:
                    explanations.append(current_explanation)
                    current_explanation = None
                continue
            
            # Check if this line starts a new numbered explanation
            if line[0].isdigit() or line.startswith(("•", "-")):
                # Save previous explanation if exists
                if current_explanation:
                    explanations.append(current_explanation)
                
                # Start new explanation
                for prefix in ["1.", "2.", "3.", "•", "-"]:
                    if line.startswith(prefix):
                        current_explanation = line[len(prefix) :].strip()
                        break
                else:
                    current_explanation = line
            elif current_explanation:
                # Continue building current explanation
                current_explanation += " " + line
            else:
                # First explanation without number
                current_explanation = line
        
        # Add last explanation
        if current_explanation:
            explanations.append(current_explanation)
        
        # Clean up and ensure we have 3
        cleaned = [exp.strip() for exp in explanations[:3] if exp.strip()]
        
        # Ensure we have 3 explanations
        while len(cleaned) < 3:
            cleaned.append("This sketch explores a design approach for addressing the challenge.")
        
        return cleaned[:3]
    except Exception as e:
        # Fallback to using sketch prompts as explanations
        import sys
        print(f"Warning: Failed to generate sketch concepts: {e}", file=sys.stderr)
        return sketch_prompts[:3]


async def generate_all(challenge: str) -> Dict[str, Any]:
    """
    Generate all outputs in parallel for speed.
    Returns dict with 'hmw', 'sketch_prompts', 'images', 'layouts', 'sketch_concepts'.
    """
    # Generate HMW, sketch prompts, and layouts in parallel
    hmw_task = generate_hmw_statements(challenge)
    sketch_task = generate_sketch_prompts(challenge)
    layout_task = generate_layout_suggestions(challenge)

    hmw_results, sketch_prompts, layouts = await asyncio.gather(
        hmw_task, sketch_task, layout_task
    )

    # Then generate images from sketch prompts
    images = await generate_images(sketch_prompts)
    
    # Generate conceptual explanations for each sketch
    sketch_concepts = await generate_sketch_concepts(challenge, sketch_prompts)

    return {
        "hmw": hmw_results,
        "sketch_prompts": sketch_prompts,
        "images": images,
        "layouts": layouts,
        "sketch_concepts": sketch_concepts,
    }
