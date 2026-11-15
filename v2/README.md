# Plutus AI 2.0 — foundation release

This is a working **local** vertical slice, not a production-ready brokerage or complete implementation of the master brief. The legacy Django application remains untouched. New code lives under `v2/`.

## Implemented journey

Register a development account → sign in → initialize virtual capital → save a watchlist identifier → record a confirmed paper scenario → see cash, positions and realized P&L → export CSV → log out. Manual transactions use a separate portfolio. All records persist in the configured database. Virtual capital cannot be withdrawn.

The UI displays no synthetic market series, invented quotes, generated research or fabricated forecasts. All paper prices are user-entered **hypothetical scenario prices**. These are immediate scenario fills, NOT market-session-aware paper execution. Fees are an explicit simulation assumption of 10 bps on each side, rounded half up to paise. No liquidity, bid/ask, holidays, tax model, slippage or pending orders are simulated. Manual trades currently do not support fees.

## Run locally

Requires Python 3.12+ and Node 22+.

```bash
cd v2/apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PLUTUS_ENV=development DATABASE_URL=sqlite:///plutus-local.db APP_ORIGIN=http://localhost:3000 uvicorn plutus.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd v2/apps/web
npm ci
API_ORIGIN=http://127.0.0.1:8000 npm run dev
```

Open http://localhost:3000. Register with a password of at least 12 characters. Development accounts do not send verification emails. This mode must never be exposed publicly. The development database is initialized automatically. API docs: http://127.0.0.1:8000/docs.

## Test

```bash
cd v2/apps/api
pip install -r research/requirements.txt
PYTHONPATH=. python -m pytest tests -q
cd ../web
npm run build
```

Tests exercise real SQL transactions through FastAPI, access isolation, session revocation, CSRF origin checks, idempotency conflicts, duplicate/concurrent execution, insufficient funds/shares, non-finite prices, pooled-cost accounting, export and forecast feature alignment. They use temporary SQLite databases. PostgreSQL concurrency and deployed Supabase auth need separate integration verification.

## Production configuration (not yet completed)

1. Create a dedicated Supabase project. Do not reuse SkillBridge tables or credentials.
2. Set `DATABASE_URL` to its verified TLS PostgreSQL connection and configure a restricted backend database role.
3. From `apps/api`, run `alembic upgrade head`. The initial migration enables RLS and revokes browser role access. The backend uses explicit user scoping on every query. The initial backend role needs owner-equivalent access; a restricted-role policy design is a launch blocker.
4. Configure `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, email confirmation and a verified email sender. No service-role key belongs in a browser.
5. Configure `PLUTUS_ENV=production` and `APP_ORIGIN` to the exact frontend HTTPS origin. The API fails closed without a database or authentication configuration.
6. Deploy `apps/api` to a persistent Python service using its Dockerfile (e.g. Render). PostgreSQL is mandatory in production. `index.py` also exposes the ASGI app for Vercel FastAPI hosting; long-running research jobs must run elsewhere.
7. Deploy `apps/web` as a Next.js project on Vercel, with server-side `API_ORIGIN` set to the backend origin. The frontend uses a same-origin reverse proxy and HttpOnly cookies.
8. Run deployed authentication, persistence, isolation and origin tests. Configure shared rate limits, structured audit logs, monitoring, backup restoration drills and the remaining launch controls before opening public accounts.

Production auth calls Supabase signup, password token and authenticated user endpoints. This transport has not been tested against a provisioned Plutus project. Refresh-token rotation, password reset, MFA, OAuth, account deletion/export and device revocation remain incomplete. Current sessions expire after one hour and require login again.

## Offline quantitative research

```bash
cd v2/apps/api
pip install -r research/requirements.txt
python -m research.evaluate YOUR_LICENSED_HISTORY.csv --horizon 5 --source 'vendor/dataset/version' > evaluation.json
```

Input: one security, unique chronological `date,adjusted_close` daily session rows. At least 350 complete feature/target rows are required. Horizons: 1, 5 and 20 trading observations. Expanding-window evaluation purges training labels that would be unobserved at each test decision. A histogram gradient boosting model is compared with no-change and trailing-mean-return baselines. Reports include MAE, RMSE, directional accuracy, fold boundaries, data hash and baseline comparison. No stock model has been evaluated on licensed data in this session. Unit-test synthetic data is never financial evidence. Probabilities, intervals and deployment eligibility are explicitly absent/false.

## Integration blockers

See [feature status](docs/FEATURE_STATUS.md), [architecture](docs/ARCHITECTURE.md) and [verification](docs/VERIFICATION.md). Environment placeholders for future services are enumerated in `.env.example`; those integrations are not implemented merely because their variable exists.
