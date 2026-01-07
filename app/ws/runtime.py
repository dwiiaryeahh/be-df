# app/ws/runtime.py
import asyncio
from typing import Optional

main_loop: Optional[asyncio.AbstractEventLoop] = None
