# app/ws/manager.py
from typing import Set
from fastapi import WebSocket
import asyncio


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        async with self._lock:
            conns = list(self.active_connections)

        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                await self.disconnect(ws)


# Global instance to avoid circular imports
ws_manager = ConnectionManager()
