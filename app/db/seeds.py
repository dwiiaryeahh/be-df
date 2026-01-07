# app/db/seeds.py
"""
Database seeds - Auto-populate data ke database
"""
import json
import os
from sqlalchemy.orm import Session
from app.db.models import Operator, FreqOperator


def load_operator_data():
    """Load operator data dari operator.json"""
    json_file = os.path.join(
        os.path.dirname(__file__),
        '../json/operator.json'
    )
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            return json.load(f)
    return []


def load_freq_operator_data():
    """Load freq_operator data dari freq_operator.json"""
    json_file = os.path.join(
        os.path.dirname(__file__),
        '../json/freq_operator.json'
    )
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            return json.load(f)
    return []


def seed_operators(db: Session):
    """
    Seed operator data ke database
    Jika sudah ada, skip (tidak insert duplikat)
    """
    data = load_operator_data()
    
    if not data:
        print("⚠ operator.json tidak ditemukan atau kosong")
        return 0
    
    count = 0
    for item in data:
        # Check apakah sudah ada operator dengan mcc+mnc yang sama
        existing = db.query(Operator).filter(
            Operator.mcc == item.get('mcc'),
            Operator.mnc == item.get('mnc')
        ).first()
        
        if not existing:
            operator = Operator(
                mcc=item.get('mcc'),
                mnc=item.get('mnc'),
                brand=item.get('brand')
            )
            db.add(operator)
            count += 1
    
    if count > 0:
        db.commit()
        print(f"✓ Seeded {count} operators")
    else:
        print("ℹ No new operators to seed (all exist)")
    
    return count


def seed_freq_operators(db: Session):
    """
    Seed freq_operator data ke database
    Jika sudah ada (berdasarkan arfcn + provider_id), skip
    """
    data = load_freq_operator_data()
    
    if not data:
        print("⚠ freq_operator.json tidak ditemukan atau kosong")
        return 0
    
    count = 0
    for item in data:
        # Check apakah sudah ada dengan arfcn + provider_id yang sama
        existing = db.query(FreqOperator).filter(
            FreqOperator.arfcn == item.get('arfcn'),
            FreqOperator.provider_id == item.get('provider_id')
        ).first()
        
        if not existing:
            freq_op = FreqOperator(
                arfcn=item.get('arfcn'),
                provider_id=item.get('provider_id'),
                band=item.get('band'),
                dl_freq=item.get('dl_freq'),
                ul_freq=item.get('ul_freq'),
                mode=item.get('mode')
            )
            db.add(freq_op)
            count += 1
    
    if count > 0:
        db.commit()
        print(f"✓ Seeded {count} freq_operators")
    else:
        print("ℹ No new freq_operators to seed (all exist)")
    
    return count


def seed_all(db: Session):
    """
    Run semua seeds
    """
    print("\n" + "="*60)
    print("Starting Database Seeding")
    print("="*60)
    
    seed_operators(db)
    seed_freq_operators(db)
    
    print("="*60)
    print("Database Seeding Complete")
    print("="*60 + "\n")
