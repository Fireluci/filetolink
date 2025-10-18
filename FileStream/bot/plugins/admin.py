import os
import time
import string
import random
import asyncio
import aiofiles
import datetime

from FileStream.utils.broadcast_helper import send_msg
from FileStream.utils.database import Database
from FileStream.bot import FileStream
from FileStream.server.exceptions import FIleNotFound
from FileStream.config import Telegram
from pyrogram import filters, Client
from pyrogram.types import Message
from pyrogram.enums.parse_mode import ParseMode

db = Database(Telegram.DATABASE_URL, Telegram.SESSION_NAME)
broadcast_ids = {}


# --- 🔒 Global Ban Check (priority 0) ---
@FileStream.on_message(filters.private, group=0)
async def global_ban_check(c: Client, m: Message):
    try:
        if m.from_user and await db.is_user_banned(m.from_user.id):
            await m.reply_text(
                "❌ You are banned. You cannot upload, process, or generate download/stream links.",
                parse_mode=ParseMode.MARKDOWN,
                quote=True
            )
            return True  # Stop all further handlers
    except Exception as e:
        print(f"Ban check error: {e}")


# --- 🔹 Owner Commands --- #

@FileStream.on_message(filters.command("status") & filters.private & filters.user(Telegram.OWNER_ID))
async def status(c: Client, m: Message):
    await m.reply_text(
        text=f"""**Total Users in DB:** `{await db.total_users_count()}`
**Banned Users in DB:** `{await db.total_banned_users_count()}`
**Total Links Generated:** `{await db.total_files()}`""",
        parse_mode=ParseMode.MARKDOWN, quote=True
    )


@FileStream.on_message(filters.command("ban") & filters.private & filters.user(Telegram.OWNER_ID))
async def ban_user(c: Client, m: Message):
    try:
        user_id = int(m.text.split("/ban ")[-1])
    except ValueError:
        await m.reply_text("❌ Invalid user ID.", quote=True)
        return

    if not await db.is_user_banned(user_id):
        try:
            await db.ban_user(user_id)
            await db.delete_user(user_id)
            await m.reply_text(f"`{user_id}` **is Banned!**", parse_mode=ParseMode.MARKDOWN, quote=True)
            if not str(user_id).startswith('-100'):
                await c.send_message(
                    chat_id=user_id,
                    text="**❗️You're Banned!**",
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
        except Exception as e:
            await m.reply_text(f"**Something went wrong: {e}**", parse_mode=ParseMode.MARKDOWN, quote=True)
    else:
        await m.reply_text(f"`{user_id}` **is Already Banned**", parse_mode=ParseMode.MARKDOWN, quote=True)


@FileStream.on_message(filters.command("unban") & filters.private & filters.user(Telegram.OWNER_ID))
async def unban_user(c: Client, m: Message):
    try:
        user_id = int(m.text.split("/unban ")[-1])
    except ValueError:
        await m.reply_text("❌ Invalid user ID.", quote=True)
        return

    if await db.is_user_banned(user_id):
        try:
            await db.unban_user(user_id)
            await m.reply_text(f"`{user_id}` **is Unbanned**", parse_mode=ParseMode.MARKDOWN, quote=True)
            if not str(user_id).startswith('-100'):
                await c.send_message(
                    chat_id=user_id,
                    text="**✅ You Can Use Me Now**",
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
        except Exception as e:
            await m.reply_text(f"**Something went wrong: {e}**", parse_mode=ParseMode.MARKDOWN, quote=True)
