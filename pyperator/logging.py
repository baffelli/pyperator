import logging as _log


def setup_custom_logger(name , level=_log.DEBUG, file=None):
    formatter = _log.Formatter(fmt='%(asctime)s  %(levelname)s- %(name)s - %(message)s')

    handler = _log.StreamHandler()
    handler.setFormatter(formatter)

    logger = _log.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    if file:
        file_handler = _log.FileHandler(file, mode='w+')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger