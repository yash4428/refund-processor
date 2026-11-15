# Payments API (local mock)

Base URL: `http://localhost:4343`

Authentication: send `Authorization: Bearer sk_test_refunds_practice` on every request.

All amounts are integers in the smallest currency unit (cents for `usd`).

**Request bodies are form-encoded** (`Content-Type: application/x-www-form-urlencoded`), not JSON. Responses are JSON.

## The charge object

| Field | Type | Notes |
|---|---|---|
| `id` | string | e.g. `ch_0001` |
| `amount` | integer | cents |
| `amount_refunded` | integer | cents refunded so far |
| `currency` | string | |
| `customer` | string | |
| `status` | string | `succeeded` or `failed` |
| `created` | integer | Unix timestamp |

## GET /v1/charges

Lists charges, oldest first.

| Query parameter | Notes |
|---|---|
| `limit` | 1..10, default 10 |
| `starting_after` | A charge id. Returns the page after that charge. |

Response: `{"object": "list", "data": [...], "has_more": true}`

## GET /v1/charges/{id}

Returns one charge, or 404.

## POST /v1/refunds

Refunds all or part of a charge.

| Param | Required | Notes |
|---|---|---|
| `charge` | yes | Charge id |
| `amount` | no | Cents. Defaults to the full unrefunded amount. |
| `reason` | no | `duplicate`, `fraudulent` or `requested_by_customer` |
| `metadata[KEY]` | no | Any number of string key/value pairs, e.g. `metadata[order]=o_1` |

Headers: `Idempotency-Key` (optional, recommended).

Response (200): the refund object.

```
{"id": "re_0001", "object": "refund", "amount": 2500, "charge": "ch_0001",
 "currency": "usd", "reason": "requested_by_customer", "metadata": {}, "status": "succeeded", "created": 1794053026}
```

### Idempotency

The first request with a key is executed. A later request with the same key and the same params is not executed again: it returns the saved status and body, with the header `Idempotent-Replayed: true`. The same key with different params returns 400 with error type `idempotency_error`.

### Status codes

| Status | Meaning |
|---|---|
| 200 | Refund created (or replayed) |
| 400 | Invalid request, e.g. amount greater than the unrefunded amount |
| 401 | Missing or invalid API key |
| 404 | No such charge |
| 429 | Rate limited. `Retry-After` gives the seconds to wait. |
| 5xx | Server error. The refund may or may not have been applied. Retry with the same `Idempotency-Key`. |

## GET /v1/refunds

Lists all refunds: `{"object": "list", "data": [...], "has_more": false}`

## Errors

```
{"error": {"type": "invalid_request_error", "message": "..."}}
```
