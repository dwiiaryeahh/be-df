from app.config.utils import HeartBeat, GPSInfoIndi, GSM_WB, GetCellParaRsp, GetAppCfgExtRsp, GetNmmCfg, OneUeInfoIndi, status_variabel
from app.config.utils import HEARTBEAT_JSON, CRAWLING_JSON, GPS_JSON
import time
import re
import os
import glob
import json


def load_json(filename):
    """Memuat data dari file JSON jika ada."""
    if os.path.exists(filename):
        with open(filename, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}
    return {}

def save_json(filename, data):
    """Menyimpan data ke file JSON."""
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)

def save_xml_file(message, source_ip, folder_name, log_message):
    print(log_message)
    xml_pattern = r"<\?xml[\s\S]*"
    xml_match = re.search(xml_pattern, message)

    if xml_match:
        xml_string = xml_match.group(0)
        print(xml_string)

        # Path dasar xml_file
        base_path = os.path.join(os.path.dirname(__file__), '../xml_file')
        os.makedirs(base_path, exist_ok=True)

        # Path folder_name di dalam xml_file
        full_folder_path = os.path.join(base_path, folder_name)
        os.makedirs(full_folder_path, exist_ok=True)

        # Path lengkap file
        file_path = os.path.join(full_folder_path, f"{folder_name}_{source_ip}.xml")
        with open(file_path, "w") as file:
            file.write(xml_string)

        print("File XML telah dibuat di:", os.path.abspath(file_path))
    else:
        print("Tidak ditemukan XML dalam string yang diberikan.")


def RespUdp(message, addr):
    print(f"Message : {message}")
    # create_db_receiver = createDBReceiver()
    source_ip = addr[0]
    print("Source IP:", source_ip, "Received message:", message)

    date_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    if HeartBeat in message:
        STATE = message.split("STATE[")[1].split("]")[0]
        TEMP = message.split("TEMP[")[1].split("]")[0]
        MODE = message.split("MODE[")[1].split("]")[0]
        # FREQ = message.split("FREQ[")[1].split("]")[0]
        CH = message.split(" ")[3]

        if STATE == "CLOSED":
            STATE = "ONLINE"
        else:
            STATE

        

        # Load existing data
        data = load_json(HEARTBEAT_JSON)
      

        # Update data berdasarkan source_ip
        data[source_ip] = {
            "STATE": STATE,
            "TEMP": TEMP,
            "MODE": MODE,
            "CH": CH,
            "timestamp": date_now
        }

        # Simpan data ke JSON
        save_json(HEARTBEAT_JSON, data)
 

    elif GetCellParaRsp in message:
        save_xml_file(message, source_ip, 'cellpara', "(CellParaRsp)")

    elif GetAppCfgExtRsp in message:
        save_xml_file(message, source_ip, 'appcfgext', "(AppCfgExtRsp)")

    elif OneUeInfoIndi in message:

        # parsing data dari bbu
        date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        rsrp = '0'
        rsrp = message.split("rsrp[")[1].split("]")[0]
        taType = message.split("taType[")[1].split("]")[0]
        ulCqi = message.split("ulCqi[")[1].split("]")[0]
        ulRssi = message.split("ulRssi[")[1].split("]")[0]
        imsi = message.split("imsi[")[1].split("]")[0]

        signal_data = load_json(CRAWLING_JSON)

        signal_data[imsi] = {
            "timestamp": date,
            "rsrp": rsrp,
            "taType": taType,
            "ulCqi": ulCqi,
            "ulRssi": ulRssi,
            "imsi": imsi,
            "ip": source_ip
        }

        save_json(CRAWLING_JSON, signal_data)
    
    else:
        print(f" ")
        