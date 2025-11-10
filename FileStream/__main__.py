import sys
import asyncio
import logging
import traceback
import logging.handlers as handlers
from FileStream.config import Telegram, Server
from aiohttp import web
from pyrogram import idle, Client

from FileStream.bot import FileStream
from FileStream.server import web_server
from FileStream.bot.clients import initialize_clients

# ================================
# Logging Setup
# ================================
logging.basicConfig(
    level=logging.INFO,
    datefmt="%d/%m/%Y %H:%M:%S",
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(stream=sys.stdout),
        handlers.RotatingFileHandler("streambot.log", mode="a", maxBytes=104857600, backupCount=2, encoding="utf-8")
    ],
)

logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

# ================================
# AIOHTTP Web Server
# ================================
server = web.AppRunner(web_server())

loop = asyncio.get_event_loop()

# ================================
# Start Both Bot + Web Server
# ================================
async def start_services():
    print()
    if Telegram.SECONDARY:
        print("------------------ Starting as Secondary Server ------------------")
    else:
        print("------------------- Starting as Primary Server -------------------")
    print()

    # Initialize Pyrogram clients
    await initialize_clients()

    # Start FileStream Bot
    app = Client(
        "FileToLink",
        api_id=Telegram.API_ID,
        api_hash=Telegram.API_HASH,
        bot_token=Telegram.BOT_TOKEN,
        plugins=dict(root="FileStream/bot/plugins")  # <-- ensures all /start, /ban, /status commands load
    )

    await app.start()
    logging.info("✅ Bot client started successfully!")

    # Start web server
    await server.setup()
    site = web.TCPSite(server, host=Server.BIND_ADDRESS, port=Server.PORT)
    await site.start()
    logging.info(f"🌐 Web server started at http://{Server.BIND_ADDRESS}:{Server.PORT}")

    # Keep running
    await idle()
    await app.stop()

# ================================
# Entry Point
# ================================
if __name__ == "__main__":
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        logging.warning("🛑 Stopped by user.")
    except Exception as e:
        logging.error(f"❌ Startup failed: {e}")
        traceback.print_exc()
