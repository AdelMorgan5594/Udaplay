"""
LLM Configuration for Vocareum/Udacity Environment

This module provides a configured ChatOpenAI instance that works with
the Vocareum API proxy used in Udacity projects.
"""

import os
from langchain_openai import ChatOpenAI

# Vocareum API base URL
VOCAREUM_API_BASE = "https://openai.vocareum.com/v1"


def get_llm(model: str = "gpt-4o-mini", temperature: float = 0) -> ChatOpenAI:
    """
    Get a configured LLM instance for Vocareum environment.
    
    Args:
        model: The model to use (default: gpt-4o-mini)
        temperature: The temperature setting (default: 0)
        
    Returns:
        Configured ChatOpenAI instance
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("VOCAREUM_API_KEY")
    
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        base_url=VOCAREUM_API_BASE
    )
