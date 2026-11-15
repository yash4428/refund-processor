import os

from refunds.client import ApiClient
from refunds.csv_reader import read_requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:4343")
API_KEY = os.environ.get("API_KEY", "sk_test_refunds_practice")


def main():
    client = ApiClient(BASE_URL, API_KEY)
    rows = read_requests("data/refund_requests.csv")
    print(f"Loaded {len(rows)} refund requests")


if __name__ == "__main__":
    main()
