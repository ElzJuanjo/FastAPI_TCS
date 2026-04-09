import logging
import os
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)

    log_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] "
        "[%(name)s:%(lineno)d] %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    root_logger.handlers.clear()

    # File handler
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(LOG_LEVEL)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(LOG_LEVEL)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Service loggers
    for name, filename in [
        ("payments", "payments.log"),
        ("siesa", "siesa.log"),
        ("email", "email.log"),
        ("placetopay", "placetopay.log"),
    ]:
        _create_service_logger(name, filename, log_format)


def _create_service_logger(name, filename, formatter):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    logger.handlers.clear()

    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, filename),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    handler.setFormatter(formatter)
    handler.setLevel(LOG_LEVEL)

    logger.addHandler(handler)
    logger.propagate = False
