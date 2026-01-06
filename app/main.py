from fastapi import FastAPI, HTTPException, Header
from app.controller import client_udp
import sys
import threading
import uvicorn
import os

from app.service.restapiService import app



class MyApp():

    def __init__(self):
        super().__init__()   

    def start_fastapi_server(self):
        """Jalankan server FastAPI di thread terpisah."""
        uvicorn.run(app, host="0.0.0.0", port=8888)

    def start_app(self):
        # self.delete_files()
        # app = QCoreApplication(sys.argv)

        # Jalankan FastAPI di thread terpisah
        api_thread = threading.Thread(target=self.start_fastapi_server, daemon=True)
        api_thread.start()

        client_udp()
        print("Server UDP sudah berjalan.........")
        # sys.exit(app.exec())
