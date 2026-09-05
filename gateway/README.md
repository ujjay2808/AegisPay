# AegisPay Gateway

FastAPI gateway for the AegisPay Review 2 protocol-simulation flow: AP2-style Intent -> Cart -> simulated Payment, canonical normalization, spend-cap governance, and PostgreSQL persistence.

## Run locally

From the `gateway` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Check the service at <http://127.0.0.1:8000/health>.

Expected response:

```json
{ "status": "ok", "service": "aegispay-gateway" }
```

## Configuration

Copy `.env.example` to `.env` and set values for the deployment environment. The application reads:

- `SERVICE_NAME`: service name returned by the health endpoint.
- `ENVIRONMENT`: deployment environment name.
- `LOG_LEVEL`: Python logging level.
- `DATABASE_URL`: PostgreSQL connection URL used by SQLAlchemy and Alembic. URL-encode reserved characters in passwords, such as `@` as `%40`.
- `SPEND_CAP_AMOUNT`: global spend cap, default `5000.00`.
- `SPEND_CAP_CURRENCY`: global spend-cap currency, default `INR`.

No credentials are committed to the repository.

## PostgreSQL and migrations

Set `DATABASE_URL` in `.env` to the PostgreSQL database used by the gateway. The URL uses the SQLAlchemy format, for example:

```text
postgresql+psycopg://USER:PASSWORD@localhost:5432/aegispay_gateway
```

Apply the schema with:

```powershell
alembic upgrade head
```

Create a new migration after model changes with:

```powershell
alembic revision --autogenerate -m "describe change"
```

Run tests with:

```powershell
pytest -q
```

## Architecture

```text
AP2 request -> AP2 adapter -> canonical model -> policy engine -> PostgreSQL repository
```

The HTTP routes delegate to the mandate flow service. The protocol adapter boundary keeps policy logic independent of AP2 and leaves room for a future x402 adapter. The repository boundary keeps the flow service independent of SQLAlchemy; the in-memory repository remains available for isolated unit tests.

## API flow

1. Create an intent:

```powershell
$intent = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/mandates/intent -ContentType 'application/json' -Body '{"agent_id":"agent-1","user_id":"user-1","purpose":"Purchase office supplies","spending_constraints":{"max_amount":"5000.00","currency":"INR"}}'
```

2. Create a cart using the returned `intent_id`. The server calculates the total from item quantities and unit prices; clients cannot supply the authoritative total.

3. Create a simulated payment using the returned `cart_id`, one of `SIMULATED_CARD`, `SIMULATED_BANK`, or `SIMULATED_WALLET`, and a unique `idempotency_key`.

An amount less than or equal to the effective spend cap returns `APPROVED` with `WITHIN_SPEND_LIMIT`. An amount above the cap returns `ESCALATED` with `SPEND_LIMIT_EXCEEDED`. A lower same-currency intent limit takes precedence over the global cap. These are policy outcomes, not fraud classifications.

Repeated payment requests with the same idempotency key return the original payment result. Reusing a key for another cart returns `IDEMPOTENCY_KEY_CONFLICT`.

## Error responses

Public errors use this shape and never include stack traces or database details:

```json
{ "code": "CART_NOT_FOUND", "message": "Cart was not found" }
```

Validation failures use `VALIDATION_ERROR`; database failures use `DATABASE_UNAVAILABLE`; unexpected failures use `INTERNAL_ERROR`.

## Review 2 scope

Included: AP2-style simulation, canonical normalization, Intent -> Cart -> Payment relationships, simulated payment methods, PostgreSQL persistence, Alembic migrations, and the spend-cap policy.

Not included: ML/fraud detection, SHAP, blockchain/Web3, real payment processing, x402 implementation, Redis, dashboard, deployment infrastructure, and AWS/Kubernetes configuration.
