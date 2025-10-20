import os
import time

import requests


BASE_URL = os.environ.get("AEGIS_BASE_URL", "http://localhost:8000")


def _wait_for_api(timeout_sec: int = 180) -> None:
    start = time.time()
    url = f"{BASE_URL}/api/v1/health/"
    while time.time() - start < timeout_sec:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError(f"API not healthy after {timeout_sec}s: {url}")


def test_basic_health():
    _wait_for_api()
    r = requests.get(f"{BASE_URL}/api/v1/health/", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") in ("healthy", "degraded", "unhealthy")
    assert "version" in data
