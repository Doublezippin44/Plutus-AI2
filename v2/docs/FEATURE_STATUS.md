# Feature status — 2026-11-16

| Module | Actual status | Remaining work |
|---|---|---|
| Existing repo inspection | Implemented and verified | Legacy migration plan must be executed separately |
| Next.js workspace | Build verified | Browser QA pending; only six workspace views, not all 26 requested pages |
| Local registration/login/logout | Implemented and verified through API tests | UI journey and production verification |
| Supabase authentication | Implemented but not verified | Dedicated project, credentials, email configuration, real E2E tests |
| OAuth, MFA, reset, profile and privacy controls | Incomplete | Implementation and validation |
| Database models | SQLite verified | Apply and test PostgreSQL migration, RLS advisors and least-privilege role |
| Watchlist identifiers | Implemented and verified | Multiple lists/folders and instrument catalog validation |
| Manual portfolio | Implemented and verified | Import, fees, dividends, corporate actions and performance history |
| Portfolio cost and realized P&L | Implemented and verified | Current valuation/benchmark analytics need licensed data |
| Paper scenario ledger | Implemented and verified | Not full market-session-aware engine; no limits/pending orders/slippage |
| CSV export | Implemented and API-tested | Spreadsheet-level import/export validation |
| Financial market data/search/charts | Pending vendor approval; incomplete | Choose and license provider, implement adapters and live tests |
| AI assistant and RAG | Incomplete; pending external credentials | Scoped server tools, model provider, citations, security/evaluation |
| Offline ML evaluation | Implemented and unit-tested | Licensed data and real out-of-sample evaluation; not a production forecast |
| Forecast API/intervals/registry/drift | Incomplete | Calibration, deployment pipeline and monitoring |
| Razorpay payments | Incomplete; pending external credentials | Test checkout, signatures, events, reconciliation, entitlements |
| Broker sandbox | Incomplete; pending external credentials | Adapter and sandbox app/token; full workflow tests |
| Live brokerage execution | Pending vendor and legal/compliance approval | Explicitly disabled in code |
| Alerts/news/notifications | Incomplete | Licensed sources, durable worker, retries, UI |
| Resend | Pending domain configuration | Only connected domain reports failed verification; no email was sent |
| Screener/comparison/backtesting/reports | Incomplete | Data, calculations, UI and tests |
| Billing/settings/admin/legal pages | Incomplete | Product/operator details, implementation and review |
| CI workflow | Implemented | Remote run results recorded separately |
| Production monitoring/backups/shared rate limits | Incomplete | Required before public launch |
| Deployment | See VERIFICATION.md | Do not infer service readiness from a rendered frontend |

The master brief's Definition of Done is NOT met. This release establishes the first working development slice and fail-closed production configuration.
