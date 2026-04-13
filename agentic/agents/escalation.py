"""Escalation Agent - Handles tickets that need human support."""

import json
import logging
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from agentic.llm_config import get_llm


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("escalation_agent")


SYSTEM_PROMPT = """You are creating an escalation for a support ticket that could not be resolved automatically.

Respond with JSON:
{
    "customer_response": "Message to the customer about escalation",
    "escalation_summary": "Summary for human agent",
    "priority": "low/medium/high/critical",
    "suggested_team": "billing/technical/account/general"
}
"""


def create_escalation(ticket_content: str, classification: dict, resolution: dict, account_info: dict) -> dict:
    """
    Create an escalation for unresolved tickets.
    
    Logs the escalation decision and assigns priority based on classification.
    """
    model = get_llm(model="gpt-4o-mini", temperature=0.3)
    
    context = f"Ticket: {ticket_content}\n"
    if classification:
        context += f"Classification: {json.dumps(classification)}\n"
    if resolution:
        context += f"Resolution Attempt: {json.dumps(resolution)}\n"
    
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
        
        # Log escalation decision
        logger.info(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "agent": "escalation",
            "action": "create_escalation",
            "priority": result.get("priority", "medium"),
            "suggested_team": result.get("suggested_team", "general"),
            "reason": "low_confidence_or_unresolved"
        }))
        
        return result
    except Exception as e:
        logger.error(f"Escalation creation failed: {e}")
        return {
            "customer_response": "I'm connecting you with a human agent who can better assist you.",
            "escalation_summary": ticket_content,
            "priority": "medium",
            "suggested_team": "general"
        }
