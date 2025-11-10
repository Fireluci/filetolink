import logging
from FileStream.utils.database import Database
from FileStream.config import Telegram

logger = logging.getLogger(__name__)
db = Database(Telegram.DATABASE_URL, Telegram.SESSION_NAME)


async def get_file_ids(is_old: bool, db_id: str, multi_clients, message):
    """Fetch or update file_ids for Telegram media."""
    try:
        if not is_old:
            await db.update_file_ids(db_id, await update_file_id(message.id, multi_clients))
            logger.info(f"✅ File IDs updated for DB ID {db_id}")
        else:
            logger.info(f"ℹ️ Skipped update for old file ID {db_id}")
    except Exception as e:
        logger.error(f"❌ Error in get_file_ids: {e}")


async def update_file_id(log_msg_id, multi_clients):
    """Updates file_id for all clients safely."""
    file_ids = {}
    for client in multi_clients.values():
        try:
            # Ensure the client session is active and has .me loaded
            if not getattr(client, "me", None):
                await client.start()
            media = await client.get_messages("me", log_msg_id)
            file_ids[str(client.me.id)] = getattr(media, "file_id", "")
            logger.info(f"✅ Updated file_id for client {client.me.id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to update file_id for a client: {e}")
            continue
    return file_ids


async def get_file_property(db_id: str):
    """Returns file details from database."""
    try:
        return await db.get_file(db_id)
    except Exception as e:
        logger.error(f"Error fetching file properties: {e}")
        return None
