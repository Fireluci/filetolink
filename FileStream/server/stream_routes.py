import logging
import asyncio
from aiohttp import web
from FileStream.utils.custom_dl import ByteStreamer
from FileStream.bot import multi_clients

logger = logging.getLogger(__name__)

# ======================================================
# Helper function to handle safe streaming (no crash)
# ======================================================

async def safe_stream_response(response, generator):
    """
    Handles client disconnects and socket errors gracefully.
    Prevents 'socket.send() raised exception' spam.
    """
    try:
        async for chunk in generator:
            await response.write(chunk)
    except (ConnectionResetError, OSError, asyncio.CancelledError) as e:
        logger.warning(f"⚠️ Client disconnected or socket error: {e}")
    finally:
        try:
            await response.write_eof()
        except Exception:
            pass

# ======================================================
# Main streaming route
# ======================================================

routes = web.RouteTableDef()

@routes.get("/stream/{message_id}")
async def stream_handler(request: web.Request):
    """
    Streams Telegram files through HTTP with retry-safe handling.
    """
    try:
        message_id = int(request.match_info["message_id"])
        offset = int(request.query.get("offset", 0))
        limit = 1024 * 1024  # 1MB per chunk

        # Select a client from multi_clients (first one if only one)
        client = next(iter(multi_clients.values()))
        streamer = ByteStreamer(client)

        # Fetch message by ID
        message = await client.get_messages("me", message_id)
        if not message or not (message.document or message.video):
            return web.Response(text="Invalid or missing file.", status=400)

        # Setup HTTP response
        response = web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Disposition": f'attachment; filename="{message.document.file_name if message.document else "file.bin"}"',
                "Accept-Ranges": "bytes"
            },
        )
        await response.prepare(request)

        # Stream content safely
        generator = streamer.yield_file(client, message, offset, limit)
        await safe_stream_response(response, generator)

        return response

    except Exception as e:
        logger.error(f"❌ Stream handler error: {e}")
        return web.Response(text=f"Internal server error: {e}", status=500)


# ======================================================
# Route registration function
# ======================================================

def setup_routes(app: web.Application):
    """
    Registers all streaming routes into aiohttp app.
    """
    app.add_routes(routes)
    logger.info("✅ Stream routes registered successfully.")


# ======================================================
# Keep-Alive settings for stability (Koyeb / Heroku)
# ======================================================

def setup_keepalive(app: web.Application):
    """
    Adds keep-alive configuration to reduce dropped connections.
    """
    app._keepalive_timeout = 120  # 2 minutes
    logger.info("🟢 Keep-alive timeout set to 120s.")
