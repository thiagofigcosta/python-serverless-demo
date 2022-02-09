import logging
import os
import sys

LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', 'INFO').upper()


def setup_and_get_logger(name=None):
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(LOGGING_LEVEL)
    logger.addHandler(handler)
    logger.propagate = False  # to prevent log duplication in lambda

    logging.getLogger('boto3').setLevel(logging.CRITICAL)
    logging.getLogger('botocore').setLevel(logging.CRITICAL)

    return logger
