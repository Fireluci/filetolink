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

# --- 🔒 Global Ban Check for all private messages ---
@FileStream.on_message(filters.private, group=0)  # highest priority
async def global_ban_check(c: Client, m: Message):
    try:
        if m.from_user and await db.is_user_banned(m.from_user.id):
            await m.reply_text(
                "❌ You are banned. You cannot upload, process, or download any files.",
                parse_mode=ParseMode.MARKDOWN,
                quote=True
            )
            return  # Stop further handlers
    except Exception as e:
        print(f"Ban check error: {e}")


# --- 🔹 Owner Commands --- #

@FileStream.on_message(filters.command("status") & filters.private & filters.user(Telegram.OWNER_ID))
async def status(c: Client, m: Message):
    await m.reply_text(
        text=f"""**Total Users in DB:** `{await db.total_users_count()}`
**Banned Users in DB:** `{await db.total_banned_users_count()}`
**Total Links Generated:** `{await db.total_files()}`""",
        parse_mode=ParseMode.MARKDOWN,
        quote=True
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
    else:
        await m.reply_text(f"`{user_id}` **is not Banned**", parse_mode=ParseMode.MARKDOWN, quote=True)


@FileStream.on_message(filters.command("broadcast") & filters.private & filters.user(Telegram.OWNER_ID) & filters.reply)
async def broadcast_(c: Client, m: Message):
    all_users = await db.get_all_users()
    broadcast_msg = m.reply_to_message

    # Generate unique broadcast ID
    while True:
        broadcast_id = ''.join(random.choice(string.ascii_letters) for _ in range(3))
        if not broadcast_ids.get(broadcast_id):
            break

    out = await m.reply_text("Broadcast initiated! You will get a log file when done.")
    start_time = time.time()
    total_users = await db.total_users_count()
    done = 0
    failed = 0
    success = 0

    broadcast_ids[broadcast_id] = dict(total=total_users, current=done, failed=failed, success=success)

    async with aiofiles.open('broadcast.txt', 'w') as broadcast_log_file:
        async for user in all_users:
            sts, msg = await send_msg(user_id=int(user['id']), message=broadcast_msg)
            if msg:
                await broadcast_log_file.write(msg)
            if sts == 200:
                success += 1
            else:
                failed += 1
            if sts == 400:
                await db.delete_user(user['id'])
            done += 1
            if broadcast_ids.get(broadcast_id) is None:
                break
            broadcast_ids[broadcast_id].update(dict(current=done, failed=failed, success=success))
            try:
                await out.edit_text(f"Broadcast Status\n\ncurrent: {done}\nfailed: {failed}\nsuccess: {success}")
            except:
                pass

    if broadcast_ids.get(broadcast_id):
        broadcast_ids.pop(broadcast_id)

    completed_in = datetime.timedelta(seconds=int(time.time() - start_time))
    await asyncio.sleep(3)
    await out.delete()

    if failed == 0:
        await m.reply_text(
            f"Broadcast completed in `{completed_in}`\n\nTotal users {total_users}.\nDone: {done}, Success: {success}, Failed: {failed}.",
            quote=True
        )
    else:
        await m.reply_document(
            document='broadcast.txt',
            caption=f"Broadcast completed in `{completed_in}`\n\nTotal users {total_users}.\nDone: {done}, Success: {success}, Failed: {failed}.",
            quote=True
        )
    os.remove('broadcast.txt')


@FileStream.on_message(filters.command("del") & filters.private & filters.user(Telegram.OWNER_ID))
async def delete_file(c: Client, m: Message):
    file_id = m.text.split(" ")[-1]
    try:
        file_info = await db.get_file(file_id)
    except FIleNotFound:
        await m.reply_text("**File Already Deleted**", quote=True)
        return

    await db.delete_one_file(file_info['_id'])
    await db.count_links(file_info['user_id'], "-")
    await m.reply_text("**File Deleted Successfully!**", quote=True)


# --- 🔹 General message handler for non-banned users ---
@FileStream.on_message(filters.private, group=1)  # group=1 runs after ban check
async def handle_user_messages(c: Client, m: Message):
    # Here you can process files, generate links, etc.
    # Since banned users are blocked at group=0, only non-banned users reach this
    pass
