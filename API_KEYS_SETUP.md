# Numeris API Keys Setup Guide

Copy `.env.example` to `.env`, then configure the required backend keys and Supabase project values.

Required for production:
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
- `APP_SECRET_KEY`, `ENCRYPTION_SECRET_KEY`
- `GROQ_API_KEY`, `MISTRAL_API_KEY`, `DEEPSEEK_API_KEY`
- `ALPHA_VANTAGE_KEY`, `NEWS_API_KEY`

Frontend on Vercel needs only public values:
- `VITE_API_BASE_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

Never expose `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, broker secrets, or model provider keys to the browser.
