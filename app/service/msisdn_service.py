import requests
import time
import threading
from sqlalchemy.orm import Session
from app.db.models import Crawling
from app.db.database import SessionLocal


def make_post_request(imsi):
        mcc = imsi[:3]
        mnc = imsi[3:5]
        
        params = {
            "i": imsi,
            "l": '',
            "c": '',
            "cc": mcc,
            "nc": mnc,
            "k": 'CAAA89A74C6A3CDD655CB43F134AC'
        }

        url = "http://157.230.34.151:1442/WmoMpmdGan_trans.php"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(url, headers=headers, data=params)

        json_response = response.json()
        print(f'respon json {json_response}')

        if 'message' in json_response and json_response['message'] == 'Not Found':
            print("Message 'Not Found' received. Setting msisdn to '-'.")
            return '-'
        
        if 'body' in json_response:
            msisdn = json_response['body'].get('msisdn', None)
            print("MSISDN:", msisdn)
            return msisdn
        else:
            print("MSISDN not found in the response.")
            return None

def translate_telkomsel(imsi: str) -> str:
    pre = '628'
    imsi = imsi.strip()
    im1 = imsi[5:]         
    im2 = im1[0:2]         
    im3 = im1[0:4]         
    im4 = im3[2]           
    im5 = im1[4:]          
    mapping = {
        '1': '11',
        '2': '12',
        '3': '13',
        '6': '21',
        '7': '22',
        '8': '23',
        '9': '51',
        '4': '52'
    }
    imm = mapping.get(im4, '53')

    return f"{pre}{imm}{im2}{im5}"


def get_msisdn_for_imsi(db: Session, imsi: str) -> str:
    """
    Get MSISDN untuk IMSI tertentu.
    Logic:
    1. Jika IMSI sudah ada di database, ambil MSISDN existing
    2. Jika belum ada:
       - Jika provider Telkomsel, gunakan translate_telkomsel
       - Jika provider lain, gunakan make_post_request
    """
    try:
        # Cek apakah IMSI sudah ada di database
        existing_crawl = db.query(Crawling).filter(
            Crawling.imsi == imsi,
            Crawling.msisdn.isnot(None),
            Crawling.msisdn != ''
        ).first()
        
        if existing_crawl and existing_crawl.msisdn:
            print(f"[MSISDN] Found existing MSISDN for IMSI {imsi}: {existing_crawl.msisdn}")
            return existing_crawl.msisdn
        
        # Tentukan provider berdasarkan MCC
        mcc = imsi[:3]
        mnc = imsi[3:5]
        
        # Telkomsel MCC: 510
        if mcc == '510' and mnc == '10':
            msisdn = translate_telkomsel(imsi)
            print(f"[MSISDN] Generated MSISDN for Telkomsel IMSI {imsi}: {msisdn}")
            return msisdn
        else:
            # Provider lain gunakan API
            msisdn = make_post_request(imsi)
            print(f"[MSISDN] Got MSISDN from API for IMSI {imsi}: {msisdn}")
            return msisdn
    
    except Exception as e:
        print(f"[MSISDN ERROR] Error getting MSISDN for {imsi}: {str(e)}")
        return None


def background_msisdn_checker(interval_seconds: int = 5):
    """
    Background task untuk mengecek dan update MSISDN secara berkala.
    Cek semua crawling records yang msisdn-nya NULL atau kosong, kemudian update.
    Berjalan terus menerus dengan interval tertentu.
    """
    print("[MSISDN Checker] Background MSISDN checker started")
    
    while True:
        try:
            db = SessionLocal()
            
            # Query crawling yang msisdn-nya NULL
            crawlings_to_check = db.query(Crawling).filter(
                (Crawling.msisdn.is_(None)) | (Crawling.msisdn == '')
            ).all()
            
            if crawlings_to_check:
                print(f"[MSISDN Checker] Found {len(crawlings_to_check)} records with NULL msisdn")
                
                for crawl in crawlings_to_check:
                    try:
                        msisdn = get_msisdn_for_imsi(db, crawl.imsi)
                        
                        if msisdn:
                            crawl.msisdn = msisdn
                            db.commit()
                            print(f"[MSISDN Checker] Updated IMSI {crawl.imsi} with MSISDN {msisdn}")
                        else:
                            print(f"[MSISDN Checker] Failed to get MSISDN for IMSI {crawl.imsi}")
                    
                    except Exception as e:
                        db.rollback()
                        print(f"[MSISDN Checker] Error updating IMSI {crawl.imsi}: {str(e)}")
            else:
                print("[MSISDN Checker] No records with NULL msisdn found")
            
            db.close()
            
        except Exception as e:
            print(f"[MSISDN Checker] Error in background checker: {str(e)}")
            if 'db' in locals():
                try:
                    db.close()
                except:
                    pass
        
        # Tunggu sebelum cek lagi
        time.sleep(interval_seconds)


def start_background_msisdn_checker(interval_seconds: int = 5):
    """
    Start background MSISDN checker sebagai daemon thread.
    Aman dipanggil berulang kali - hanya akan start sekali.
    """
    # Cek apakah thread sudah jalan
    for thread in threading.enumerate():
        if thread.name == "MSISDNChecker":
            print("[MSISDN Checker] Background MSISDN checker thread already running")
            return
    
    # Jika belum ada, create dan start thread baru
    checker_thread = threading.Thread(
        target=background_msisdn_checker,
        args=(interval_seconds,),
        name="MSISDNChecker",
        daemon=True
    )
    checker_thread.start()
    print("[MSISDN Checker] Background MSISDN checker thread started")
