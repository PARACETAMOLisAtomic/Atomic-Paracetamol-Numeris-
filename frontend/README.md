# Numeris Frontend

Vite + React production frontend for Numeris.

Required Vercel environment variables:

```bash
VITE_API_BASE_URL=https://your-fastapi-backend.example.com
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-public-anon-key
```

Do not configure backend secrets in Vercel frontend variables.

Local commands:

```bash
npm install
npm run dev
npm run build
```
