from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from app.controller import send_commend_modul  # Sesuaikan dengan struktur file Anda
import time
from typing import Optional, List, Dict
from app.config.utils import token_bbu, StartCell, StopCell
from app.config.utils import HEARTBEAT_JSON, CRAWLING_JSON, GPS_JSON
import json
from typing import List
import re
import os
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # naik 1 level ke project/
DOCS_PATH = os.path.join(BASE_DIR, "docs", "docs.html")



# Inisialisasi aplikasi FastAPI
app = FastAPI(
    title="BBU CONTROL",
    description="API untuk kontrol BBU via UDP",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # atau tentukan domain docs kamu
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
def get_spotlight():
    return FileResponse(DOCS_PATH)


# Model data untuk request dan response
class start_status(BaseModel):
    status: str
    last_checked: Optional[str] = None  # Buat opsional

class stop_status(BaseModel):
    status: str
    last_checked: Optional[str] = None  # Buat opsional
    

def validate_token(token: str) -> bool:
    # Contoh validasi token
    return token == token_bbu


class status_setting(BaseModel):
    status: str
    last_checked: Optional[str] = None  # Buat opsional

class command_data(BaseModel):
    command: str = Field(..., example="GetCellPara")

class setting_request(BaseModel):
    topic: str = Field(..., example="get_data_bbu", description="Topik operasi untuk API.")
    data: List[command_data] = Field(
        ...,
        example=[
            {"command": "GetCellPara"},
            {"command": "GetAppCfgExt"},
            {"command": "GetNmmCfg"}
        ]
    )
class start_status(BaseModel):
    status: str
    last_checked: str
    details: list  # Menyimpan hasil dari setiap IP

# --- Request dan Response Schema ---
class StartRequest(BaseModel):
    sn: str = Field(default="SN12345678", description="Serial number perangkat (8–20 karakter alfanumerik)")

class StartResult(BaseModel):
    ip: str
    status: str
    error: str | None = None

class StartStatus(BaseModel):
    status: str
    last_checked: str
    details: List[StartResult]


# --- Request dan Response Models ---
class StopRequest(BaseModel):
    sn: str = Field(default="SN12345678", description="Serial number perangkat (8–20 karakter alfanumerik)")

class StopResult(BaseModel):
    ip: str
    status: str
    error: str | None = None

class StopStatus(BaseModel):
    status: str
    last_checked: str
    details: List[StopResult]

class StartOneRequest(BaseModel):
    sn: str = Field(default="SN12345678", description="Serial number perangkat (8–20 karakter alfanumerik)")
    ip: str = Field(default="192.168.10.11", description="masukan ip yang akan di start)")

class StopOneRequest(BaseModel):
    sn: str = Field(default="SN12345678", description="Serial number perangkat (8–20 karakter alfanumerik)")
    ip: str = Field(default="192.168.10.11", description="masukan ip yang akan di start)")


def delete_files():
    files_to_delete = ["gps.json", "heartbeat.json", "crawling.json", "summary.json"]
    results = []

    for file_name in files_to_delete:
        if os.path.exists(file_name):
            os.remove(file_name)
            results.append({"file": file_name, "status": "deleted"})
        else:
            results.append({"file": file_name, "status": "not found"})

    return results


def get_all_ips(filename):
    """Mengambil semua IP dari file JSON."""
    try:
        with open(filename, "r") as file:
            data = json.load(file)
            return list(data.keys())  # Mengembalikan daftar IP
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error membaca JSON: {e}")
        return []

def read_json(filename):
    """Membaca data dari heartbeat.json"""
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error membaca JSON: {e}")
        return {}

# Inisialisasi modul perintah
send_command_instance = send_commend_modul()


XML_TYPE_MAP = {
    "cell_para": {
        "get": "GetCellPara",
        "set": "SetCellPara",
        "folder": "cellpara",
    },
    "app_cfg_ext": {
        "get": "GetAppCfgExt",
        "set": "SetAppCfgExt",
        "folder": "appcfgext",
    },
    "nmm_para": {
        "get": "GetNmmCfg",
        "set": "SetNmmCfg",
        "folder": "nmmcfg",
    },
    "work_cfg": {
        "get": "GetBaseWorkCfg",
        "set": "SetBaseWorkCfg",
        "folder": "GetBaseWorkCfgRsp",
    },
    "app_cfg": {
        "get": "GetWeilanCfg",
        "set": "SetWeilanCfg",
        "folder": "GetWeilanCfgRsp",
    },
}

def build_xml_path(xml_type: str, ip: str) -> str:
    folder = XML_TYPE_MAP[xml_type]["folder"]
    return os.path.join(BASE_DIR, "xml_file", folder, f"{folder}_{ip}.xml")


def generate_summary():
    # Baca file JSON
    try:
        with open('heartbeat.json') as f:
            heartbeat_data = json.load(f)
        with open('crawling.json') as f:
            crawling_data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membaca file input: {e}")

    # Buat mapping ip dari crawling
    crawling_ips = {v['ip']: v for v in crawling_data.values()}

    # Proses heartbeat
    results = []
    found_count = 0
    not_found_count = 0

    for ip, hb_info in heartbeat_data.items():
        if ip in crawling_ips:
            status = "FOUND"
            found_count += 1
        else:
            status = "NOT FOUND"
            not_found_count += 1

        result = {
            "ip": ip,
            "TEMP": hb_info.get("TEMP"),
            "MODE": hb_info.get("MODE"),
            "CH": hb_info.get("CH"),
            "status": status
        }
        results.append(result)

    final_output = {
        "results": results,
        "summary": {
            "FOUND": found_count,
            "NOT_FOUND": not_found_count
        }
    }

    # Simpan ke summary.json
    with open('summary.json', 'w') as f:
        json.dump(final_output, f, indent=4)

    return final_output

class DeviceInfo(BaseModel):
    STATE: str
    TEMP: str
    MODE: str
    CH: str
    timestamp: str

class HeartbeatResponse(BaseModel):
    status: str
    last_checked: str
    data: Dict[str, DeviceInfo]  # key = IP (string), value = DeviceInfo

@app.get("/device", response_model=HeartbeatResponse,tags=["DATA BBU"])
def get_heartbeat():
    """
    Mengambil seluruh data dari heartbeat.json.
    """
    data = json_control.read_json(HEARTBEAT_JSON)
    if not data:
        raise HTTPException(status_code=404, detail="Data tidak ditemukan atau file kosong.")
    
    return {
        "status": "success",
        "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data": data
    }

    

# --- Endpoint POST dengan validasi SN ---
@app.post("/start_all_bbu", response_model=StartStatus, tags=["Crawling Imsi"])
def start(req: StartRequest):
    """
    Memulai StartCell via UDP berdasarkan IP dalam heartbeat.json dan validasi SN.
    """
    # Validasi format SN (contoh: alfanumerik 8–20 karakter)
    if not re.fullmatch(r"[A-Za-z0-9]{8,20}", req.sn):
        raise HTTPException(status_code=400, detail="Serial number tidak valid. Harus 8–20 karakter alfanumerik.")

    try:
        ip_list = get_all_ips(HEARTBEAT_JSON)
        results = []

        for ip in ip_list:
            try:
                send_command_instance.command(ip, StartCell)
                results.append({"ip": ip, "status": "success"})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {
            "status": "success",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": results
        }
    except Exception as e:
        return {
            "status": "error",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": [{"ip": "all", "status": "error", "error": str(e)}]
        }


# --- Endpoint POST /stopbbu ---
@app.post("/stop_all_bbu", response_model=StopStatus , tags=["Crawling Imsi"])
def stop(req: StopRequest):
    """
    Mengirim perintah StopCell ke semua IP di heartbeat.json dengan validasi SN.
    """
    if not re.fullmatch(r"[A-Za-z0-9]{8,20}", req.sn):
        raise HTTPException(status_code=400, detail="Serial number tidak valid. Harus 8–20 karakter alfanumerik.")

    try:
        ip_list = get_all_ips(HEARTBEAT_JSON)
        results = []

        for ip in ip_list:
            try:
                send_command_instance.command(ip, StopCell)
                results.append({"ip": ip, "status": "success"})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {
            "status": "success",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": results
        }
    except Exception as e:
        return {
            "status": "error",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": [{"ip": "all", "status": "error", "error": str(e)}]
        }


@app.get("/summary", tags=["DATA BBU"])
def get_summary():
    """
    Membaca heartbeat.json dan crawling.json, melakukan perbandingan,
    menyimpan hasil ke summary.json, lalu mengembalikan hasilnya.
    """
    data = generate_summary()
    return {
        "status": "success",
        "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data": data
    }


@app.get("/cell_para", tags=["Get XML"])
def get_cellpara():
    """
    Mengambil seluruh data dari heartbeat.json.
    """
    try:
        ip_list = get_all_ips(HEARTBEAT_JSON)
        results = []

        for ip in ip_list:
            try:
                send_command_instance.command(ip, XML_TYPE_MAP["cell_para"]["get"])
                file_path = build_xml_path("cell_para", ip)
                exists = os.path.exists(file_path)
                msg = "File XML telah dibuat berdasarkan IP" if exists else "Perintah dikirim, menunggu file XML"
                results.append({"ip": ip, "status": "success", "file_exists": exists, "file_path": file_path, "message": msg})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {
            "status": "success",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": results
        }
    except Exception as e:
        return {
            "status": "error",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": [{"error": str(e)}]
        }

@app.get("/app_cfg_ext", tags=["Get XML"])
def get_appcfgext():
    """
    Mengambil seluruh data dari heartbeat.json.
    """
    try:
        ip_list = get_all_ips(HEARTBEAT_JSON)
        results = []

        for ip in ip_list:
            try:
                send_command_instance.command(ip, XML_TYPE_MAP["app_cfg_ext"]["get"])
                file_path = build_xml_path("app_cfg_ext", ip)
                exists = os.path.exists(file_path)
                msg = "File XML telah dibuat berdasarkan IP" if exists else "Perintah dikirim, menunggu file XML"
                results.append({"ip": ip, "status": "success", "file_exists": exists, "file_path": file_path, "message": msg})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {
            "status": "success",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": results
        }
    except Exception as e:
        return {
            "status": "error",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": [{"error": str(e)}]
        }

@app.get("/nmm_para", tags=["Get XML"])
def get_nmmcfg():
    """
    Mengambil seluruh data dari heartbeat.json.
    """
    try:
        ip_list = get_all_ips(HEARTBEAT_JSON)
        results = []

        for ip in ip_list:
            try:
                send_command_instance.command(ip, XML_TYPE_MAP["nmm_para"]["get"])
                file_path = build_xml_path("nmm_para", ip)
                exists = os.path.exists(file_path)
                msg = "File XML telah dibuat berdasarkan IP" if exists else "Perintah dikirim, menunggu file XML"
                results.append({"ip": ip, "status": "success", "file_exists": exists, "file_path": file_path, "message": msg})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {
            "status": "success",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": results
        }
    except Exception as e:
        return {
            "status": "error",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": [{"error": str(e)}]
        }


@app.get("/work_cfg", tags=["Get XML"])
def get_nmmcfg():
    """
    Mengambil seluruh data dari heartbeat.json.
    """
    try:
        ip_list = get_all_ips(HEARTBEAT_JSON)
        results = []

        for ip in ip_list:
            try:
                send_command_instance.command(ip, XML_TYPE_MAP["work_cfg"]["get"])
                file_path = build_xml_path("work_cfg", ip)
                exists = os.path.exists(file_path)
                msg = "File XML telah dibuat berdasarkan IP" if exists else "Perintah dikirim, menunggu file XML"
                results.append({"ip": ip, "status": "success", "file_exists": exists, "file_path": file_path, "message": msg})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {
            "status": "success",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": results
        }
    except Exception as e:
        return {
            "status": "error",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": [{"error": str(e)}]
        }

@app.get("/app_cfg", tags=["Get XML"])
def get_nmmcfg():
    """
    Mengambil seluruh data dari heartbeat.json.
    """
    try:
        ip_list = get_all_ips(HEARTBEAT_JSON)
        results = []

        for ip in ip_list:
            try:
                send_command_instance.command(ip, XML_TYPE_MAP["app_cfg"]["get"])
                file_path = build_xml_path("app_cfg", ip)
                exists = os.path.exists(file_path)
                msg = "File XML telah dibuat berdasarkan IP" if exists else "Perintah dikirim, menunggu file XML"
                results.append({"ip": ip, "status": "success", "file_exists": exists, "file_path": file_path, "message": msg})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {
            "status": "success",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": results
        }
    except Exception as e:
        return {
            "status": "error",
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
            "details": [{"error": str(e)}]
        }

class SetXmlRequest(BaseModel):
    type: str
    ip: str | None = None
    xml: str | None = None
    items: List[Dict[str, str]] | None = None

@app.get("/xml/{xml_type}", tags=["Get XML"])
def list_xml(xml_type: str):
    if xml_type not in XML_TYPE_MAP:
        raise HTTPException(status_code=400, detail="xml_type tidak dikenali")
    ip_list = get_all_ips(HEARTBEAT_JSON)
    items = []
    for ip in ip_list:
        file_path = build_xml_path(xml_type, ip)
        exists = os.path.exists(file_path)
        download_url = f"/xml/{xml_type}/{ip}"
        items.append({"ip": ip, "file_exists": exists, "file_path": file_path, "download_url": download_url})
    return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": items}

@app.get("/xml/{xml_type}/{ip}", tags=["Get XML"])
def get_xml_file(xml_type: str, ip: str):
    if xml_type not in XML_TYPE_MAP:
        raise HTTPException(status_code=400, detail="xml_type tidak dikenali")
    file_path = build_xml_path(xml_type, ip)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File XML tidak ditemukan")
    return FileResponse(file_path, media_type="application/xml")

@app.post("/set_xml", tags=["Set XML"])
def set_xml(req: SetXmlRequest):
    if req.type not in XML_TYPE_MAP:
        raise HTTPException(status_code=400, detail="type tidak dikenali")
    cmd = XML_TYPE_MAP[req.type]["set"]
    try:
        if req.items:
            results = []
            for item in req.items:
                try:
                    ip = item.get("ip")
                    xml = item.get("xml")
                    file_path = build_xml_path(req.type, ip)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "w") as f:
                        f.write(xml)
                    send_command_instance.command(ip, cmd)
                    exists = os.path.exists(file_path)
                    results.append({"ip": ip, "status": "success", "file_path": file_path, "file_exists": exists, "updated": True})
                except Exception as e:
                    results.append({"ip": item.get("ip"), "status": "error", "error": str(e)})
            return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}
        if req.ip:
            file_path = build_xml_path(req.type, req.ip)
            if req.xml is not None:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(req.xml)
            send_command_instance.command(req.ip, cmd)
            exists = os.path.exists(file_path)
            return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"ip": req.ip, "file_path": file_path, "file_exists": exists, "updated": req.xml is not None}]}
        else:
            ip_list = get_all_ips(HEARTBEAT_JSON)
            results = []
            for ip in ip_list:
                try:
                    file_path = build_xml_path(req.type, ip)
                    if req.xml is not None:
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, "w") as f:
                            f.write(req.xml)
                    send_command_instance.command(ip, cmd)
                    exists = os.path.exists(file_path)
                    results.append({"ip": ip, "status": "success", "file_path": file_path, "file_exists": exists, "updated": req.xml is not None})
                except Exception as e:
                    results.append({"ip": ip, "status": "error", "error": str(e)})
            return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"error": str(e)}]}

