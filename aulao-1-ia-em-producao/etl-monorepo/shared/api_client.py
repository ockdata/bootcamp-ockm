import requests
import os


class APIClient:
    """Generic HTTP API client."""

    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = base_url or os.environ.get("API_BASE_URL", "")
        self.token = token or os.environ.get("API_TOKEN", "")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def get(self, path: str, params: dict = None) -> dict:
        response = self.session.get(f"{self.base_url}{path}", params=params)
        response.raise_for_status()
        return response.json()
