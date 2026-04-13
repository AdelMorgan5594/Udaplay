"""Knowledge Search Tool - Searches knowledge base articles."""

import os
import json
from typing import List


def get_articles_path():
    """Get path to knowledge base articles."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    solution_dir = os.path.dirname(os.path.dirname(current_dir))
    return os.path.join(solution_dir, "data", "external", "cultpass_articles.jsonl")


def load_knowledge_base() -> List[dict]:
    """Load all articles from the knowledge base."""
    articles_path = get_articles_path()
    
    if not os.path.exists(articles_path):
        return []
    
    articles = []
    with open(articles_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    articles.append(json.loads(line))
                except:
                    continue
    
    return articles


def search_knowledge(query: str) -> List[dict]:
    """Search knowledge base for relevant articles."""
    articles = load_knowledge_base()
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
    return [r["article"] for r in results[:3]]
