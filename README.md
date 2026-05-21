# Numeris

Numeris is a production-oriented AI financial intelligence platform with a Vite/React frontend, FastAPI backend, Supabase Auth/Postgres persistence, market-data services, and agent-assisted analysis.

## Architecture

- `frontend/`: Vite React app deployed to Vercel.
- `backend/`: FastAPI API, Supabase-secured data access, market endpoints, AI agent routes, and portfolio APIs.
- `supabase/migrations/`: Numeris Postgres schema, RLS policies, and one-time legacy table migration.
- `scripts/`: setup, local startup, health, and integration checks.

## Local Development

```bash
copy .env.example .env
scripts\setup.bat
scripts\start_all.bat
```

Frontend: `http://localhost:5173`
Backend: `http://localhost:8000`
API docs: `http://localhost:8000/docs`

## Production Deployment

1. Apply `supabase/migrations/202605150001_numeris_schema.sql` to Supabase.
2. Deploy `backend/` to a Python-capable host and set backend environment variables from `.env.example`.
3. Deploy `frontend/` to Vercel and set only:
   - `VITE_API_BASE_URL`
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
4. Run frontend build checks and backend smoke checks before release.

Never expose service-role, JWT secret, broker credentials, or AI provider keys in frontend environment variables.
