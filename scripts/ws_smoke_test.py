from __future__ import annotations

import asyncio
import os
import json
from urllib import request

import websockets


BASE_HTTP_URL = os.getenv("RANSOMFORGE_HTTP_URL", "http://127.0.0.1:8000")
BASE_WS_URL = os.getenv("RANSOMFORGE_WS_URL", "ws://127.0.0.1:8000")
WS_URL = f"{BASE_WS_URL.rstrip('/')}/ws"
DEMO_URL = f"{BASE_HTTP_URL.rstrip('/')}/demo/event"


async def trigger_demo_event() -> str:
    def post_demo_event() -> str:
        req = request.Request(DEMO_URL, method="POST")
        with request.urlopen(req, timeout=10) as response:
            return response.read().decode("utf-8")

    return await asyncio.to_thread(post_demo_event)


async def main() -> None:
    async with websockets.connect(WS_URL) as websocket:
        banner = await websocket.recv()
        print(f"banner: {banner}")

        await websocket.send("ping")
        pong = await websocket.recv()
        print(f"ws: {pong}")

        demo_task = asyncio.create_task(trigger_demo_event())
        seen_types = set()
        while True:
            message = await websocket.recv()
            print(f"event: {message}")
            try:
                payload = json.loads(message)
                message_type = payload.get("type")
                if message_type:
                    seen_types.add(message_type)
            except json.JSONDecodeError:
                continue

            if {"NEW_EVENT", "THREAT_UPDATE", "ALERT"}.issubset(seen_types):
                break

            if len(seen_types) >= 3:
                break

        print(f"http: {await demo_task}")

        if "ALERT" not in seen_types:
            print("alert: not emitted on this run (score below threshold or timing window)")
        else:
            print("alert: emitted")


if __name__ == "__main__":
    asyncio.run(main())
