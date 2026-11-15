# Verification evidence

Date: 2026-11-16. Only observed results belong here.

- Repository cloned: `Doublezippin44/Plutus-AI2`, branch `feat/plutus-v2-foundation`.
- Next.js production build passed, including TypeScript checking.
- Eight automated tests passed initially: six API/accounting/security tests and two research tests. Final rerun results recorded below if changed.
- Tests use temporary SQLite and synthetic research fixtures. No actual market forecasting performance was measured.
- No real trade, payment, or email was sent.
- Supabase discovery found a healthy SkillBridge project and an unrelated inactive project. Neither was modified. A dedicated Plutus project was not provisioned; organization choice remains unresolved.
- Vercel discovery found no existing Plutus project.
- Resend discovery found one domain in failed status; no deliverability is claimed.
- Managed browser preview failed because its runner appended Vite-only `--host` and `--strictPort` arguments to `next dev`. Browser QA was not replaced with another local browser path.
- Hosted PostgreSQL migration, Supabase authentication, checkout, broker sandbox and provider integrations are unverified.

Deployment and remote CI evidence will be appended after actual results are available.

## Observed hosted foundation checks

- GitHub draft PR: https://github.com/Doublezippin44/Plutus-AI2/pull/2
- Commit `6c3f1fad87ab4270597b2a05c77e6541635d6e1e`: both GitHub Actions jobs (`api`, `web`) completed successfully in run https://github.com/Doublezippin44/Plutus-AI2/actions/runs/43758003677.
- Backend Vercel preview `dpl_GMifbxWvXHmC3hFPgEj4m6q3GAME` reached READY. GET https://plutus-ai-v2-dw4nj7cbw-pirate-apollo.vercel.app/api/v1/health returned HTTP 200 with `database_ready:false`, `environment:production`, `public_launch_ready:false`.
- Frontend preview `dpl_GPxMPepCBUAMh1GLbfhKoKPJhEBg` reached READY. A further deployment applies the configured API proxy origin.
- Initial Alembic migration successfully applied to a temporary SQLite database. This is not proof of a PostgreSQL migration.
- Source publication used the connected GitHub API because shell Git push lacked a credential. No credentials were copied into files.

## Final preview verification

Application commit: `6518a8d7e4fe9a1bc8d4561cfc8337270efd380c`.

- Both CI runs on this commit succeeded, including https://github.com/Doublezippin44/Plutus-AI2/actions/runs/43758236953.
- Frontend: https://plutus-ai-v2-git-feat-plutus-v2-foundation-pirate-apollo.vercel.app/
- Backend: https://plutus-ai-v2-api-git-feat-plutus-v2-foundation-pirate-apollo.vercel.app
- Frontend `/api/v1/health` proxy returned HTTP 200 with `database_ready:false` and `public_launch_ready:false`.
- Backend `/api/v1/capabilities` returned HTTP 200 with auth, market data, AI, forecasts, payments and live trading all false.
- Backend `/api/v1/accounts/paper` returned HTTP 503, `Database is not configured`, as intended.
- Hosted browser inspection verified dashboard rendering, Watchlist navigation and Connections navigation. After the configured deployment loaded, Connections displayed `Application API: Reachable · production` and `Authentication & database: Configuration required`.
- Browser registration/trading end-to-end remains blocked by database provisioning. Mobile browser interaction has not been tested. No public-ready claim is made.
- Vercel projects: `plutus-ai-v2` and `plutus-ai-v2-api`, in team `Pirate Apollo`; this is preview infrastructure. FastAPI is temporarily hosted on Vercel, not Render. Long-running jobs/Redis/monitoring are not provisioned.
