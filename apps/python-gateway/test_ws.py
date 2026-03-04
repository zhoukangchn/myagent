import asyncio
import websockets

async def test():
    try:
        async with websockets.connect("ws://127.0.0.1:8000/v1/ws/openclaw") as ws:
            print("Connected!")
            await ws.send('{"type": "ping"}')
            print(f"Received: {await ws.recv()}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
