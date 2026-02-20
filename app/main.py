# main.py (atau file main kamu)
import threading
import uvicorn
import time
import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.controller import client_udp
from app.db.database import engine, SessionLocal
from app.db import models
from app.db.seeds import seed_all
from app.ws import runtime
from app.api.routes import distance, websocket, campaign, license, target, crawling, health

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_PATH = os.path.join(BASE_DIR, "docs", "docs.html")

app = FastAPI(
    title="IMSI CATCHER BACKEND",
    description="API untuk IMSI CATCHER BACKEND",
    version="1.0.0"
)

@app.on_event("startup")
async def on_startup():
    runtime.main_loop = asyncio.get_running_loop()
    
    from app.service.timer_service import get_timer_ops_instance
    from app.db.database import SessionLocal
    from app.service.msisdn_service import start_background_msisdn_checker
    
    db = SessionLocal()
    try:
        timer_ops = get_timer_ops_instance()
        timer_ops.recover_active_campaigns(db)
    except Exception as e:
        print(f"Error recovering campaigns: {e}")
    finally:
        db.close()
    
    # Start background MSISDN checker
    try:
        start_background_msisdn_checker(interval_seconds=5)
    except Exception as e:
        print(f"Error starting background MSISDN checker: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
def get_spotlight():
    return FileResponse(DOCS_PATH)

app.include_router(websocket.router)
app.include_router(target.router)
app.include_router(campaign.router)
app.include_router(distance.router)
app.include_router(crawling.router)
app.include_router(license.router)
app.include_router(health.router)


class MyApp:
    def __init__(self):
        super().__init__()

    def init_db(self):
        models.Base.metadata.create_all(bind=engine)        
        db = SessionLocal()
        try:
            seed_all(db)
        finally:
            db.close()

    def start_fastapi_server(self):
        uvicorn.run(app, host="0.0.0.0", port=8888)

    def start_app(self):
        self.init_db()

        api_thread = threading.Thread(target=self.start_fastapi_server, daemon=True)
        api_thread.start()

        for _ in range(50):
            if runtime.main_loop is not None:
                break
            time.sleep(0.1)
        
        from app.service.heartbeat_service import heartbeat_watcher
        runtime.main_loop.call_soon_threadsafe(
            lambda: asyncio.create_task(heartbeat_watcher())
        )

        client_udp()
        print("Server UDP sudah berjalan.........")
