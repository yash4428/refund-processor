import requests


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(f"{status}: {message}")
        self.status = status
        self.message = message


class ApiClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_key}"

    def get(self, path, params=None):
        response = self.session.get(self.base_url + path, params=params, timeout=10)
        if not response.ok:
            raise ApiError(response.status_code, response.json()["error"]["message"])
        return response.json()
