HOST = '0.0.0.0'
HOSTDESKTOP = '127.0.0.1'
BufferSize = 955350

# Max RTO
MAX_RETRIES = 10
PortUDPServer = 9001
PortMyApp = 1236
PortUdpClient = 7001

HeartBeat = "HeartBeat"
GPSInfoIndi = "GPSInfoIndi"
GetCellParaRsp = "GetCellParaRsp"
SetCellPara = "SetCellPara"
GetAppCfgExtRsp = "GetAppCfgExtRsp"
SetAppCfgExt = "SetAppCfgExt"
GetNmmCfg = "GetNmmCfgRsp"
StartCell = "StartCell"
StopCell = "StopCell"
OneUeInfoIndi = "OneUeInfoIndi"
SetBlackList = "SetBlackList" # + " " + IMSI
SetUlPcPara = "SetUlPcPara 40 30 1"

db_setting = "setting.db"
db_heartbeat = "heartbeat.db"
db_gps = "gps_info.db"
db_sniffer = "sniffer.db"
db_provider = "provider.db"
GSM_WB = "GSM-WB"

CREATEDB = 86400

TIMESENDHEARTBEAT = 5000
TIMESENDIMSI = 2000
TIMESENDSNIFF = 2000

# Max send imsi
MAX_IMSI = 20

# Max RTO
MAX_RETRIES = 10

status_variabel = {"SNIFF" : 0}

token_bbu = "e3b0c44298fc1c149afbf4c8996fb924"

CRAWLING_JSON = "crawling.json"
GPS_JSON = "gps.json"
