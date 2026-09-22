import os


def get_env_variable(name: str, default: str) -> str:
    return os.getenv(name) or default


def get_integer_env_variable(name: str, default: int) -> int:
    try:
        return int(get_env_variable(name, str(default)))
    except ValueError:
        return default
