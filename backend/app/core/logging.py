import logging
import os

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

logger = setup_logger(__name__)
