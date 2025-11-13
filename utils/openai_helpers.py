"""
Placeholder OpenAI helper utilities.

To be implemented in Phase 2 per build plan:
    - Async wrappers around GPT-4 and DALL·E endpoints
    - Structured logging and cost tracking
    - Retry and rate-limit handling
"""

from __future__ import annotations

from typing import Any, Dict, List


class OpenAIClient:
    """Thin wrapper intended to manage OpenAI interactions."""

    def __init__(self) -> None:
        # TODO: Initialize OpenAI client with API key from environment.
        self._client = None

    async def generate_hmw_statements(self, challenge: str) -> List[str]:
        """TODO: return three reframed 'How Might We' statements."""
        raise NotImplementedError

    async def generate_sketch_prompts(self, challenge: str) -> List[str]:
        """TODO: return three concept sketches as text prompts."""
        raise NotImplementedError

    async def generate_layout_suggestions(self, challenge: str) -> List[str]:
        """TODO: return three UI layout suggestions."""
        raise NotImplementedError

    async def generate_images(self, prompts: List[str]) -> List[Dict[str, Any]]:
        """TODO: call DALL·E (or equivalent) to produce images."""
        raise NotImplementedError


