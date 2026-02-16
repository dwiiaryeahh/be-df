import logging
import os
from datetime import datetime

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG) 

    os.makedirs("logs", exist_ok=True)

    if not logger.handlers:
        levels = [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL")
        ]

        for level, level_name in levels:
            handler = logging.FileHandler(f"logs/{level_name}.log")
            handler.setLevel(level)
            
            def create_filter(lvl):
                return lambda record: record.levelno == lvl
            
            handler.addFilter(create_filter(level))
            
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            
            logger.addHandler(handler)

    return logger