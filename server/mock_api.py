"""Local mock of a payments API (charges + refunds).

Run:  python server/mock_api.py            (normal)
      python server/mock_api.py --flaky    (some requests fail with 429/5xx)

Listens on http://localhost:4343. Data resets every time the server starts.
"""
import json
import random
import sys
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT = 4343
API_KEY = "sk_test_refunds_practice"
FLAKY = "--flaky" in sys.argv


def make_charges():
    rng = random.Random(42)
    customers = ["cus_amy", "cus_ben", "cus_cho", "cus_dev", "cus_eli"]
    charges = []
    for i in range(1, 31):
        amount = rng.randrange(500, 20000, 5)
        status = "failed" if i in (7, 19) else "succeeded"
        refunded = 0
        if i in (4, 12, 25):
            refunded = amount // 2
        if i == 16:
            refunded = amount
        charges.append({
            "id": f"ch_{i:04d}",
            "object": "charge",
            "amount": amount,
            "amount_refunded": refunded,
            "currency": "usd",
            "customer": customers[i % 5],
            "status": status,
            "created": 1793000000 + i * 3600,
        })
    return charges


STATE = {"charges": make_charges(), "refunds": [], "idem": {}, "attempts": {}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.command, self.path))

    def send_json(self, status, body, headers=None):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def error(self, status, message, type_="invalid_request_error", headers=None):
        self.send_json(status, {"error": {"type": type_, "message": message}}, headers)

    def authorized(self):
        if self.headers.get("Authorization") != f"Bearer {API_KEY}":
            self.error(401, "Invalid API key provided", "authentication_error")
            return False
        return True

    def do_GET(self):
        if not self.authorized():
            return
        url = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        parts = url.path.strip("/").split("/")

        if parts == ["v1", "charges"]:
            try:
                limit = int(query.get("limit", 10))
            except ValueError:
                return self.error(400, "limit must be an integer")
            if not 1 <= limit <= 10:
                return self.error(400, "limit must be between 1 and 10")
            charges = STATE["charges"]
            start = 0
            if "starting_after" in query:
                ids = [c["id"] for c in charges]
                if query["starting_after"] not in ids:
                    return self.error(400, "starting_after: no such charge")
                start = ids.index(query["starting_after"]) + 1
            page = charges[start:start + limit]
            return self.send_json(200, {"object": "list", "data": page,
                                        "has_more": start + limit < len(charges)})

        if len(parts) == 3 and parts[:2] == ["v1", "charges"]:
            for c in STATE["charges"]:
                if c["id"] == parts[2]:
                    return self.send_json(200, c)
            return self.error(404, f"No such charge: '{parts[2]}'")

        if parts == ["v1", "refunds"]:
            return self.send_json(200, {"object": "list", "data": STATE["refunds"], "has_more": False})

        self.error(404, "Unrecognized request URL")

    def do_POST(self):
        if not self.authorized():
            return
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode()

        if url.path != "/v1/refunds":
            return self.error(404, "Unrecognized request URL")

        if "application/x-www-form-urlencoded" not in self.headers.get("Content-Type", ""):
            return self.error(400, "Request body must be form-encoded (application/x-www-form-urlencoded)")
        params = {k: v[0] for k, v in parse_qs(raw).items()}
        key = self.headers.get("Idempotency-Key")

        if key:
            saved = STATE["idem"].get(key)
            if saved:
                if saved["params"] != params:
                    return self.error(400, "Keys for idempotent requests can only be used with the same parameters they were first used with.", "idempotency_error")
                return self.send_json(saved["status"], saved["body"], {"Idempotent-Replayed": "true"})

        failure = None
        if FLAKY and key:
            n = STATE["attempts"].get(key, 0) + 1
            STATE["attempts"][key] = n
            h = zlib.crc32(key.encode())
            if h % 4 == 0 and n == 1:
                return self.error(429, "Too many requests", "rate_limit_error", {"Retry-After": "1"})
            if h % 4 == 1 and n == 1:
                return self.error(503, "Service temporarily unavailable", "api_error")
            if h % 4 == 2 and n == 1:
                failure = "after"   # apply the refund, then fail anyway

        status, body = self.create_refund(params)
        if key:
            STATE["idem"][key] = {"params": params, "status": status, "body": body}
        if failure == "after":
            return self.error(500, "Internal server error", "api_error")
        self.send_json(status, body)

    def create_refund(self, params):
        charge_id = params.get("charge")
        if not charge_id:
            return 400, {"error": {"type": "invalid_request_error", "message": "Missing required param: charge."}}
        charge = next((c for c in STATE["charges"] if c["id"] == charge_id), None)
        if charge is None:
            return 404, {"error": {"type": "invalid_request_error", "message": f"No such charge: '{charge_id}'"}}
        if charge["status"] != "succeeded":
            return 400, {"error": {"type": "invalid_request_error", "message": "Charge did not succeed, so it cannot be refunded."}}
        remaining = charge["amount"] - charge["amount_refunded"]
        if "amount" in params:
            try:
                amount = int(params["amount"])
            except ValueError:
                return 400, {"error": {"type": "invalid_request_error", "message": "Invalid integer: amount"}}
            if amount <= 0:
                return 400, {"error": {"type": "invalid_request_error", "message": "amount must be positive"}}
        else:
            amount = remaining
        if remaining == 0:
            return 400, {"error": {"type": "invalid_request_error", "message": f"Charge {charge_id} has already been refunded."}}
        if amount > remaining:
            return 400, {"error": {"type": "invalid_request_error", "message": f"Refund amount ({amount}) is greater than unrefunded amount on charge ({remaining})."}}
        charge["amount_refunded"] += amount
        refund = {
            "id": f"re_{len(STATE['refunds']) + 1:04d}",
            "object": "refund",
            "amount": amount,
            "charge": charge_id,
            "currency": charge["currency"],
            "reason": params.get("reason"),
            "metadata": {k[9:-1]: v for k, v in params.items() if k.startswith("metadata[")},
            "status": "succeeded",
            "created": int(time.time()),
        }
        STATE["refunds"].append(refund)
        return 200, refund


if __name__ == "__main__":
    mode = " (flaky mode)" if FLAKY else ""
    print(f"Mock API on http://localhost:{PORT}{mode}. Ctrl+C to stop.", flush=True)
    ThreadingHTTPServer(("localhost", PORT), Handler).serve_forever()
