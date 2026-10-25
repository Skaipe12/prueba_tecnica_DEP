import logging

LOG_LEVEL = "INFO"

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(module)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger con la configuración del pipeline ya aplicada."""
    return logging.getLogger(name)
