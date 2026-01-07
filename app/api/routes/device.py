"""
Device endpoints - DATA BBU dan WebSocket realtime
Tags: DATA BBU
"""
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import time
import asyncio

from app.db.database import get_db
from app.db.models import Heartbeat
from app.db.schemas import HeartbeatResponse
from app.service.services import (
    heartbeat_snapshot,
    crawling_snapshot,
    get_sniffing_data_snapshot
)
from app.ws.manager import ws_manager, sniffing_manager

router = APIRouter()


# -----------------------------------
# HTTP ENDPOINT /device (DB)
# -----------------------------------
@router.get("/device", response_model=HeartbeatResponse, tags=["DATA BBU"])
def get_heartbeat(db: Session = Depends(get_db)):
    rows = db.query(Heartbeat).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Data tidak ditemukan atau table heartbeat kosong.")

    data = {
        r.source_ip: {
            "STATE": r.state,
            "TEMP": r.temp,
            "MODE": r.mode,
            "CH": r.ch,
            "timestamp": r.timestamp
        }
        for r in rows
    }

    return {
        "status": "success",
        "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data": data
    }


@router.get("/summary", tags=["DATA BBU"])
def get_summary(db: Session = Depends(get_db)):
    from app.service.services import generate_summary_db
    data = generate_summary_db(db)
    return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "data": data}


# -----------------------------------
# WEBSOCKET REALTIME /ws/device
# -----------------------------------
@router.websocket("/ws/device")
async def ws_device(websocket: WebSocket):
    """
    WebSocket real-time untuk heartbeat monitoring
    
    Response format:
    {
        "status": "success",
        "last_checked": "2026-01-07 16:39:10",
        "data": [
            {
                "IP": "192.168.12.81",
                "STATE": "ONLINE",
                "TEMP": "43",
                "MODE": "TDD-LTE",
                "CH": "CH-01",
                "timestamp": "1234567890.123"
            },
            {
                "IP": "192.168.12.82",
                "STATE": "ONLINE",
                "TEMP": "45",
                "MODE": "TDD-LTE",
                "CH": "CH-01",
                "timestamp": "1234567890.123"
            }
        ]
    }
    """
    await ws_manager.connect(websocket)

    db_gen = get_db()
    db = next(db_gen)

    try:
        # Send initial snapshot
        await websocket.send_json(heartbeat_snapshot(db))
        
        # Send updates every 2 seconds
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            except asyncio.TimeoutError:
                pass
            
            snapshot = heartbeat_snapshot(db)
            await websocket.send_json(snapshot)
            
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    finally:
        db.close()


@router.websocket("/ws/data_imsi")
async def ws_data_imsi(websocket: WebSocket, campaign_id: int = None):
    await ws_manager.connect(websocket)

    db_gen = get_db()
    db = next(db_gen)

    try:
        await websocket.send_json(crawling_snapshot(db, campaign_id=campaign_id))
        while True:
            await websocket.receive_text()  # keepalive (client bisa ping)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    finally:
        db.close()

# -----------------------------------
# WEBSOCKET REALTIME /ws/sniffing
# -----------------------------------
@router.websocket("/ws/sniffing")
async def ws_sniffing(websocket: WebSocket):
    await sniffing_manager.connect(websocket)

    db_gen = get_db()
    db = next(db_gen)

    try:
        # Send initial snapshot
        snapshot = get_sniffing_data_snapshot(db)
        await websocket.send_json({
            "type": "sniffing_snapshot",
            "timestamp": time.time(),
            "data": snapshot
        })

        # Send updates setiap 2 detik
        while True:
            try:
                # Receive with timeout untuk detect disconnect
                await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            except asyncio.TimeoutError:
                # Timeout OK, continue to send updates
                pass

            # Get updated snapshot dan broadcast
            snapshot = get_sniffing_data_snapshot(db)
            await websocket.send_json({
                "type": "sniffing_update",
                "timestamp": time.time(),
                "data": snapshot
            })

    except WebSocketDisconnect:
        await sniffing_manager.disconnect(websocket)
    finally:
        db.close()
