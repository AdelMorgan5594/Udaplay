"""
Researcher Agent - Deep account investigation and context gathering.
"""

import json
from agentic.tools.account_lookup import lookup_account
from agentic.tools.subscription import get_subscription_info


def research_account(user_id: str, ticket_content: str) -> dict:
    """
    Perform deep research on account for complex issues.
    
    Args:
        user_id: The user ID to research
        ticket_content: The ticket content for context
        
    Returns:
        dict with account_info, subscription_info, recommendations
    """
    # Get account information
    account_info = lookup_account(user_id)
    
    # Get subscription details
    subscription_info = get_subscription_info(user_id)
    
    # Analyze the situation
    recommendations = []
    
    # Check subscription status
    if subscription_info:
        status = subscription_info.get("status", "")
        if status == "expired":
            recommendations.append("Subscription has expired - offer renewal options")
        elif status == "cancelled":
            recommendations.append("Subscription was cancelled - check for win-back opportunities")
        elif status == "active":
            recommendations.append("Active subscription - check entitlements match expectations")
    
    # Check for billing-related keywords
    billing_keywords = ["refund", "charge", "payment", "billing", "invoice"]
    if any(kw in ticket_content.lower() for kw in billing_keywords):
        recommendations.append("Billing issue detected - may require finance team review")
    
    # Check for urgency indicators
    urgent_keywords = ["urgent", "immediately", "asap", "critical", "emergency"]
    if any(kw in ticket_content.lower() for kw in urgent_keywords):
        recommendations.append("High urgency detected - prioritize response")
    
    return {
        "user_id": user_id,
        "account_info": account_info,
        "subscription_info": subscription_info,
        "recommendations": recommendations,
        "research_complete": True
    }
