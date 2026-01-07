"""
Device endpoints - DATA BBU dan WebSocket realtime
Tags: DATA BBU
"""
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import time

from app.db.database import get_db
from app.db.models import Heartbeat
from app.db.schemas import HeartbeatResponse
from app.service.services import heartbeat_snapshot
from app.ws.manager import ws_manager

router = APIRouter()


# -----------------------------------
# HTTP ENDPOINT /device (DB)
# -----------------------------------
@router.get("/device", response_model=HeartbeatResponse, tags=["DATA BBU"])
def get_heartbeat(db: Session = Depends(get_db)):
    """Ambil semua heartbeat data dari database"""
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
    """
    Summary dari DB:
    - heartbeat: table heartbeat
    - crawling: table crawling
    """
    from app.service.services import generate_summary_db
    data = generate_summary_db(db)
    return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "data": data}


# -----------------------------------
# WEBSOCKET REALTIME /ws/device
# -----------------------------------
@router.websocket("/ws/device")
async def ws_device(websocket: WebSocket):
    """WebSocket endpoint untuk real-time heartbeat updates"""
    await ws_manager.connect(websocket)

    db_gen = get_db()
    db = next(db_gen)

    try:
        await websocket.send_json(heartbeat_snapshot(db))
        while True:
            await websocket.receive_text()  # keepalive (client bisa ping)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    finally:
        db.close()
