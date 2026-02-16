"""
Service layer - Business logic dan helper functions
"""
from typing import List, Dict
import os
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import FreqOperator, Heartbeat, Crawling, GPS, Operator
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_all_ips_db(db: Session) -> List[str]:
    """Mengambil semua IP dari table heartbeat"""
    rows = db.query(Heartbeat.source_ip).all()
    return [r[0] for r in rows]

def get_ips_with_sniffer_enabled(db: Session) -> List[str]:
    """Ambil IP yang sniff_status = 1 (ada modul sniffer / nyala)."""
    rows = db.query(Heartbeat.source_ip).filter(
        Heartbeat.sniff_status == 1
    ).all()
    return [r[0] for r in rows]

# LOGIC GET IP FOR WHITELIST/BLACKLIST PROCESS
def get_exception_ips(db: Session) -> dict:
    exception_ips = []
    other_ips = []
    
    operator_ips = set()
    operators = db.query(Operator).all()
    for op in operators:
        if op.ip:
            operator_ips.add(op.ip)
    
    heartbeats = db.query(Heartbeat).all()
    
    for hb in heartbeats:
        if hb.source_ip in operator_ips:
            exception_ips.append(hb.source_ip)
        else:
            other_ips.append(hb.source_ip)
    
    # logger.debug(f"Exception IPs (from Operator table): {exception_ips}")
    # logger.debug(f"Other IPs: {other_ips}")
    
    return {
        'exception_ips': exception_ips,
        'other_ips': other_ips
    }

def validate_token(token: str) -> bool:
    """Validasi token"""
    from app.config.utils import token_bbu
    return token == token_bbu


# -------------------------
# Lazy initialization untuk menghindari circular import
# -------------------------
_send_command_instance = None

def get_send_command_instance():
    """Get atau create send_command instance secara lazy"""
    global _send_command_instance
    if _send_command_instance is None:
        from app.controller import send_commend_modul
        _send_command_instance = send_commend_modul()
    return _send_command_instance


# -------------------------
# XML Configuration
# -------------------------
XML_TYPE_MAP = {
    "cell_para": {"get": "GetCellPara", "set": "SetCellPara", "folder": "cellpara"},
    "app_cfg_ext": {"get": "GetAppCfgExt", "set": "SetAppCfgExt", "folder": "appcfgext"},
    "nmm_para": {"get": "GetNmmCfg", "set": "SetNmmCfg", "folder": "nmmcfg"},
    "work_cfg": {"get": "GetBaseWorkCfg", "set": "SetBaseWorkCfg", "folder": "GetBaseWorkCfgRsp"},
    "app_cfg": {"get": "GetWeilanCfg", "set": "SetWeilanCfg", "folder": "GetWeilanCfgRsp"},
}


def build_xml_path(xml_type: str, ip: str) -> str:
    """Build path untuk XML file berdasarkan type dan IP"""
    folder = XML_TYPE_MAP[xml_type]["folder"]
    return os.path.join(BASE_DIR, "xml_file", folder, f"{folder}_{ip}.xml")

def get_provider_data(db: Session, arfcn: int):
    row = (
        db.query(
            FreqOperator.arfcn,
            Operator.brand.label("brand"),
            FreqOperator.band,
            FreqOperator.dl_freq,
            FreqOperator.ul_freq,
            FreqOperator.mode,
        )
        .join(Operator, Operator.id == FreqOperator.provider_id, isouter=True)
        .filter(FreqOperator.arfcn == arfcn)
        .first()
    )

    if not row:
        return {
            "arfcn": arfcn,
            "operator": None,
            "band": None,
            "dl_freq": None,
            "ul_freq": None,
            "mode": None,
        }

    return {
        "arfcn": row.arfcn,
        "operator": row.brand,
        "band": row.band,
        "dl_freq": row.dl_freq,
        "ul_freq": row.ul_freq,
        "mode": row.mode,
    }

def get_provider_data_multiple(db: Session, arfcn_raw: str):
    if not arfcn_raw:
        return {
            "dl_freq": "",
            "ul_freq": ""
        }
    
    arfcn_list = [a.strip() for a in str(arfcn_raw).split(',')]
    
    dl_freq_list = []
    ul_freq_list = []
    
    for arfcn_str in arfcn_list:
        try:
            arfcn_int = int(arfcn_str)
            provider_data = get_provider_data(db, arfcn_int)
            
            if provider_data.get("dl_freq") is not None:
                dl_freq_list.append(str(provider_data["dl_freq"]))
            else:
                dl_freq_list.append("-")
                
            if provider_data.get("ul_freq") is not None:
                ul_freq_list.append(str(provider_data["ul_freq"]))
            else:
                ul_freq_list.append("-")
                
        except (ValueError, TypeError):
            dl_freq_list.append("-")
            ul_freq_list.append("-")
    
    dl_freq_result = ",".join(dl_freq_list) if len(dl_freq_list) > 1 else (dl_freq_list[0] if dl_freq_list else "")
    ul_freq_result = ",".join(ul_freq_list) if len(ul_freq_list) > 1 else (ul_freq_list[0] if ul_freq_list else "")
    
    return {
        "dl_freq": dl_freq_result,
        "ul_freq": ul_freq_result
    }

def provider_mapping(imsi: str) -> str:
    if imsi.startswith("51010"):
        return "Telkomsel"

    elif imsi.startswith("51011"):
        return "XL"

    elif imsi.startswith(("51001", "51021", "51089", "5101")):
        return "Indosat"

    elif imsi.startswith(("51028", "51009")):
        return "Smartfren"

    else:
        return "Other"

def parse_xml(xml_path, mode):
    if os.path.isfile(xml_path) and os.path.getsize(xml_path) > 0:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        if mode == "GSM-WB":
            mccgsm_values = []
            mncgsm_values = []
            arfcngsm_values = []

            for itemgms in root.findall('.//item'):
                mccgsm = itemgms.find('mcc').text
                mccgsm_values.append(mccgsm)

                mncgsm = itemgms.find('mnc').text.strip()
                mncgsm_values.append(mncgsm.zfill(2))

                arfcngsm = itemgms.find("./arfcnList/arfcn").text
                arfcngsm_values.append(arfcngsm)

            output_mcc = ','.join(mccgsm_values)
            output_mnc = ','.join(mncgsm_values)
            output_arfcn = ','.join(arfcngsm_values)

            return {"mcc": output_mcc, "mnc": output_mnc, "frequency": output_arfcn, "band": 0}
        
        elif mode == "GSM":
            mcc_gsm = root.find('.//mcc').text.strip()
            mnc_gsm = root.find('.//mnc').text.strip()
            arfcn_gsm = root.find('.//arfcn').text.strip()

            return {"mcc": mcc_gsm, "mnc": mnc_gsm, "frequency": arfcn_gsm, "band": 0}
        
        elif mode == "WCDMA":
            mcc_node = root.find(".//sib/mcc")
            mnc_node = root.find(".//sib/mnc")

            def digits_to_str(node_text: str) -> str:
                return "".join(node_text.split())

            mcc_wcdma = digits_to_str(mcc_node.text.strip()) if mcc_node is not None and mcc_node.text else ""
            mnc_wcdma_raw = digits_to_str(mnc_node.text.strip()) if mnc_node is not None and mnc_node.text else ""

            mnc_wcdma = mnc_wcdma_raw.zfill(2) if mnc_wcdma_raw else ""

            urfcn_node = root.find(".//urfcn")

            frequency = None
            frequency = urfcn_node.text.strip()
            return {
                "mcc": mcc_wcdma,
                "mnc": mnc_wcdma,
                "frequency": frequency,
                "band": 0
            }

        else:
            mcc = root.find('.//mcc').text.strip()
            mnc = root.find('.//mnc').text.strip()
            # Format MNC to ensure two digits
            mnc = mnc.zfill(2)
            band = root.find('.//band').text.strip()

            urfcn = root.find('.//urfcn')
            arfcn = root.find('.//arfcn')
            erfcn = root.find('.//erfcn')

            frequency = (erfcn.text.strip() if erfcn is not None else
                         arfcn.text.strip() if arfcn is not None else
                         urfcn.text.strip() if urfcn is not None else None)

            return {"mcc": mcc, "mnc": mnc, "frequency": frequency, "band": band}

    else:
        print(f"File XML kosong: {xml_path}. Tidak ada eksekusi yang dilakukan.")
        return None
    
def get_frequency(ip):
    db = SessionLocal()
    try:
        heartbeat_data = db.query(Heartbeat).filter(Heartbeat.source_ip == ip).first()
        if heartbeat_data:
            return {
                "arfcn": heartbeat_data.arfcn, 
                "ul_freq": heartbeat_data.ul_freq, 
                "dl_freq": heartbeat_data.dl_freq,
                "mode": heartbeat_data.mode
            }
        return None
    finally:
        db.close()
