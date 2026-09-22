import logging

def log_to_file(message: str) -> None: logging.getLogger("api_analytics.logger").info(message)
def log_error_to_file(_ip: str, _key: str, message: str) -> None: log_to_file(message)
def log_requests_to_file(key: str, inserted: int, total: int) -> None: log_to_file(f"key={key}: inserted {inserted}/{total}")
