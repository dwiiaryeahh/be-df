# app/controller/handle_message_receiver_bbu.py
from app.config.utils import HeartBeat, GetCellParaRsp, GetAppCfgExtRsp, OneUeInfoIndi, GPSInfoIndi
import time
import re
import os

import asyncio

from app.db.database import SessionLocal, engine
from app.db import models
from app.db.models import Heartbeat as HeartbeatModel, Crawling as CrawlingModel
from app.service.services import insert_sniffer_nmmcfg, reset_nmmcfg
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

    from app.service.services import (
        upsert_heartbeat, 
        upsert_crawling, 
        insert_or_update_gps, 
        update_status_ip_sniffer,
        get_provider_data
    )

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

            from app.service.services import get_latest_campaign_id
            campaign_id = get_latest_campaign_id(db)

            upsert_crawling(
                db=db,
                timestamp=date_now,
                rsrp=rsrp,
                taType=taType,
                ulCqi=ulCqi,
                ulRssi=ulRssi,
                imsi=imsi,
                ip=source_ip,
                campaign_id=campaign_id,
            )
            db.commit()

            payload = {
                "imsi": imsi,
                "campaign_id": campaign_id,
                "data": {
                    "timestamp": date_now,
                    "rsrp": rsrp,
                    "taType": taType,
                    "ulCqi": ulCqi,
                    "ulRssi": ulRssi,
                    "ip": source_ip,
                    "campaign_id": campaign_id,
                }
            }

            if runtime.main_loop:
                asyncio.run_coroutine_threadsafe(ws_manager.broadcast(payload), runtime.main_loop)

        elif GPSInfoIndi in message:
            latitude = message.split("latitude[")[1].split("]")[0]
            longitude = message.split("longitude[")[1].split("]")[0]
            date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print("GPS Info - Latitude:", latitude, "Longitude:", longitude, "Date:", date)
            insert_or_update_gps(latitude, longitude, date)

        elif "SnifferRsltIndi" in message:
            start = 0
            stop = 2

            if "[-1]" not in message:
                pattern = r'erfcn\[(\d+)\],pci\[(\d+)\],rsrp\[(-?\d+)\]'
                match = re.search(pattern, message)

                print("msgggg", message)
                if match:
                    earfcn_value = int(match.group(1))
                    pci_value = match.group(2)
                    rsrp_value = match.group(3)

                    prov = get_provider_data(db, earfcn_value)

                    insert_sniffer_nmmcfg(
                        db=db,
                        ip=source_ip,
                        msg=message,
                        status=start,
                        arfcn=earfcn_value,
                        operator=prov["operator"],
                        band=prov["band"],
                        dl_freq=prov["dl_freq"],
                        ul_freq=prov["ul_freq"],
                        pci=str(pci_value) if pci_value else None,
                        rsrp=str(rsrp_value) if rsrp_value else None,
                    )

                    update_status_ip_sniffer(source_ip, 'scan', 1, db)

            else:
                print("masuk -1 nih<<<<<<<", message)
                time.sleep(1)
                update_status_ip_sniffer(source_ip, 'scan', -1, db)


        elif "StartSniffer" in message:
            RESULT = message.split("RESULT[")[1].split("]")[0]
            print("RESULT SNIF", RESULT)
            reset_nmmcfg(db)
            update_status_ip_sniffer(source_ip, 'scan', 1, db)

            if RESULT == "PARA_ERROR":
                # PARA_ERROR menandakan modul sniffer tidak ada
                update_status_ip_sniffer(source_ip, 'status', 0, db)

        else:
            print(" ")

    except Exception as e:
        db.rollback()
        print("DB error:", str(e))
    finally:
        db.close()
