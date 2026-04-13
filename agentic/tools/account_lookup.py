"""Account Lookup Tool - Retrieves user account information."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from data.models import cultpass


def get_db_path():
    """Get path to CultPass database."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    solution_dir = os.path.dirname(os.path.dirname(current_dir))
    return os.path.join(solution_dir, "data", "external", "cultpass.db")


def lookup_account(user_id: str) -> dict:
    """Look up user account by ID or email."""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        return {"success": False, "error": "Database not found"}
    
    try:
        engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        user = session.query(cultpass.User).filter(
            (cultpass.User.user_id == user_id) | (cultpass.User.email == user_id)
        ).first()
        
        if user:
            result = {
                "success": True,
                "user": {
                    "user_id": user.user_id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "is_blocked": user.is_blocked
                }
            }
            if user.subscription:
                result["subscription"] = {
                    "status": user.subscription.status,
                    "tier": user.subscription.tier
                }
        else:
            result = {"success": False, "error": "User not found"}
        
        session.close()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}
