import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from FileStream.utils.database import Database
from FileStream.utils.file_properties import get_file_ids
from FileStream.bot import FileStream, multi_clients
from FileStream.config import Telegram

logger = logging.getLogger(__name__)
db = Database(Telegram.DATABASE_URL, Telegram.SESSION_NAME)


@FileStream.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def private_receive_handler(client: Client, message: Message):
    """Handles files sent by users in private chat."""
    try:
        # Extract file details
        file_name = None
        file_size = None
        file_unique_id = None

        if message.document:
            file_name = message.document.file_name
            file_size = message.document.file_size
            file_unique_id = message.document.file_unique_id
        elif message.video:
            file_name = message.video.file_name or "video.mp4"
            file_size = message.video.file_size
            file_unique_id = message.video.file_unique_id
        elif message.audio:
            file_name = message.audio.file_name or "audio.mp3"
            file_size = message.audio.file_size
            file_unique_id = message.audio.file_unique_id
        else:
            await message.reply_text("⚠️ Unsupported file type.")
            return

        # Add file record to DB
        inserted_id = await db.add_file(
            user_id=message.from_user.id,
            file_name=file_name,
            file_size=file_size,
            file_unique_id=file_unique_id,
        )

        # Update file_id and cache
        await get_file_ids(False, inserted_id, multi_clients, message)

        await message.reply_text(
            "✅ File received successfully.\nGenerating your stream link..."
        )
        logger.info(f"📦 File from {message.from_user.id} stored successfully.")

    except Exception as e:
        logger.error(f"❌ Error handling file upload: {e}")
        await message.reply_text(
            f"❌ An unexpected error occurred.\nError: `{e}`"
        )
