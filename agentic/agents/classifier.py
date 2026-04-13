"""Classifier Agent - Classifies support tickets."""

import json
import logging
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from agentic.llm_config import get_llm


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("classifier_agent")


SYSTEM_PROMPT = """You are a ticket classifier for CultPass support.

Classify the ticket and respond with JSON only:
{
    "category": "billing/technical/account/subscription/reservation/general",
    "urgency": "low/medium/high/critical",
    "complexity": "simple/moderate/complex",
    "requires_account_lookup": true/false,
    "requires_research": true/false,
    "requires_escalation": true/false,
    "confidence": 0.0-1.0
}

Consider urgency indicators: "urgent", "asap", "immediately" = high/critical
Consider complexity: multiple issues or vague descriptions = complex
"""


def classify_ticket(ticket_content: str, metadata: dict = None) -> dict:
    """
    Classify a support ticket based on content and metadata.
    
    Args:
        ticket_content: The ticket text
        metadata: Optional metadata (date, source, user_tier, etc.)
        
    Returns:
        Classification dict with category, urgency, complexity, confidence
    """
    model = get_llm(model="gpt-4o-mini", temperature=0)
    
    # Include metadata in classification if provided
    context = ticket_content
    if metadata:
        context += f"\n\nMetadata: {json.dumps(metadata)}"
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context)
    ]
    
    response = model.invoke(messages)
    
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)
        
        # Log classification decision
        logger.info(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "agent": "classifier",
            "action": "classify_ticket",
            "category": result.get("category"),
            "urgency": result.get("urgency"),
            "confidence": result.get("confidence", 0.8),
            "requires_escalation": result.get("requires_escalation", False)
        }))
        
        return result
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return {
            "category": "general",
            "urgency": "medium",
            "complexity": "moderate",
            "requires_account_lookup": False,
            "requires_research": False,
            "requires_escalation": False,
            "confidence": 0.5
        }
