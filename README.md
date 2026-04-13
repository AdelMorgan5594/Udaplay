# UDA-Hub Solution

A multi-agent customer support system built for the CultPass cultural experiences platform.

## Requirements

- Python 3.11+
- OpenAI API key

## Setup Instructions

1. Create virtual environment:
   ```bash
   python -m venv udacity_project
   source udacity_project/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

4. Run database setup notebooks in order:
   - 01_external_db_setup.ipynb
   - 02_core_db_setup.ipynb

5. Run the application: 03_agentic_app.ipynb

## Architecture

Uses a Supervisor pattern with 4 specialized agents:

1. **Classifier Agent** - Categorizes tickets by type, intent, urgency
2. **researcher Agent** - Deep investigation for complex account-related issues
3. **Resolver Agent** - Resolves using knowledge base and tools
4. **Escalation Agent** - Handles complex cases for human support

## Tools

1. Account Lookup - Retrieves user account info
2. Subscription Management - Gets subscription details
3. Knowledge Search - Searches 15 support articles

## Memory

- Short-term: LangGraph thread_id for session context
- Long-term: SQLite database for customer history

## Test Cases

6 test scenarios included in 03_agentic_app.ipynb covering:
- FAQ queries
- Subscription questions
- Technical issues
- Billing/refunds
- Login problems
- Premium upgrades

## architecture design could be found under agentic/design/architecture.md
