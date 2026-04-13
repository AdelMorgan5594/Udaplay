# UDA-Hub Multi-Agent Support System Architecture

## Overview

This document describes the multi-agent architecture for UDA-Hub's customer support system. The system uses a **Supervisor Pattern** where a classifier agent routes tickets to specialized agents based on ticket content and metadata.

## Architecture Diagram

```
                    ┌─────────────────────────────────────────────────┐
                    │                 USER REQUEST                     │
                    └─────────────────────┬───────────────────────────┘
                                          │
                                          ▼
                    ┌─────────────────────────────────────────────────┐
                    │              CLASSIFIER AGENT                    │
                    │  - Analyzes ticket content                       │
                    │  - Extracts metadata (urgency, category)         │
                    │  - Routes to appropriate agent                   │
                    └─────────────────────┬───────────────────────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
              ▼                           ▼                           ▼
┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│     RESOLVER AGENT      │ │    RESEARCHER AGENT     │ │    ESCALATION AGENT     │
│                         │ │                         │ │                         │
│ - Knowledge base search │ │ - Deep account lookup   │ │ - Human handoff         │
│ - FAQ responses         │ │ - Subscription analysis │ │ - Urgent issues         │
│ - Common issues         │ │ - Historical context    │ │ - Complex problems      │
│ - Confidence scoring    │ │ - Detailed research     │ │ - Create escalation     │
└───────────┬─────────────┘ └───────────┬─────────────┘ └───────────┬─────────────┘
            │                           │                           │
            └───────────────────────────┼───────────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────────────┐
                    │              RESPONSE TO USER                    │
                    └─────────────────────────────────────────────────┘
```

## Agent Roles and Responsibilities

### 1. Classifier Agent (`classifier.py`)
**Role**: Entry point for all tickets. Analyzes and routes requests.

**Responsibilities**:
- Parse incoming ticket content
- Extract metadata (category, urgency, complexity)
- Determine required tools (account lookup, subscription check)
- Assign confidence level to classification
- Route to appropriate downstream agent

**Input**: Raw user message
**Output**: Classification object with category, urgency, routing decision

### 2. Resolver Agent (`resolver.py`)
**Role**: Primary responder for standard support queries.

**Responsibilities**:
- Search knowledge base for relevant articles
- Generate responses based on FAQ content
- Calculate confidence score for responses
- Flag for escalation if confidence is low
- Handle common issues (login, billing, features)

**Input**: Classified ticket, knowledge base articles
**Output**: Response with confidence score, escalation flag

### 3. Researcher Agent (`researcher.py`)
**Role**: Deep investigation for complex account-related issues.

**Responsibilities**:
- Perform detailed account lookups
- Analyze subscription history
- Check previous interactions (long-term memory)
- Compile comprehensive context for resolution
- Support resolver with additional data

**Input**: Ticket requiring account investigation
**Output**: Detailed account context and recommendations

### 4. Escalation Agent (`escalation.py`)
**Role**: Handle tickets requiring human intervention.

**Responsibilities**:
- Create escalation tickets with full context
- Assign priority level based on urgency
- Notify appropriate support tier
- Generate customer-facing response
- Log escalation for tracking

**Input**: Unresolved ticket, resolution attempts
**Output**: Escalation ticket, customer response

## Information Flow

```
User Message
    │
    ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Classification                                            │
│ - Classifier agent analyzes message                               │
│ - Extracts: category, urgency, requires_account_lookup            │
│ - Determines routing: resolver, researcher, or direct escalation  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Research (if needed)                                      │
│ - Researcher agent performs deep account lookup                   │
│ - Retrieves subscription details, history                         │
│ - Checks long-term memory for previous interactions               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: Resolution Attempt                                        │
│ - Resolver agent searches knowledge base                          │
│ - Generates response with confidence score                        │
│ - If confidence < 0.5 → route to escalation                       │
└───────────────────────────────┬──────────────────────────────────┘
                                │
               ┌────────────────┴────────────────┐
               │                                 │
     confidence >= 0.5                  confidence < 0.5
               │                                 │
               ▼                                 ▼
┌──────────────────────────┐      ┌──────────────────────────┐
│ RESPOND TO USER          │      │ STEP 4: Escalation       │
│ - Send resolution        │      │ - Create escalation      │
│ - Log to memory          │      │ - Assign priority        │
└──────────────────────────┘      │ - Notify human agent     │
                                  └──────────────────────────┘
```

## Routing Logic

### Classification Categories
| Category | Route To | Description |
|----------|----------|-------------|
| `general_inquiry` | Resolver | FAQ, how-to questions |
| `technical_issue` | Resolver → Escalation | Login, errors, bugs |
| `billing` | Researcher → Resolver | Payment, refunds |
| `account_management` | Researcher → Resolver | Profile, settings |
| `subscription` | Researcher → Resolver | Plan changes, cancellation |
| `urgent` | Escalation | Critical issues, immediate attention |
| `complaint` | Escalation | Dissatisfied customers |

### Urgency Levels
| Level | Definition | Handling |
|-------|------------|----------|
| `low` | General questions | Standard resolution |
| `medium` | Issues affecting usage | Prioritized resolution |
| `high` | Service disruption | Immediate escalation |
| `critical` | Security, legal, safety | Direct human handoff |

## Tools Integration

### Account Lookup Tool (`account_lookup.py`)
- Queries CultPass database for user information
- Returns account details, subscription status
- Used by: Researcher Agent

### Subscription Tool (`subscription.py`)
- Retrieves subscription plans and history
- Checks entitlements and features
- Used by: Researcher Agent

### Knowledge Search Tool (`knowledge_search.py`)
- Searches FAQ articles in knowledge base
- Returns relevant articles with scores
- Used by: Resolver Agent

## Memory Architecture

### Short-Term Memory (Session)
- **Storage**: LangGraph MemorySaver with thread_id
- **Scope**: Single conversation session
- **Content**: Message history, context

### Long-Term Memory (Persistent)
- **Storage**: SQLite database (udahub.db)
- **Scope**: Cross-session, per-customer
- **Content**: Resolved tickets, preferences, interaction history

## State Management

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add]  # Conversation history
    classification: dict                          # Ticket classification
    confidence: float                             # Resolution confidence
    account_context: dict                         # Account lookup results
    escalation_required: bool                     # Escalation flag
```

## Error Handling

1. **No matching knowledge**: Escalate with "unable to find answer"
2. **Database errors**: Log error, provide generic response
3. **Classification failure**: Default to general inquiry
4. **Tool timeout**: Retry once, then escalate

## Logging Strategy

All agent decisions are logged with:
- Timestamp
- Agent name
- Decision type
- Input summary
- Output/action
- Confidence score

This enables debugging and continuous improvement of the system.
