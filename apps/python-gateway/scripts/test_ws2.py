import asyncio
import websockets

async def test():
    try:
        async with websockets.connect(
            "ws://127.0.0.1:8000/v1/ws/openclaw",
            extra_headers={"x-openclaw-id": "openclaw-test"}
        ) as ws:
            print("Connected! Waiting for pings...")
            while True:
                msg = await ws.recv()
                print(f"Received: {msg}")
                if "ping" in msg:
                    await ws.send('{"type": "pong"}')
                    print("Sent pong!")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
