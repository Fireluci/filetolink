import sys
import asyncio
import logging
import traceback
import logging.handlers as handlers
from FileStream.config import Telegram, Server
from aiohttp import web
from pyrogram import idle

# Import the existing client from bot/__init__.py
from FileStream.bot import FileStream, initialize_clients
from FileStream.server import web_server

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
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.INFO)

server = web.AppRunner(web_server())
loop = asyncio.get_event_loop()

# ================================
# Start Bot + Web Server
# ================================
async def start_services():
    print()
    print("------------------- Starting as Primary Server -------------------")
    print()

    await initialize_clients()

    # ✅ Start FileStream (the real bot client)
    await FileStream.start()
    logging.info("✅ FileStream bot started successfully!")

    # ✅ Start the AIOHTTP web server
    await server.setup()
    site = web.TCPSite(server, host=Server.BIND_ADDRESS, port=Server.PORT)
    await site.start()
    logging.info(f"🌐 Web server started at http://{Server.BIND_ADDRESS}:{Server.PORT}")

    # ✅ Keep running both
    await idle()
    await FileStream.stop()

if __name__ == "__main__":
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        logging.warning("🛑 Stopped manually.")
    except Exception as e:
        logging.error(f"❌ Startup failed: {e}")
        traceback.print_exc()
