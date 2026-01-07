"""
Pydantic models untuk requests/responses API
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class start_status(BaseModel):
    status: str
    last_checked: Optional[str] = None


class stop_status(BaseModel):
    status: str
    last_checked: Optional[str] = None


class status_setting(BaseModel):
    status: str
    last_checked: Optional[str] = None


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


class DeviceInfo(BaseModel):
    STATE: str
    TEMP: str
    MODE: str
    CH: str
    timestamp: str


class HeartbeatResponse(BaseModel):
    status: str
    last_checked: str
    data: Dict[str, DeviceInfo]


class SetXmlRequest(BaseModel):
    type: str
    ip: str | None = None
    xml: str | None = None
    items: List[Dict[str, str]] | None = None


# ==========================================
# Campaign Models - Untuk endpoint campaign
# ==========================================

class CrawlingData(BaseModel):
    """Campaign Crawling - Detail crawling untuk satu campaign"""
    id: int
    timestamp: str
    rsrp: str
    taType: str
    ulCqi: str
    ulRssi: str
    imsi: str
    ip: str


class CampaignCreate(BaseModel):
    """Campaign Create - Request untuk membuat campaign baru (seperti start scan)"""
    name: str = Field(..., description="Nama campaign")
    imsi: str = Field(..., description="IMSI untuk scanning")
    provider: str = Field(default="", description="Provider/Operator")


class CampaignUpdate(BaseModel):
    """Campaign Update - Request untuk update campaign status (stop)"""
    status: str = Field(..., description="Status campaign (started, stopped, completed, failed)")


class CampaignDetail(BaseModel):
    """Campaign Detail - Response dengan campaign detail dan crawling data"""
    id: int
    name: str
    imsi: str
    provider: str
    status: str | None
    created_at: str
    crawlings: List[CrawlingData] = []


class CampaignListItem(BaseModel):
    """Campaign List Item - Item dalam list campaign"""
    id: int
    name: str
    imsi: str
    provider: str
    status: str | None
    created_at: str
    crawling_count: int = 0


class CampaignListResponse(BaseModel):
    """Campaign List Response - Response untuk list campaign"""
    status: str
    message: str
    data: List[CampaignListItem]
    total: int
