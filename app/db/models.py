# app/db/models.py
from sqlalchemy import Boolean, Column, Float, Integer, String, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from .database import Base


class Target(Base):
    __tablename__ = "target"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    imsi = Column(String, nullable=False)
    alert_status = Column(String, nullable=True)
    target_status = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Heartbeat(Base):
    __tablename__ = "heartbeat"

    source_ip = Column(String, primary_key=True, index=True)
    state = Column(String, nullable=False)
    temp = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    ch = Column(String, nullable=False)
    band = Column(String, nullable=False)
    arfcn = Column(String, nullable=True)
    mcc = Column(String, nullable=True)
    mnc = Column(String, nullable=True)
    ul_freq = Column(String, nullable=True)
    dl_freq = Column(String, nullable=True)
    sniff_status = Column(Integer, nullable=True, default=1) 
    # 0 Mati (tidak ada modul sniff) 
    # 1 Nyala (ada modul sniff)
    sniff_scan = Column(Integer, nullable=True, default=1) 
    # -1 Mati (selesai sniff) 
    # 1 Nyala (lagi sniff) 
    # 0 (tidak ada modul sniff)
    timestamp = Column(String, nullable=False)

class NmmCfg(Base):
    __tablename__ = "nmmcfg"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String, nullable=True)
    time = Column(String, nullable=True)
    arfcn = Column(Integer)
    operator = Column(String, nullable=True)
    dl_freq = Column(Float, default=0.0, nullable=True)
    ul_freq = Column(Float, default=0.0, nullable=True)
    pci = Column(String, nullable=True)
    rsrp = Column(String, nullable=True)
    band = Column(Integer, nullable=True)
    ch = Column(String, nullable=True)

class Operator(Base):
    __tablename__ = "operator"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mcc = Column(String, nullable=True)
    mnc = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    ip = Column(String, nullable=True)

    # relasi ke freq_operator
    freqs = relationship(
        "FreqOperator",
        back_populates="operator",
        cascade="all, delete-orphan"
    )

class FreqOperator(Base):
    __tablename__ = "freq_operator"

    id = Column(Integer, primary_key=True, autoincrement=True)
    arfcn = Column(Integer, nullable=True)
    provider_id = Column(
        Integer,
        ForeignKey("operator.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True
    )
    band = Column(Integer, nullable=True)
    dl_freq = Column(Float, nullable=True, default=0.0)
    ul_freq = Column(Float, nullable=True, default=0.0)
    mode = Column(String, nullable=True)

    operator = relationship("Operator", back_populates="freqs")

class Campaign(Base):
    __tablename__ = "campaign"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    imsi = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False)
    status = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    mode = Column(String, nullable=True)
    duration = Column(String, nullable=True)
    start_scan = Column(DateTime(timezone=True), nullable=True)
    stop_scan = Column(DateTime(timezone=True), nullable=True)
    target_info = Column(JSON, nullable=True)

    crawlings = relationship("Crawling", back_populates="campaign")


class Crawling(Base):
    __tablename__ = "crawling"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(String, nullable=False)
    rsrp = Column(String, nullable=False)
    taType = Column(String, nullable=False)
    ulCqi = Column(String, nullable=False)
    ulRssi = Column(String, nullable=False)
    ch = Column(String, nullable=True)
    provider = Column(String, nullable=True)

    imsi = Column(String, nullable=False, index=True)
    ip = Column(String, nullable=False, index=True)
    
    lat = Column(String, nullable=True)
    long = Column(String, nullable=True)
    
    count = Column(Integer, nullable=True, default=0)
    imei = Column(String, nullable=True)
    msisdn = Column(String, nullable=True)

    campaign_id = Column(Integer, ForeignKey("campaign.id"), nullable=True)
    campaign = relationship("Campaign", back_populates="crawlings")

class GPS(Base):
    __tablename__ = "gps"

    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(String, nullable=False)
    longitude = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)

class License(Base):
    __tablename__ = "license"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    number = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
class WbStatus(Base):
    __tablename__ = "wb_status"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(Boolean, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)