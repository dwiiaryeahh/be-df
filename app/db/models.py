# app/db/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from .database import Base


class Heartbeat(Base):
    __tablename__ = "heartbeat"

    source_ip = Column(String, primary_key=True, index=True)
    state = Column(String, nullable=False)
    temp = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    ch = Column(String, nullable=False)

    timestamp = Column(String, nullable=False)


class Campaign(Base):
    __tablename__ = "campaign"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    imsi = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False)
    status = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    crawlings = relationship("Crawling", back_populates="campaign")


class Crawling(Base):
    __tablename__ = "crawling"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(String, nullable=False)
    rsrp = Column(String, nullable=False)
    taType = Column(String, nullable=False)
    ulCqi = Column(String, nullable=False)
    ulRssi = Column(String, nullable=False)

    imsi = Column(String, nullable=False, index=True)
    ip = Column(String, nullable=False, index=True)

    campaign_id = Column(Integer, ForeignKey("campaign.id"), nullable=True)
    campaign = relationship("Campaign", back_populates="crawlings")
