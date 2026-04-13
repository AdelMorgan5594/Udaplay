"""Subscription Tool - Retrieves subscription information."""

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


def get_subscription_info(user_id: str) -> dict:
    """Get subscription info for a user."""
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
        
        if not user:
            session.close()
            return {"success": False, "error": "User not found"}
        
        if user.subscription:
            result = {
                "success": True,
                "subscription": {
                    "status": user.subscription.status,
                    "tier": user.subscription.tier,
                    "monthly_quota": user.subscription.monthly_quota
                }
            }
        else:
            result = {"success": True, "subscription": None}
        
        session.close()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}
