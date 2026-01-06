from app.controller import UdpReceiver
from app.controller import RespUdp
from app.config.utils import PortUDPServer
import threading

receiver_instance = None


def start_receiver():
    global receiver_instance
    receiver_instance = UdpReceiver(host='0.0.0.0', port=PortUDPServer, callback=RespUdp)
    print("Receiver berjalan...")
    receiver_instance.run()


def client_udp():
    receiver_thread = threading.Thread(target=start_receiver)
    receiver_thread.start()


def send_data(message, address):
    if receiver_instance:
        print(f"Message : {message}")
        receiver_instance.send_message(message, address)
    else:
        print("Receiver belum berjalan. Tidak dapat mengirim pesan.")
