"""
Persistent Memory Module for UDA-Hub

Provides long-term memory storage using SQLite for:
- Conversation history per customer
- Resolved tickets for context
- Customer preferences

This enables personalized, context-aware support across sessions.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


# Database path - go up from tools -> agentic -> solution -> data/core
DB_PATH = Path(__file__).parent.parent.parent / "data" / "core" / "udahub.db"


def get_connection():
    """Get SQLite connection."""
    return sqlite3.connect(str(DB_PATH))


def init_memory_tables():
    """Initialize memory tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create conversation history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            thread_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    
    # Create resolved tickets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resolved_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            ticket_summary TEXT NOT NULL,
            resolution TEXT NOT NULL,
            category TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    
    # Create customer preferences table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_preferences (
            customer_id TEXT PRIMARY KEY,
            preferences TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()


def save_message(customer_id: str, thread_id: str, role: str, content: str):
    """Save a message to conversation history."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO conversation_history (customer_id, thread_id, role, content, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (customer_id, thread_id, role, content, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()


def get_conversation_history(customer_id: str, limit: int = 10) -> list:
    """Get recent conversation history for a customer."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT thread_id, role, content, timestamp
        FROM conversation_history
        WHERE customer_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (customer_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {"thread_id": r[0], "role": r[1], "content": r[2], "timestamp": r[3]}
        for r in rows
    ]


def save_resolved_ticket(customer_id: str, summary: str, resolution: str, category: str = None):
    """Save a resolved ticket for future reference."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO resolved_tickets (customer_id, ticket_summary, resolution, category, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (customer_id, summary, resolution, category, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()


def get_resolved_tickets(customer_id: str, limit: int = 5) -> list:
    """Get previously resolved tickets for a customer."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ticket_summary, resolution, category, timestamp
        FROM resolved_tickets
        WHERE customer_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (customer_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {"summary": r[0], "resolution": r[1], "category": r[2], "timestamp": r[3]}
        for r in rows
    ]


def save_preferences(customer_id: str, preferences: dict):
    """Save or update customer preferences."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO customer_preferences (customer_id, preferences, last_updated)
        VALUES (?, ?, ?)
    """, (customer_id, json.dumps(preferences), datetime.now().isoformat()))
    
    conn.commit()
    conn.close()


def get_preferences(customer_id: str) -> Optional[dict]:
    """Get customer preferences."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT preferences
        FROM customer_preferences
        WHERE customer_id = ?
    """, (customer_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])
    return None


def get_customer_context(customer_id: str) -> dict:
    """
    Get full customer context for personalized support.
    
    Returns conversation history, resolved tickets, and preferences.
    """
    return {
        "conversation_history": get_conversation_history(customer_id),
        "resolved_tickets": get_resolved_tickets(customer_id),
        "preferences": get_preferences(customer_id)
    }


# Initialize tables on import
try:
    init_memory_tables()
except:
    pass  # Database may not exist yet
