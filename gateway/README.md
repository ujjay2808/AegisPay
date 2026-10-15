# AegisPay Gateway

FastAPI gateway for the AegisPay protocol-simulation flow: AP2-style Intent -> Cart -> Payment, canonical normalization, policy governance (spend cap + merchant blocklist), PostgreSQL persistence, and on-chain audit logging through the backend-gateway Java service on Polygon Amoy.

## Run locally

From the `gateway` directory:

```zsh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Check the service at <http://127.0.0.1:8000/health>.

Expected response:

```json
{ "status": "ok", "service": "aegispay-gateway" }
```

## Run the full stack

From the repo root, start the local stack with:

```zsh
docker compose up --build
```

This starts PostgreSQL, the gateway on port `8000`, and the backend-gateway Java service on port `8080`. The root `.env` file must define `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` (see `.env.example`).

## Configuration

Copy `.env.example` to `.env` and set values for the deployment environment. The application reads:

- `SERVICE_NAME`: service name returned by the health endpoint.
- `ENVIRONMENT`: deployment environment name.
- `LOG_LEVEL`: Python logging level.
- `DATABASE_URL`: PostgreSQL connection URL used by SQLAlchemy and Alembic. URL-encode reserved characters in passwords, such as `@` as `%40`.
- `SPEND_CAP_AMOUNT`: global spend cap, default `5000.00`.
- `SPEND_CAP_CURRENCY`: global spend-cap currency, default `INR`.
- `BLOCKED_MERCHANT_IDS`: comma-separated merchant IDs, case-insensitive; payments to them are `DENIED` with reason code `MERCHANT_BLOCKED` before spend-cap checks. Default empty.
- `AUDIT_ENABLED`: whether every payment decision is sent to the audit service. Default `false`.
- `AUDIT_SERVICE_URL`: audit service base URL. Default `http://localhost:8080` and `http://backend-gateway:8080` inside Docker Compose.
- `AUDIT_TIMEOUT_SECONDS`: audit request timeout in seconds. Default `30`.

No credentials are committed to the repository.

## PostgreSQL and migrations

The API tests require a running PostgreSQL instance. From the repo root, start it with:

```zsh
docker compose up -d postgres
```

Then set `DATABASE_URL` in `gateway/.env` to the PostgreSQL database used by the gateway. Use the SQLAlchemy format and point it at `localhost:5432`, for example:

```text
postgresql+psycopg://USER:PASSWORD@localhost:5432/aegispay_gateway
```

Apply the schema with:

```zsh
cd gateway
alembic upgrade head
```

Create a new migration after model changes with:

```zsh
cd gateway
alembic revision --autogenerate -m "describe change"
```

Run tests with:

```zsh
cd gateway
pytest -q
```

## Architecture

```text
AP2 request -> AP2 adapter -> canonical model -> policy engine -> PostgreSQL repository
```

The HTTP routes delegate to the mandate flow service. The protocol adapter boundary keeps policy logic independent of AP2 and leaves room for a future x402 adapter. The repository boundary keeps the flow service independent of SQLAlchemy; the in-memory repository remains available for isolated unit tests.

## API flow

1. Create an intent:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/mandates/intent -H 'Content-Type: application/json' -d '{"agent_id":"agent-1","user_id":"user-1","purpose":"Purchase office supplies","spending_constraints":{"max_amount":"5000.00","currency":"INR"}}'
```

The response contains the `intent_id` used in the next step.

2. Create a cart using the returned `intent_id`. The server calculates the total from item quantities and unit prices; clients cannot supply the authoritative total.

3. Create a simulated payment using the returned `cart_id`, one of `SIMULATED_CARD`, `SIMULATED_BANK`, or `SIMULATED_WALLET`, and a unique `idempotency_key`.

An amount less than or equal to the effective spend cap returns `APPROVED` with `WITHIN_SPEND_LIMIT`. An amount above the cap returns `ESCALATED` with `SPEND_LIMIT_EXCEEDED`. A lower same-currency intent limit takes precedence over the global cap. These are policy outcomes, not fraud classifications.

Repeated payment requests with the same idempotency key return the original payment result. Reusing a key for another cart returns `IDEMPOTENCY_KEY_CONFLICT`.

## Blockchain audit logging

The payment response includes `audit_tx_hash` and the value is stored in the `payments.audit_tx_hash` database column. When audit is disabled or the audit call fails, `audit_tx_hash` is `null`.

The gateway is fail-open: if the audit service is unreachable or the transaction fails, the payment is still saved, a warning is logged, and `audit_tx_hash` remains `null`.

When audit is enabled, a payment request waits until the transaction is mined (usually a few seconds, up to 20 seconds). The decision hash is computed as `"0x" + SHA-256(JSON({transaction_id, cart_id, amount, currency, decision, reason_code}, sort_keys=True, separators=(",", ":")))` where `amount` is a string like `"500.00"`. The hash is not stored in the database; only the transaction hash is persisted.

To verify a decision on-chain, use the Java backend-gateway service at `http://localhost:8080/api/decisions/{decisionHash}`. A successful response is:

```json
{ "decisionHash": "0x...", "decision": "APPROVED", "timestamp": 1792039806, "submittedBy": "0x..." }
```

timestamp is a Unix timestamp in seconds and submittedBy is the wallet address that submitted the audit transaction. decision is APPROVED, DENIED or ESCALATED.

A missing record returns:

```json
{ "error": "Record not found" }
```

A malformed hash returns `400` and the hash must be `0x` followed by 32 bytes.

## Error responses

Public errors use this shape and never include stack traces or database details:

```json
{ "code": "CART_NOT_FOUND", "message": "Cart was not found" }
```

Validation failures use `VALIDATION_ERROR`; database failures use `DATABASE_UNAVAILABLE`; unexpected failures use `INTERNAL_ERROR`.

## Scope

Included: AP2-style simulation, canonical normalization, Intent -> Cart -> Payment relationships, simulated payment methods, PostgreSQL persistence, Alembic migrations, the spend-cap policy, the merchant blocklist, audit logging, and the decision verification endpoint.

Not included: ML/fraud detection, real payment processing, x402 implementation, Redis, dashboard, deployment infrastructure, and AWS/Kubernetes configuration.
