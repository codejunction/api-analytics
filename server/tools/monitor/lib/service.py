import requests

def service_down(url: str) -> bool:
    try: return requests.get(url, timeout=10).status_code >= 500
    except requests.RequestException: return True
