"""
Centralized backend LLM prompts package.
Provides section-based prompt templates and builders for Viva and Practice features.
"""

from app.prompts import practice, viva

__all__ = ["viva", "practice"]
