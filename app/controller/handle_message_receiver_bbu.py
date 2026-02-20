from app.config.utils import HeartBeat, GetCellParaRsp, GetAppCfgExtRsp, OneUeInfoIndi, GPSInfoIndi
import time
import re
import os
import asyncio
from app.db.database import SessionLocal, engine
from app.db import models
from app.service.heartbeat_service import get_heartbeat_by_ip
from app.service.utils_service import get_frequency, provider_mapping
from app.service.sniffer_service import insert_sniffer_nmmcfg, reset_nmmcfg
from app.service.wb_status_service import get_wb_status
from app.ws.events import event_bus
from app.ws import runtime

def schedule_async_task(coro):
    """Schedule an async task safely from synchronous context using main event loop"""
    if runtime.main_loop is not None:
        asyncio.run_coroutine_threadsafe(coro, runtime.main_loop)
    else:
        print("[WARNING] Main event loop not available, skipping async task")

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
        

def calculate_imei_check_digit(imei_14):
    if len(imei_14) != 14 or not imei_14.isdigit():
        raise ValueError("IMEI harus 14 digit angka.")

    total = 0
    for i, digit in enumerate(imei_14):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n

    check_digit = (10 - (total % 10)) % 10
    return str(check_digit)

def RespUdp(message, addr):
    print(f"Message : {message}")
    source_ip = addr[0]
    print("Source IP:", source_ip, "Received message:", message)

    date_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    from app.service.utils_service import get_provider_data
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
            
            wb_status = get_wb_status(db)
            if wb_status is not None:
                if STATE == "CLOSED":
                    if wb_status == 0:
                        STATE = "ONLINE"
                    elif wb_status == 1:
                        STATE = "STATE_CELL_RF_OPEN"


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
            mcc_str = heartbeat_data.mcc
            mnc_str = heartbeat_data.mnc
            final_provider = "Other"

            if mcc_str and mnc_str:
                try:
                    mcc_list = [x.strip() for x in mcc_str.split(',')]
                    mnc_list = [x.strip() for x in mnc_str.split(',')]
                    
                    providers = []
                    seen = set()
                    for c_mcc, c_mnc in zip(mcc_list, mnc_list):
                        plmn = c_mcc + c_mnc
                        p = provider_mapping(plmn)
                        if p not in seen:
                            providers.append(p)
                            seen.add(p)
                    
                    if providers:
                        final_provider = ", ".join(providers)
                
                except Exception as e:
                    print(f"[Error] Failed to parse MCC/MNC for Heartbeat: {e}")

            heartbeat_data = {
                "type": "heartbeat",
                "ip": source_ip,
                "state": STATE,
                "temp": TEMP,
                "mode": MODE,
                "ch": CH,
                "band": BAND or heartbeat_data.band,
                "provider": final_provider,
                "mcc": heartbeat_data.mcc,
                "mnc": heartbeat_data.mnc,
                "arfcn": heartbeat_data.arfcn,
                "ul": heartbeat_data.ul_freq,
                "dl": heartbeat_data.dl_freq,
                "timestamp": date_now
            }
            schedule_async_task(event_bus.send_heartbeat(heartbeat_data))

        elif GetCellParaRsp in message:
            save_xml_file(message, source_ip, 'cellpara', "(CellParaRsp)")

        elif GetAppCfgExtRsp in message:
            save_xml_file(message, source_ip, 'appcfgext', "(AppCfgExtRsp)")

        elif OneUeInfoIndi in message:
            rsrp = message.split("rsrp[")[1].split("]")[0]
            taType = message.split("taType[")[1].split("]")[0]
            ulCqi = message.split("ulCqi[")[1].split("]")[0]
            ulRssi_raw = message.split("ulRssi[")[1].split("]")[0]
            ulRssi = str(int(ulRssi_raw) - 130)
            imsi = message.split("imsi[")[1].split("]")[0]
            ch_match = re.search(r"CH-(\S+)", message)
            ch = ch_match.group(1) if ch_match else None
            
            result_imei = None
            if "imei[" in message and "]" in message:
                imei = message.split("imei[")[1].split("]")[0]
                imei14 = imei[:14]
                if imei14.isdigit() and len(imei14) == 14:
                    if imei14[0] != "0" and imei14[-1] != "0":
                        result_imei = imei14 + calculate_imei_check_digit(imei14)
            
            freq = get_frequency(source_ip) 

            from app.service.campaign_service import get_latest_campaign_id
            campaign_id = get_latest_campaign_id(db)
            if campaign_id is not None:
                upsert_crawling(
                    db=db,
                    timestamp=date_now,
                    rsrp=rsrp,
                    taType=taType,
                    ulCqi=ulCqi,
                    ulRssi=ulRssi,
                    imsi=imsi,
                    ip=source_ip,
                    ch="CH-" + ch if ch else None,
                    provider=provider_mapping(imsi),
                    campaign_id=campaign_id,
                    imei=result_imei
                )
                db.commit()
                
                crawling_data = {
                    "type": "crawling",
                    "provider": provider_mapping(imsi),
                    "imsi": imsi,
                    "timestamp": date_now,
                    "rsrp": rsrp,
                    "taType": taType,
                    "ulCqi": ulCqi,
                    "ulRssi": ulRssi,
                    "ip": source_ip,
                    "ch": "CH-" + ch if ch else None,  
                    "arfcn": freq["arfcn"] if freq else None,
                    "ul_freq": freq["ul_freq"] if freq else None,
                    "dl_freq": freq["dl_freq"] if freq else None,
                    "mode": freq["mode"] if freq else None,
                    "campaign_id": campaign_id
                }
                schedule_async_task(event_bus.send_crawling(crawling_data))

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
                    ch_match = re.search(r"CH-(\S+)", message)
                    ch = ch_match.group(1) if ch_match else None

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
                        ch="CH-" + ch if ch else None
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
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                        "ch": "CH-" + ch if ch else None
                    }
                    schedule_async_task(event_bus.send_sniffing(sniffing_data))

            else:
                print("masuk -1 nih<<<<<<<", message)
                time.sleep(1)
                update_status_ip_sniffer(source_ip, 'scan', -1, db)
                
                sniffing_complete = {
                    "type": "sniffing_complete",
                    "ip": source_ip,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                }
                schedule_async_task(event_bus.send_sniffing(sniffing_complete))


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
