import logging


def setup_custom_logger(name , level=logging.DEBUG):
    formatter = logging.Formatter(fmt='%(asctime)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger