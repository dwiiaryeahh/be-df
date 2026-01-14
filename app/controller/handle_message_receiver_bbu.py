# app/controller/handle_message_receiver_bbu.py
from app.config.utils import HeartBeat, GetCellParaRsp, GetAppCfgExtRsp, OneUeInfoIndi, GPSInfoIndi
import time
import re
import os
import asyncio
from app.db.database import SessionLocal, engine
from app.db import models
from app.service.heartbeat_service import get_heartbeat_by_ip
from app.service.services import provider_mapping
from app.service.sniffer_service import insert_sniffer_nmmcfg, reset_nmmcfg
from app.ws.events import event_bus

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

    from app.service.services import get_provider_data
    from app.service.heartbeat_service import upsert_heartbeat, update_status_ip_sniffer
    from app.service.crawling_service import upsert_crawling
    from app.service.gps_service import upsert_gps, get_gps_data

    db = SessionLocal()
    try:
        if HeartBeat in message:
            STATE = message.split("STATE[")[1].split("]")[0]
            TEMP = message.split("TEMP[")[1].split("]")[0]
            MODE = message.split("MODE[")[1].split("]")[0]
            BAND = message.split("BAND[")[1].split("]")[0]
            CH = message.split(" ")[3]

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
                band=BAND
            )
            db.commit()

            heartbeat_data = get_heartbeat_by_ip(db, source_ip)
            start_imsi = heartbeat_data.mcc + heartbeat_data.mnc if heartbeat_data else ""

            heartbeat_data = {
                "type": "heartbeat",
                "ip": source_ip,
                "state": STATE,
                "temp": TEMP,
                "mode": MODE,
                "ch": CH,
                "band": BAND or heartbeat_data.band,
                "provider": provider_mapping(start_imsi),
                "mcc": heartbeat_data.mcc,
                "mnc": heartbeat_data.mnc,
                "arfcn": heartbeat_data.arfcn,
                "timestamp": date_now
            }
            asyncio.run(event_bus.send_heartbeat(heartbeat_data))

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

            from app.service.campaign_service import get_latest_campaign_id
            campaign_id = get_latest_campaign_id(db)
            gps = get_gps_data(db)

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

            crawling_data = {
                "type": "crawling",
                "imsi": imsi,
                "timestamp": date_now,
                "rsrp": rsrp,
                "taType": taType,
                "ulCqi": ulCqi,
                "ulRssi": ulRssi,
                "ip": source_ip,

                "campaign_id": campaign_id
            }
            asyncio.run(event_bus.send_crawling(crawling_data))

        elif GPSInfoIndi in message:
            latitude = message.split("latitude[")[1].split("]")[0]
            longitude = message.split("longitude[")[1].split("]")[0]
            date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print("GPS Info - Latitude:", latitude, "Longitude:", longitude, "Date:", date)
            upsert_gps(latitude, longitude, date)

        elif "SnifferRsltIndi" in message:
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
                        arfcn=earfcn_value,
                        operator=prov["operator"],
                        band=prov["band"],
                        dl_freq=prov["dl_freq"],
                        ul_freq=prov["ul_freq"],
                        pci=str(pci_value) if pci_value else None,
                        rsrp=str(rsrp_value) if rsrp_value else None,
                    )

                    update_status_ip_sniffer(source_ip, 'scan', 1, db)

                    sniffing_data = {
                        "type": "sniffing",
                        "ip": source_ip,
                        "arfcn": earfcn_value,
                        "operator": prov["operator"],
                        "band": prov["band"],
                        "dl_freq": prov["dl_freq"],
                        "ul_freq": prov["ul_freq"],
                        "pci": str(pci_value) if pci_value else None,
                        "rsrp": str(rsrp_value) if rsrp_value else None,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    }
                    asyncio.run(event_bus.send_sniffing(sniffing_data))

            else:
                print("masuk -1 nih<<<<<<<", message)
                time.sleep(1)
                update_status_ip_sniffer(source_ip, 'scan', -1, db)
                
                sniffing_complete = {
                    "type": "sniffing_complete",
                    "ip": source_ip,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                }
                asyncio.run(event_bus.send_sniffing(sniffing_complete))


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
