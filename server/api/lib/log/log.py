import logging


def log_to_file(message: str) -> None:
    logging.getLogger("api_analytics.api").info(message)
