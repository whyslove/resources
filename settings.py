import logging


logs = {'INFO': logging.INFO,
        'DEBUG': logging.DEBUG}


def create_logger(mode='INFO'):
    logger = logging.getLogger('nvr_resources')
    logger.setLevel(logs[mode])

    ch = logging.StreamHandler()
    ch.setLevel(logs[mode])

    formatter = logging.Formatter(
        '%(levelname)-8s  %(asctime)s    %(message)s',
        datefmt='%d-%m-%Y %I:%M:%S %p')

    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger

