"""HTTP checks used by the monitoring CLI."""
import os
import requests
BASE_URL = os.getenv("API_ANALYTICS_URL", "https://apianalytics-server.com/api")
def request(path: str) -> requests.Response: return requests.get(f"{BASE_URL}/{path.lstrip('/')}", timeout=10)
