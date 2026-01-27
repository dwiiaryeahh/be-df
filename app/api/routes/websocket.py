from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import time
from app.db.database import get_db
from app.service.sniffer_service import (
    get_sniffing_progress,
    get_heartbeat_sniff_status
)
from app.ws.manager import ws_manager, sniffing_manager
from app.ws.events import event_bus

router = APIRouter()
@router.websocket("/ws/heartbeat")
async def ws_device(websocket: WebSocket):
    await ws_manager.connect(websocket)
    sub_id = None

    try:
        # Create callback untuk receive data dari event bus
        async def on_heartbeat_data(data: dict):
            try:
                await websocket.send_json(data)
            except Exception as e:
                import traceback
                print(f"[ERROR] ws_device send error: {e}")
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        # Subscribe ke heartbeat events
        sub_id = event_bus.subscribe_heartbeat(on_heartbeat_data)

        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"[ERROR] ws_device receive error: {e}")
                break
            
    finally:
        if sub_id is not None:
            event_bus.unsubscribe_heartbeat(sub_id)
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/data_imsi")
async def ws_data_imsi(websocket: WebSocket, campaign_id: int = None):
    await ws_manager.connect(websocket)
    sub_id = None

    try:
        # Create callback untuk receive data dari event bus
        async def on_crawling_data(data: dict):
            try:
                # Filter berdasarkan campaign_id jika di-specify
                if campaign_id is not None and data.get("campaign_id") != campaign_id:
                    return
                await websocket.send_json(data)
            except Exception as e:
                import traceback
                print(f"[ERROR] ws_data_imsi send error: {e}")
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        # Subscribe ke crawling events
        sub_id = event_bus.subscribe_crawling(on_crawling_data)

        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"[ERROR] ws_data_imsi receive error: {e}")
                break
            
    finally:
        if sub_id is not None:
            event_bus.unsubscribe_crawling(sub_id)
        await ws_manager.disconnect(websocket)

@router.websocket("/ws/sniffing")
async def ws_sniffing(websocket: WebSocket):
    await sniffing_manager.connect(websocket)
    sub_id = None

    try:
        # Create callback untuk receive data dari event bus
        async def on_sniffing_data(data: dict):
            try:
                await websocket.send_json(data)
            except Exception as e:
                import traceback
                print(f"[ERROR] ws_sniffing send error: {e}")
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        # Subscribe ke sniffing events
        sub_id = event_bus.subscribe_sniffing(on_sniffing_data)

        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"[ERROR] ws_sniffing receive error: {e}")
                break
            
    finally:
        if sub_id is not None:
            event_bus.unsubscribe_sniffing(sub_id)
        await sniffing_manager.disconnect(websocket)


@router.websocket("/ws/sniffing/state")
async def ws_sniffing_state(websocket: WebSocket):
    await ws_manager.connect(websocket)
    sub_id = None

    db_gen = get_db()
    db = next(db_gen)

    try:
        # Send initial state
        progress = get_sniffing_progress(db)
        heartbeat_status = get_heartbeat_sniff_status(db)
        await websocket.send_json({
            "type": "sniffing_state",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "progress": progress,
            "heartbeat_status": heartbeat_status
        })

        # Create callback untuk update saat ada sniffing data baru
        async def on_sniffing_update(data: dict):
            try:
                # Refresh data dari DB
                progress = get_sniffing_progress(db)
                heartbeat_status = get_heartbeat_sniff_status(db)
                await websocket.send_json({
                    "type": "sniffing_state",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "progress": progress,
                    "heartbeat_status": heartbeat_status
                })
            except Exception as e:
                import traceback
                print(f"[ERROR] ws_sniffing_state send error: {e}")
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        # Subscribe ke sniffing events untuk real-time updates
        sub_id = event_bus.subscribe_sniffing(on_sniffing_update)

        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"[ERROR] ws_sniffing_state receive error: {e}")
                break
            
    finally:
        if sub_id is not None:
            event_bus.unsubscribe_sniffing(sub_id)
        db.close()
        await ws_manager.disconnect(websocket)
