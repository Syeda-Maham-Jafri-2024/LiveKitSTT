# import websocket

# ws_url = "wss://speechtotext-n1513et7.livekit.cloud/agent"
# ws = websocket.WebSocket()
# try:
#     ws.connect(ws_url)
#     print("Connected successfully!")
# except Exception as e:
#     print("Failed to connect:", e)


import os
from dotenv import load_dotenv

load_dotenv()
print("API Key:", os.getenv("LIVEKIT_API_KEY"))
print("API Secret:", os.getenv("LIVEKIT_API_SECRET"))
