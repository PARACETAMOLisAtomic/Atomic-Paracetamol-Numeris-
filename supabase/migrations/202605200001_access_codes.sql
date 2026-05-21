-- Private Access Code and Feature Flag Schema Migration
-- Numeris v3.0

-- 1. Create Access Codes Table
create table if not exists public.numeris_access_codes (
  code text primary key,
  is_active boolean not null default true,
  role text not null default 'standard_user' check (role in ('admin', 'beta_user', 'standard_user')),
  created_at timestamptz not null default now()
);

-- 2. Create User Access Table
create table if not exists public.numeris_user_access (
  user_id uuid primary key references auth.users(id) on delete cascade,
  code text references public.numeris_access_codes(code) on delete set null,
  role text not null default 'standard_user' check (role in ('admin', 'beta_user', 'standard_user')),
  created_at timestamptz not null default now()
);

-- 3. Create Feature Flags Table
create table if not exists public.numeris_feature_flags (
  name text primary key,
  is_enabled boolean not null default false,
  description text,
  created_at timestamptz not null default now()
);

-- 4. Enable RLS
alter table public.numeris_access_codes enable row level security;
alter table public.numeris_user_access enable row level security;
alter table public.numeris_feature_flags enable row level security;

-- 5. Row Level Security Policies
-- Users can only read their own user access records
drop policy if exists "numeris_user_access_owner_select" on public.numeris_user_access;
create policy "numeris_user_access_owner_select"
on public.numeris_user_access for select
using (auth.uid() = user_id);

-- Authenticated users can read feature flags
drop policy if exists "numeris_feature_flags_select" on public.numeris_feature_flags;
create policy "numeris_feature_flags_select"
on public.numeris_feature_flags for select
using (auth.role() = 'authenticated');

-- 6. Performance Indexes
create index if not exists idx_user_access_code on public.numeris_user_access(code);
create index if not exists idx_access_codes_active on public.numeris_access_codes(code) where is_active = true;
create index if not exists idx_analysis_history_user_symbol on public.numeris_analysis_history(user_id, symbol);
create index if not exists idx_manual_portfolio_user_symbol on public.numeris_manual_portfolio(user_id, symbol);

-- 7. Seed Initial Feature Flags
insert into public.numeris_feature_flags (name, is_enabled, description)
values
  ('portfolio_optimization', false, 'Enable advanced portfolio allocation suggestions via LLM Swarm'),
  ('voice_commands', false, 'Enable voice analysis and audio feedback synthesizers'),
  ('advanced_risk_analytics', false, 'Enable Monte Carlo VaR calculations and risk stress-testing dashboards')
on conflict (name) do nothing;
