"""
UDA-Hub Multi-Agent Workflow

Architecture: Supervisor Pattern using LangGraph StateGraph
- Classifier: Routes tickets based on content and metadata
- Researcher: Deep account investigation for complex issues
- Resolver: Knowledge-based responses with confidence scoring
- Escalation: Human handoff for low-confidence or complex issues

Memory Architecture:
- Short-term: LangGraph MemorySaver with thread_id (session state)
- Long-term: SQLite persistent storage (cross-session customer context)
"""

import json
import logging
from typing import TypedDict, Annotated, Literal
from datetime import datetime
from operator import add

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Import agents
from agentic.agents.classifier import classify_ticket
from agentic.agents.researcher import research_account
from agentic.agents.resolver import resolve_ticket
from agentic.agents.escalation import create_escalation

# Import tools
from agentic.tools.account_lookup import lookup_account
from agentic.tools.subscription import get_subscription_info
from agentic.tools.knowledge_search import load_knowledge_base

# Import persistent memory
from agentic.tools.memory import (
    save_message,
    get_customer_context,
    save_resolved_ticket,
    init_memory_tables
)

# Initialize memory tables
try:
    init_memory_tables()
except:
    pass

# Set up structured JSON logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workflow")


def log_event(thread_id: str, agent: str, action: str, **kwargs):
    """Structured JSON log entry for all workflow events."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "thread_id": thread_id,
        "agent": agent,
        "action": action,
        **kwargs
    }
    logger.info(json.dumps(log_entry))


class AgentState(TypedDict):
    """State passed between agents."""
    messages: Annotated[list[BaseMessage], add]


def classifier_node(state: AgentState) -> dict:
    """Classify the ticket and determine routing."""
    messages = state.get("messages", [])
    
    # Get ticket content and thread_id from messages
    ticket_content = ""
    thread_id = "unknown"
    customer_id = "default_customer"
    
    for msg in messages:
        if isinstance(msg, HumanMessage):
            ticket_content = msg.content
        if isinstance(msg, SystemMessage) and "ThreadId:" in msg.content:
            thread_id = msg.content.replace("ThreadId: ", "").strip()
            customer_id = f"customer_{thread_id}"
    
    # Save user message to persistent memory (long-term)
    try:
        save_message(customer_id, thread_id, "user", ticket_content)
    except Exception as e:
        log_event(thread_id, "classifier", "memory_save_error", error=str(e))
    
    # Extract metadata (date, source, etc.)
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "source": "chat",
        "thread_id": thread_id
    }
    
    # Classify with metadata
    classification = classify_ticket(ticket_content, metadata)
    
    # Structured log
    log_event(
        thread_id, "classifier", "classify_ticket",
        category=classification.get("category"),
        urgency=classification.get("urgency"),
        confidence=classification.get("confidence"),
        routing_decision="pending"
    )
    
    # Store classification and customer_id in state
    classification["customer_id"] = customer_id
    classification["thread_id"] = thread_id
    return {"messages": [SystemMessage(content=f"Classification: {json.dumps(classification)}")]}


def researcher_node(state: AgentState) -> dict:
    """Deep research for complex account issues."""
    messages = state.get("messages", [])
    
    # Get ticket content and thread_id
    ticket_content = ""
    thread_id = "unknown"
    
    for msg in messages:
        if isinstance(msg, HumanMessage):
            ticket_content = msg.content
        if isinstance(msg, SystemMessage) and "Classification:" in msg.content:
            try:
                classification = json.loads(msg.content.replace("Classification: ", ""))
                thread_id = classification.get("thread_id", "unknown")
            except:
                pass
    
    # Research account (default user for demo)
    research = research_account("a4ab87", ticket_content)
    
    log_event(
        thread_id, "researcher", "research_account",
        recommendations=len(research.get("recommendations", [])),
        research_complete=research.get("research_complete", False)
    )
    
    # Store research in state
    return {"messages": [SystemMessage(content=f"Research: {json.dumps(research)}")]}


def resolver_node(state: AgentState) -> dict:
    """Resolve the ticket using knowledge base with customer context."""
    messages = state.get("messages", [])
    
    # Get ticket content, classification, and research
    ticket_content = ""
    classification = {}
    research = {}
    customer_id = "default_customer"
    thread_id = "unknown"
    
    for msg in messages:
        if isinstance(msg, HumanMessage):
            ticket_content = msg.content
        if isinstance(msg, SystemMessage):
            if "Classification:" in msg.content:
                try:
                    classification = json.loads(msg.content.replace("Classification: ", ""))
                    customer_id = classification.get("customer_id", "default_customer")
                    thread_id = classification.get("thread_id", "unknown")
                except:
                    pass
            if "Research:" in msg.content:
                try:
                    research = json.loads(msg.content.replace("Research: ", ""))
                except:
                    pass
    
    # Load knowledge base
    knowledge_base = load_knowledge_base()
    
    log_event(thread_id, "resolver", "load_knowledge_base", articles_count=len(knowledge_base))
    
    # Get account info from research or lookup
    account_info = research.get("account_info")
    if not account_info and classification.get("requires_account_lookup"):
        account_info = lookup_account("a4ab87")
        log_event(thread_id, "resolver", "tool_usage", tool="account_lookup", success=bool(account_info))
    
    # GET CUSTOMER CONTEXT FROM LONG-TERM MEMORY
    customer_context = None
    try:
        customer_context = get_customer_context(customer_id)
        log_event(
            thread_id, "resolver", "memory_retrieval",
            customer_id=customer_id,
            prior_tickets=len(customer_context.get("resolved_tickets", [])),
            has_preferences=customer_context.get("preferences") is not None
        )
    except Exception as e:
        log_event(thread_id, "resolver", "memory_retrieval_error", error=str(e))
    
    # Resolve with customer context for personalization
    resolution = resolve_ticket(
        ticket_content, 
        classification, 
        knowledge_base, 
        account_info,
        customer_context  # Pass long-term memory
    )
    
    # Store resolution and confidence
    confidence = resolution.get("confidence", 0.5)
    articles_used = resolution.get("articles_used", [])
    
    log_event(
        thread_id, "resolver", "resolve_ticket",
        confidence=confidence,
        resolved=resolution.get("resolved", False),
        escalation_needed=resolution.get("escalation_needed", False),
        articles_used=articles_used,
        kb_grounded=len(articles_used) > 0
    )
    
    # Create response
    response = resolution.get("response", "I apologize, but I couldn't process your request.")
    resolution["customer_id"] = customer_id
    resolution["thread_id"] = thread_id
    resolution_msg = SystemMessage(content=f"Resolution: {json.dumps(resolution)}")
    
    return {"messages": [resolution_msg, AIMessage(content=response)]}


def escalation_node(state: AgentState) -> dict:
    """Handle escalation to human agent."""
    messages = state.get("messages", [])
    
    # Get ticket content and context
    ticket_content = ""
    classification = {}
    resolution = {}
    customer_id = "default_customer"
    thread_id = "unknown"
    
    for msg in messages:
        if isinstance(msg, HumanMessage):
            ticket_content = msg.content
        if isinstance(msg, SystemMessage):
            if "Classification:" in msg.content:
                try:
                    classification = json.loads(msg.content.replace("Classification: ", ""))
                    customer_id = classification.get("customer_id", "default_customer")
                    thread_id = classification.get("thread_id", "unknown")
                except:
                    pass
            if "Resolution:" in msg.content:
                try:
                    resolution = json.loads(msg.content.replace("Resolution: ", ""))
                except:
                    pass
    
    # Create escalation
    escalation = create_escalation(ticket_content, classification, resolution, None)
    response = escalation.get("customer_response", "I'm connecting you with a human agent.")
    
    log_event(
        thread_id, "escalation", "create_escalation",
        priority=escalation.get("priority"),
        suggested_team=escalation.get("suggested_team"),
        reason=resolution.get("escalation_needed", "unknown")
    )
    
    # Save escalation to persistent memory
    try:
        save_message(customer_id, thread_id, "assistant", response)
        save_resolved_ticket(customer_id, ticket_content[:100], "Escalated to human agent", "escalation")
    except Exception as e:
        log_event(thread_id, "escalation", "memory_save_error", error=str(e))
    
    return {"messages": [AIMessage(content=response)]}


def route_after_classifier(state: AgentState) -> Literal["researcher", "resolver", "escalation"]:
    """Route based on classification - considers complexity and research needs."""
    messages = state.get("messages", [])
    thread_id = "unknown"
    
    for msg in reversed(messages):
        if isinstance(msg, SystemMessage) and "Classification:" in msg.content:
            try:
                classification = json.loads(msg.content.replace("Classification: ", ""))
                thread_id = classification.get("thread_id", "unknown")
                
                # Direct escalation for urgent/critical
                if classification.get("urgency") == "critical":
                    log_event(thread_id, "router", "route_decision", decision="escalation", reason="critical_urgency")
                    return "escalation"
                if classification.get("requires_escalation"):
                    log_event(thread_id, "router", "route_decision", decision="escalation", reason="requires_escalation")
                    return "escalation"
                
                # Research for complex account issues
                if classification.get("requires_research"):
                    log_event(thread_id, "router", "route_decision", decision="researcher", reason="requires_research")
                    return "researcher"
                if classification.get("complexity") == "complex":
                    log_event(thread_id, "router", "route_decision", decision="researcher", reason="complex")
                    return "researcher"
                if classification.get("category") in ["billing", "subscription", "account"]:
                    log_event(thread_id, "router", "route_decision", decision="researcher", reason="account_category")
                    return "researcher"
                
                # Default to resolver
                log_event(thread_id, "router", "route_decision", decision="resolver", reason="default")
                return "resolver"
            except:
                pass
    
    return "resolver"


def route_after_resolver(state: AgentState) -> Literal["escalation", "end"]:
    """Route based on resolution confidence and KB-grounding."""
    messages = state.get("messages", [])
    thread_id = "unknown"
    customer_id = "default_customer"
    
    for msg in reversed(messages):
        if isinstance(msg, SystemMessage) and "Resolution:" in msg.content:
            try:
                resolution = json.loads(msg.content.replace("Resolution: ", ""))
                thread_id = resolution.get("thread_id", "unknown")
                customer_id = resolution.get("customer_id", "default_customer")
                
                # Confidence-based escalation
                confidence = resolution.get("confidence", 0.5)
                escalation_needed = resolution.get("escalation_needed", False)
                articles_used = resolution.get("articles_used", [])
                
                if confidence < 0.5 or escalation_needed or len(articles_used) == 0:
                    log_event(
                        thread_id, "router", "route_decision",
                        decision="escalation",
                        confidence=confidence,
                        escalation_needed=escalation_needed,
                        kb_grounded=len(articles_used) > 0
                    )
                    return "escalation"
                
                # Successful resolution - save to long-term memory
                try:
                    response = resolution.get("response", "")
                    save_message(customer_id, thread_id, "assistant", response)
                    save_resolved_ticket(
                        customer_id,
                        response[:100],
                        f"Resolved with KB articles: {', '.join(articles_used)}",
                        resolution.get("category", "general")
                    )
                    log_event(thread_id, "router", "memory_saved", customer_id=customer_id)
                except Exception as e:
                    log_event(thread_id, "router", "memory_save_error", error=str(e))
                
                log_event(
                    thread_id, "router", "route_decision",
                    decision="end",
                    confidence=confidence,
                    resolved=True
                )
                return "end"
                
            except:
                pass
    
    return "end"


def create_workflow():
    """Create the workflow graph with all 4 agents."""
    workflow = StateGraph(AgentState)
    
    # Add all 4 agent nodes
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("resolver", resolver_node)
    workflow.add_node("escalation", escalation_node)
    
    # Set entry point
    workflow.set_entry_point("classifier")
    
    # Conditional routing after classifier
    workflow.add_conditional_edges(
        "classifier",
        route_after_classifier,
        {
            "researcher": "researcher",
            "resolver": "resolver",
            "escalation": "escalation"
        }
    )
    
    # Researcher leads to resolver
    workflow.add_edge("researcher", "resolver")
    
    # Conditional routing after resolver (confidence-based)
    workflow.add_conditional_edges(
        "resolver",
        route_after_resolver,
        {"escalation": "escalation", "end": END}
    )
    
    # Escalation ends the workflow
    workflow.add_edge("escalation", END)
    
    return workflow.compile(checkpointer=MemorySaver())


# Create the orchestrator
orchestrator = create_workflow()
