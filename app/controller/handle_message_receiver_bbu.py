# app/controller/handle_message_receiver_bbu.py
from app.config.utils import HeartBeat, GetCellParaRsp, GetAppCfgExtRsp, OneUeInfoIndi
import time
import re
import os

import asyncio

from app.db.database import SessionLocal, engine
from app.db import models
from app.db.models import Heartbeat as HeartbeatModel, Crawling as CrawlingModel
from app.ws.manager import ws_manager
from app.ws import runtime

# pastikan table ada (aman walau dipanggil berulang)
models.Base.metadata.create_all(bind=engine)

def save_xml_file(message, source_ip, folder_name, log_message):
    print(log_message)
    xml_pattern = r"<\?xml[\s\S]*"
    xml_match = re.search(xml_pattern, message)

    if xml_match:
        xml_string = xml_match.group(0)

        base_path = os.path.join(os.path.dirname(__file__), '../xml_file')
        os.makedirs(base_path, exist_ok=True)

        full_folder_path = os.path.join(base_path, folder_name)
        os.makedirs(full_folder_path, exist_ok=True)

        file_path = os.path.join(full_folder_path, f"{folder_name}_{source_ip}.xml")
        with open(file_path, "w") as file:
            file.write(xml_string)

        print("File XML telah dibuat di:", os.path.abspath(file_path))
    else:
        print("Tidak ditemukan XML dalam string yang diberikan.")


def RespUdp(message, addr):
    print(f"Message : {message}")
    source_ip = addr[0]
    print("Source IP:", source_ip, "Received message:", message)

    date_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    from app.service.services import upsert_heartbeat, upsert_crawling

    db = SessionLocal()
    try:
        if HeartBeat in message:
            STATE = message.split("STATE[")[1].split("]")[0]
            TEMP = message.split("TEMP[")[1].split("]")[0]
            MODE = message.split("MODE[")[1].split("]")[0]
            CH = message.split(" ")[3]  # contoh: CH-04

            if STATE == "CLOSED":
                STATE = "ONLINE"

            upsert_heartbeat(
                db=db,
                source_ip=source_ip,
                state=STATE,
                temp=TEMP,
                mode=MODE,
                ch=CH,
                timestamp=date_now,
            )
            db.commit()

            # broadcast realtime ke websocket
            payload = {
                "source_ip": source_ip,
                "data": {
                    "STATE": STATE,
                    "TEMP": TEMP,
                    "MODE": MODE,
                    "CH": CH,
                    "timestamp": date_now,
                }
            }

            if runtime.main_loop:
                asyncio.run_coroutine_threadsafe(ws_manager.broadcast(payload), runtime.main_loop)

        elif GetCellParaRsp in message:
            save_xml_file(message, source_ip, 'cellpara', "(CellParaRsp)")

        elif GetAppCfgExtRsp in message:
            save_xml_file(message, source_ip, 'appcfgext', "(AppCfgExtRsp)")

        elif OneUeInfoIndi in message:
            rsrp = message.split("rsrp[")[1].split("]")[0]
            taType = message.split("taType[")[1].split("]")[0]
            ulCqi = message.split("ulCqi[")[1].split("]")[0]
            ulRssi = message.split("ulRssi[")[1].split("]")[0]
            imsi = message.split("imsi[")[1].split("]")[0]

            upsert_crawling(
                db=db,
                timestamp=date_now,
                rsrp=rsrp,
                taType=taType,
                ulCqi=ulCqi,
                ulRssi=ulRssi,
                imsi=imsi,
                ip=source_ip,
                campaign_id=None,
            )
            db.commit()

        else:
            print(" ")

    except Exception as e:
        db.rollback()
        print("DB error:", str(e))
    finally:
        db.close()
