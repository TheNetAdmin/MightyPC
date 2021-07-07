import logging


def setup_logger(filename):
    log_format = logging.Formatter(
        "[%(asctime)s][%(filename)s:%(lineno)4s - %(funcName)10s()][%(levelname)s] %(message)s"
    )
    handler = logging.StreamHandler()
    handler.setFormatter(log_format)
    logging.getLogger().addHandler(handler)
    handler = logging.FileHandler(f"{filename}.log")
    handler.setFormatter(log_format)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
