import logging


def setup_custom_logger(name , level=logging.DEBUG, file=None):
    formatter = logging.Formatter(fmt='%(asctime)s  %(levelname)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    if file:
        file_handler = logging.FileHandler(file, mode='w+')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger