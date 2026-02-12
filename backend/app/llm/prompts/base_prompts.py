"""Base prompt utilities and RAG context formatting."""
from typing import Optional


def build_rag_section(rag_context: Optional[str]) -> str:
    """Build RAG context section for prompts if available."""
    if rag_context and rag_context.strip() and rag_context != "No similar patterns found.":
        return f"""

CONTEXT FROM SIMILAR FRAUD PATTERNS:
{rag_context}

Use this context to inform your analysis, but base your score on the specific transaction details provided below.
"""
    return ""
