# Refund Processor

Support agents collect refund requests in a CSV file. You will build a tool that checks them against the Payments API and issues the refunds.

**Time limit:** 60 minutes. **Rules:** no AI tools; Google and official docs are allowed.

Your interviewer will give you the next part when the current one works.

## Setup

Needs Python 3.8+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start the mock API in its own terminal (from this folder, venv active):

```bash
python server/mock_api.py
```

Then, in another terminal:

```bash
python main.py
pytest -q
```

The server keeps its data in memory. Restart it to reset everything.

## Files

- `main.py`: entry point. Write your code here and in `refunds/`.
- `refunds/client.py`: a small API client (GET only so far)
- `refunds/csv_reader.py`: reads the CSV
- `data/refund_requests.csv`: the refund requests
- `docs/payments_api.md`: Payments API documentation
- `server/mock_api.py`: the local mock API (don't change it)
- `tests/`: pytest tests
- `output/`: save generated files here

## Part 1

For each row in `data/refund_requests.csv`, decide if the refund request is valid, using the charge data from the API. Print one line per request, in file order:

```
req_001: OK 2500
req_003: REJECTED <reason>
```

`OK` is followed by the refund amount in cents. The `amount` column is in dollars, or the word `full`, which means everything not yet refunded on that charge.

A request is rejected if the amount can't be read or isn't positive, the charge doesn't exist, the charge didn't succeed, nothing is left to refund, or the amount is more than what's left to refund. Check each request on its own against the charge as the API returns it.

Finish with:

```
OK: N, REJECTED: M, total to refund: X cents
```

Add tests for your amount parsing.
