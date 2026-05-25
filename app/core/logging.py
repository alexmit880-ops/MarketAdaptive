import logging
from logging.handlers import RotatingFileHandler
from .config import LoggingConfig

def setup_logging(cfg: LoggingConfig):
    fmt = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(cfg.level)
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        cfg.file,
        maxBytes=_parse_size(cfg.rotation),
        backupCount=10,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(file_handler)

def _parse_size(s: str) -> int:
    value, unit = s.split()
    value = int(value)
    unit = unit.upper()
    return value * 1024 * 1024 if unit == "MB" else value
