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
    ip: str = Field(..., description="IP device yang akan di-start")


class StopOneRequest(BaseModel):
    ip: str = Field(..., description="IP device yang akan di-stop")


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
    ch: str
    provider: str | None = None
    count: int | None = None
    alert_status: str | None = None
    alert_name: str | None = None


class CampaignCreate(BaseModel):
    """Campaign Create - Request untuk membuat campaign baru (seperti start scan)"""
    name: str = Field(default="", description="Nama campaign")
    imsi: str = Field(default="", description="IMSI untuk scanning")
    mode: str = Field(default="" ,description="WB: Whitelist, Blacklist, All | DF : DF")
    provider: Optional[str] = Field(default="", description="Provider/Operator")
    duration: Optional[str] = Field(None, description="Duration in MM:SS format (e.g., 05:00 for 5 minutes)")


class CampaignUpdate(BaseModel):
    """Campaign Update - Request untuk update campaign status (stop)"""
    status: str = Field(..., description="Status campaign (started, stopped, completed, failed)")


class CampaignDetail(BaseModel):
    """Campaign Detail - Response dengan campaign detail dan crawling data"""
    id: int
    name: str
    imsi: str
    provider: str
    mode: str
    status: str | None
    duration: str | None = None
    created_at: str
    start_scan: str | None = None
    stop_scan: str | None = None
    crawlings: List[CrawlingData] = []


class CampaignListItem(BaseModel):
    """Campaign List Item - Item dalam list campaign"""
    id: int
    name: str
    imsi: str
    provider: str
    status: str | None
    mode: str | None
    created_at: str
    start_scan: str | None = None
    stop_scan: str | None = None
    crawling_count: int = 0


class CampaignListResponse(BaseModel):
    """Campaign List Response - Response untuk list campaign"""
    status: str
    message: str
    data: List[CampaignListItem]
    total: int


# ==========================================
# Target Models - Untuk endpoint target
# ==========================================

class TargetCreate(BaseModel):
    """Target Create - Request untuk membuat target baru"""
    name: str = Field(..., description="Nama target")
    imsi: str = Field(..., description="IMSI target")
    alert_status: Optional[str] = Field(None, description="Status alert")
    target_status: Optional[str] = Field(None, description="Status target")
    campaign_id: Optional[int] = Field(None, description="Optional campaign ID untuk integrasi dengan campaign yang sedang berjalan")


class TargetUpdate(BaseModel):
    """Target Update - Request untuk update target"""
    name: Optional[str] = Field(None, description="Nama target")
    imsi: Optional[str] = Field(None, description="IMSI target")
    alert_status: Optional[str] = Field(None, description="Status alert")
    target_status: Optional[str] = Field(None, description="Status target")


class TargetResponse(BaseModel):
    """Target Response - Response untuk single target"""
    id: int
    name: str
    imsi: str
    alert_status: Optional[str]
    target_status: Optional[str]
    created_at: str
    updated_at: str

class TargetSingleResponse(BaseModel):
    status: str
    message: str
    data: TargetResponse

class TargetListResponse(BaseModel):
    """Target List Response - Response untuk list target"""
    status: str
    message: str
    data: List[TargetResponse]
    total: Optional[int]


class TargetImportResponse(BaseModel):
    """Target Import Response - Response untuk import target dari XLSX"""
    status: str
    message: str
    imported: int
    failed: int
    errors: List[str] = []


# ==========================================
# Command Models - Untuk unified command endpoint
# ==========================================

class CommandRequest(BaseModel):
    """Command Request - Mode-based bundled commands"""
    mode: str = Field(..., description="Mode: whitelist, blacklist, all, df")
    imsi: Optional[str] = Field(None, description="IMSI target (space-separated for multiple)")
    duration: Optional[str] = Field(None, description="Duration in MM:SS format")
    provider: Optional[str] = Field(None, description="Provider for df mode")
    ip: Optional[str] = Field(None, description="Specific IP (optional, default: all IPs)")


class CommandResult(BaseModel):
    """Command Result - Detail hasil command untuk satu IP"""
    ip: str
    status: str
    error: Optional[str] = None
    file_exists: Optional[bool] = None
    file_path: Optional[str] = None
    message: Optional[str] = None
    provider: Optional[str] = None


class CommandResponse(BaseModel):
    """Unified Command Response - Response untuk endpoint /command"""
    status: str
    last_checked: str
    details: List[CommandResult]
