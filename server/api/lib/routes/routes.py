"""Route registration lives in :mod:`server.api.main` for the Python API service."""
from server.api.main import app, create_app

__all__ = ("app", "create_app")
