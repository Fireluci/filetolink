# utils/checks.py
from typing import Optional
from database.users_chats_db import db   # your DB module (you already use this)
from utils import temp

async def is_banned_user(user_id: Optional[int]) -> bool:
    """
    Returns True if user is banned.
    Uses in-memory temp.BANNED_USERS for speed, falls back to DB check if needed.
    """
    if not user_id:
        return False
    # fast check: in-memory set loaded at start
    try:
        if user_id in getattr(temp, "BANNED_USERS", set()):
            return True
    except Exception:
        pass

    # fallback: ask DB (implement according to your db API)
    try:
        return await db.is_banned_user(user_id)  # implement this if not present
    except Exception:
        return False

async def is_banned_chat(chat_id: Optional[int]) -> bool:
    if not chat_id:
        return False
    try:
        if chat_id in getattr(temp, "BANNED_CHATS", set()):
            return True
    except Exception:
        pass
    try:
        return await db.is_banned_chat(chat_id)  # implement this if not present
    except Exception:
        return False
