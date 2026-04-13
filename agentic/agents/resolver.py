"""Resolver Agent - Resolves support tickets using knowledge base."""

import json
import logging
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from agentic.llm_config import get_llm


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("resolver_agent")


SYSTEM_PROMPT = """You are a CultPass support agent. Use the knowledge base to help customers.

IMPORTANT: Only respond based on the knowledge base articles provided. If no relevant article found, set confidence to 0.3 or lower.

Respond with JSON:
{
    "response": "Your response to the customer",
    "resolved": true/false,
    "escalation_needed": true/false,
    "confidence": 0.0-1.0,
    "articles_used": ["article titles used"]
}

Confidence guide:
- 0.9-1.0: Exact match in knowledge base
- 0.7-0.9: Good match with relevant article
- 0.5-0.7: Partial match, some uncertainty
- 0.3-0.5: Weak match, likely needs escalation
- 0.0-0.3: No relevant knowledge found, escalate
"""


def search_knowledge_base(query: str, articles: list) -> list:
    """Simple keyword search of knowledge base."""
    query_lower = query.lower()
    results = []
    
    for article in articles:
        score = 0
        title = article.get("title", "").lower()
        content = article.get("content", "").lower()
        
        for word in query_lower.split():
            if len(word) > 3:
                if word in title:
                    score += 3
                if word in content:
                    score += 1
        
        if score > 0:
            results.append({"article": article, "score": score})
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:3]


def resolve_ticket(ticket_content: str, classification: dict, knowledge_base: list, account_info: dict = None, customer_context: dict = None) -> dict:
    """
    Resolve a support ticket using knowledge base.
    
    CRITICAL: If no relevant KB articles found, MUST escalate.
    All responses must be grounded in KB articles.
    
    Args:
        ticket_content: The ticket text
        classification: Ticket classification
        knowledge_base: List of KB articles
        account_info: Optional account info
        customer_context: Optional historical customer context (long-term memory)
    
    Returns:
        Response dict with confidence score and escalation decision
    """
    # Search KB first
    relevant = search_knowledge_base(ticket_content, knowledge_base)
    retrieved_titles = [item["article"]["title"] for item in relevant]
    
    # Log tool usage (structured JSON)
    logger.info(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "agent": "resolver",
        "action": "knowledge_search",
        "query": ticket_content[:100],
        "articles_found": len(relevant),
        "article_titles": retrieved_titles
    }))
    
    # CRITICAL: Force escalation if no KB articles found
    if not relevant:
        logger.info(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "agent": "resolver",
            "action": "force_escalation",
            "reason": "no_relevant_kb_articles",
            "confidence": 0.2
        }))
        return {
            "response": "I apologize, but I don't have specific information about this in our knowledge base. Let me connect you with a specialist who can help.",
            "resolved": False,
            "escalation_needed": True,
            "confidence": 0.2,
            "articles_used": []
        }
    
    # Build context from KB articles
    model = get_llm(model="gpt-4o-mini", temperature=0.3)
    
    context = "Knowledge Base Articles:\n"
    for item in relevant:
        article = item["article"]
        context += f"- {article['title']}: {article['content']}\n"
    
    if account_info:
        context += f"\nAccount Info: {json.dumps(account_info)}"
    
    # Add customer history for personalization (long-term memory)
    if customer_context:
        history = customer_context.get("resolved_tickets", [])
        if history:
            context += f"\nPrevious Interactions: Customer has {len(history)} prior resolved tickets."
            for prev in history[:2]:  # Last 2 tickets
                context += f"\n- {prev.get('summary', 'N/A')}"
        prefs = customer_context.get("preferences", {})
        if prefs:
            context += f"\nCustomer Preferences: {json.dumps(prefs)}"
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Ticket: {ticket_content}\n\nClassification: {json.dumps(classification)}\n\n{context}")
    ]
    
    response = model.invoke(messages)
    
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)
        
        # ENFORCE KB-GROUNDING: If no articles_used, force escalation
        articles_used = result.get("articles_used", [])
        if not articles_used or len(articles_used) == 0:
            logger.info(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "agent": "resolver",
                "action": "force_escalation",
                "reason": "no_articles_used_in_response",
                "confidence": 0.3
            }))
            result["resolved"] = False
            result["escalation_needed"] = True
            result["confidence"] = min(result.get("confidence", 0.5), 0.3)
        
        # Log resolution decision (structured JSON)
        logger.info(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "agent": "resolver",
            "action": "resolve_ticket",
            "resolved": result.get("resolved", False),
            "confidence": result.get("confidence", 0.5),
            "escalation_needed": result.get("escalation_needed", False),
            "articles_used": result.get("articles_used", []),
            "kb_grounded": len(result.get("articles_used", [])) > 0
        }))
        
        return result
    except Exception as e:
        # On parse failure, escalate (don't return resolved=True)
        logger.error(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "agent": "resolver",
            "action": "parse_error",
            "error": str(e),
            "escalation_needed": True
        }))
        return {
            "response": "I need to connect you with a specialist to ensure you get accurate help.",
            "resolved": False,
            "escalation_needed": True,
            "confidence": 0.2,
            "articles_used": []
        }
