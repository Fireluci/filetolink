import asyncio
import logging
from typing import Dict
from FileStream.bot import work_loads
from pyrogram import Client, raw
from .file_properties import get_file_ids
from pyrogram.file_id import FileId
from pyrogram.types import Message

logger = logging.getLogger(__name__)

class ByteStreamer:
    def __init__(self, client: Client):
        self.clean_timer = 30 * 60
        self.client: Client = client
        self.cached_file_ids: Dict[str, FileId] = {}
        asyncio.create_task(self.clean_cache())

    async def get_file_properties(self, db_id: str, multi_clients) -> FileId:
        if not db_id in self.cached_file_ids:
            logging.debug("Before Calling generate_file_properties")
            await self.generate_file_properties(db_id, multi_clients)
            logging.debug(f"Cached file properties for file with ID {db_id}")
        return self.cached_file_ids[db_id]

    async def generate_file_properties(self, db_id: str, multi_clients):
        file = await get_file_ids(db_id, multi_clients)
        self.cached_file_ids[db_id] = file

    async def clean_cache(self):
        while True:
            await asyncio.sleep(self.clean_timer)
            self.cached_file_ids.clear()

    async def yield_file(self, client, message: Message, offset: int, limit: int = 1024 * 1024):
        """Stream Telegram media with retry-safe connection handling."""
        file_id = message.document.file_id if message.document else message.video.file_id
        file_info = self.cached_file_ids.get(file_id)
        if not file_info:
            file_info = await self.get_file_properties(file_id, client)
        file_ref = file_info.file_reference

        while True:
            try:
                media_session = await client.storage.get_session()
                result = await media_session.invoke(
                    raw.functions.upload.GetFile(
                        location=raw.types.InputDocumentFileLocation(
                            id=file_info.media_id,
                            access_hash=file_info.access_hash,
                            file_reference=file_ref
                        ),
                        offset=offset,
                        limit=limit
                    )
                )
                yield result.bytes
                break  # successful — stop retry loop

            except OSError as e:
                logger.warning(f"Connection lost during stream (offset={offset}): {e}. Retrying...")
                await asyncio.sleep(2)
                continue  # retry on connection drop

            except Exception as e:
                logger.error(f"Unexpected error while streaming: {e}")
                break
