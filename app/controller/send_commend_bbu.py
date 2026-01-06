from app.config.utils import PortUDPServer
from .udp_client import send_data
from app.config.utils import HOSTDESKTOP, PortUdpClient
import time



class send_commend_modul():
    def __init__(self):
        super().__init__()

    # @pyqtSlot()
    def command(self, udp_ip, command):
       
        send_data(command, (udp_ip, PortUDPServer))

        print(f'data apa ini {command}, {udp_ip}')
