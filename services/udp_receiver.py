from config import BufferSize, MAX_RETRIES
import socket
import time


class UdpReceiver():
    def __init__(self, host, port, callback):
        super().__init__()
        self.host = host
        self.port = port
        self.callback = callback
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))

    def run(self):
        while True:
            data, addr = self.sock.recvfrom(BufferSize)
            message = data.decode()
            # self.received_data.emit(message,addr)
            self.callback(message, addr)

    def send_message(self, message, address):
        try_count = 0
        while try_count < MAX_RETRIES:
            try:
                print(f'>>>>> {message} {address}')
                self.sock.sendto(message.encode('utf-8'), address)
                break
            except OSError as e:
                try_count += 1
                time.sleep(1)
                print(f'error : {e}')
