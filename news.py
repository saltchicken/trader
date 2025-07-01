import asyncio
import websockets
import json
import os

from dotenv import load_dotenv

load_dotenv()
# Your API keys
API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")

# The test endpoint (use /v2/stocks for live data)
WS_URL = "wss://stream.data.alpaca.markets/v1beta1/news"


async def connect():
    async with websockets.connect(WS_URL) as websocket:
        # Send authentication message
        auth_msg = {"action": "auth", "key": API_KEY, "secret": SECRET_KEY}
        await websocket.send(json.dumps(auth_msg))
        print("-> Sent auth message")

        # Wait for confirmation
        response = await websocket.recv()
        print("<- Auth response:", response)

        # Subscribe to a data stream (e.g., stock trades or news)
        # News only available on live endpoint (not test), so here we do trades:
        subscribe_msg = {
            "action": "subscribe",
            "trades": [],
            "quotes": [],
            "bars": [],
            "news": ["*"],  # Add "news": ["*"] on live endpoint for real-time news
        }
        await websocket.send(json.dumps(subscribe_msg))
        print("-> Sent subscription message")

        # Listen for messages
        while True:
            message = await websocket.recv()
            print("<-", message)


asyncio.run(connect())
