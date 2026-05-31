-- ============================================================
-- PromptX — Full Supabase Migration (run in SQL Editor)
-- ============================================================
-- Copy-paste this entire file into the Supabase Dashboard SQL Editor
-- and click "Run" to create all tables, policies, and indexes.
--
-- Tables created:
--   1. profiles        (auto-created on signup)
--   2. prompt_history   (enhancement audit trail)
--   3. prompt_projects  (prompt collections)
--   4. prompt_assets    (individual prompts)
--   5. prompt_versions  (version history per prompt)
-- ============================================================


-- ╔══════════════════════════════════════════════════════════════╗
-- ║  001 — PROFILES                                              ║
-- ╚══════════════════════════════════════════════════════════════╝

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique not null,
  full_name text default '',
  plan text default 'free' check (plan in ('free', 'pro', 'pro_plus')),
  price_rs integer default 0,
  avatar_url text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

comment on table public.profiles is 'User profiles auto-created on signup. Mirrors Django UserPlan.';

create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', '')
  );
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();


-- ╔══════════════════════════════════════════════════════════════╗
-- ║  002 — PROMPT HISTORY                                        ║
-- ╚══════════════════════════════════════════════════════════════╝

create table if not exists public.prompt_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete set null,
  session_id text default '',
  original_prompt text not null,
  enhanced_prompt text not null,
  enhancement_level text default 'basic'
    check (enhancement_level in ('basic', 'intermediate', 'advanced', 'expert')),
  detected_intent text default '',
  detected_domain text default '',
  detected_task_type text default '',
  complexity_level text default 'medium',
  original_quality_score float default 0.0,
  enhanced_quality_score float default 0.0,
  improvement_delta float default 0.0,
  original_scores_detail jsonb default '{}'::jsonb,
  enhanced_scores_detail jsonb default '{}'::jsonb,
  validation_passed boolean default true,
  validation_issues jsonb default '[]'::jsonb,
  validation_warnings jsonb default '[]'::jsonb,
  processing_time_ms float default 0.0,
  enhancement_method text default 'rule_based',
  pipeline_stages_completed jsonb default '[]'::jsonb,
  rules_applied jsonb default '[]'::jsonb,
  user_rating integer check (user_rating is null or (user_rating >= 1 and user_rating <= 5)),
  user_feedback text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

comment on table public.prompt_history is 'Complete audit trail of all prompt enhancements.';


-- ╔══════════════════════════════════════════════════════════════╗
-- ║  003 — PROMPT PROJECTS / ASSETS / VERSIONS                   ║
-- ╚══════════════════════════════════════════════════════════════╝

create table if not exists public.prompt_projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  description text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.prompt_assets (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.prompt_projects(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  description text default '',
  is_public boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(user_id, name)
);

create table if not exists public.prompt_versions (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid references public.prompt_assets(id) on delete cascade not null,
  version_number integer not null,
  content text not null,
  commit_message text default 'Initial version',
  quality_score float default 0.0,
  history_ref uuid references public.prompt_history(id) on delete set null,
  created_at timestamptz default now(),
  unique(asset_id, version_number)
);


-- ╔══════════════════════════════════════════════════════════════╗
-- ║  004 — ROW LEVEL SECURITY                                    ║
-- ╚══════════════════════════════════════════════════════════════╝

alter table public.profiles enable row level security;
alter table public.prompt_history enable row level security;
alter table public.prompt_projects enable row level security;
alter table public.prompt_assets enable row level security;
alter table public.prompt_versions enable row level security;

-- Profiles
create policy "profiles_select_own" on public.profiles for select using (auth.uid() = id);
create policy "profiles_update_own" on public.profiles for update using (auth.uid() = id);
create policy "profiles_insert_service" on public.profiles for insert with check (auth.uid() = id);

-- Prompt History
create policy "history_select_own" on public.prompt_history for select using (auth.uid() = user_id);
create policy "history_insert_own" on public.prompt_history for insert with check (auth.uid() = user_id);
create policy "history_update_own" on public.prompt_history for update using (auth.uid() = user_id);

-- Prompt Projects
create policy "projects_select_own" on public.prompt_projects for select using (auth.uid() = user_id);
create policy "projects_insert_own" on public.prompt_projects for insert with check (auth.uid() = user_id);
create policy "projects_update_own" on public.prompt_projects for update using (auth.uid() = user_id);
create policy "projects_delete_own" on public.prompt_projects for delete using (auth.uid() = user_id);

-- Prompt Assets (own + public)
create policy "assets_select_own_or_public" on public.prompt_assets for select using (auth.uid() = user_id or is_public = true);
create policy "assets_insert_own" on public.prompt_assets for insert with check (auth.uid() = user_id);
create policy "assets_update_own" on public.prompt_assets for update using (auth.uid() = user_id);
create policy "assets_delete_own" on public.prompt_assets for delete using (auth.uid() = user_id);

-- Prompt Versions (inherit from asset)
create policy "versions_select_accessible" on public.prompt_versions for select using (
  exists (select 1 from public.prompt_assets where id = prompt_versions.asset_id and (user_id = auth.uid() or is_public = true))
);
create policy "versions_insert_own" on public.prompt_versions for insert with check (
  exists (select 1 from public.prompt_assets where id = prompt_versions.asset_id and user_id = auth.uid())
);
create policy "versions_update_own" on public.prompt_versions for update using (
  exists (select 1 from public.prompt_assets where id = prompt_versions.asset_id and user_id = auth.uid())
);
create policy "versions_delete_own" on public.prompt_versions for delete using (
  exists (select 1 from public.prompt_assets where id = prompt_versions.asset_id and user_id = auth.uid())
);


-- ╔══════════════════════════════════════════════════════════════╗
-- ║  005 — INDEXES + UPDATED_AT TRIGGER                          ║
-- ╚══════════════════════════════════════════════════════════════╝

create index if not exists idx_prompt_history_user on public.prompt_history(user_id);
create index if not exists idx_prompt_history_created on public.prompt_history(created_at desc);
create index if not exists idx_prompt_history_intent_domain on public.prompt_history(detected_intent, detected_domain);
create index if not exists idx_prompt_history_level on public.prompt_history(enhancement_level);
create index if not exists idx_prompt_history_session on public.prompt_history(session_id) where session_id != '';
create index if not exists idx_prompt_projects_user on public.prompt_projects(user_id);
create index if not exists idx_prompt_projects_updated on public.prompt_projects(updated_at desc);
create index if not exists idx_prompt_assets_user on public.prompt_assets(user_id);
create index if not exists idx_prompt_assets_project on public.prompt_assets(project_id);
create index if not exists idx_prompt_assets_public on public.prompt_assets(is_public) where is_public = true;
create index if not exists idx_prompt_versions_asset on public.prompt_versions(asset_id);
create index if not exists idx_prompt_versions_asset_number on public.prompt_versions(asset_id, version_number desc);

-- Auto-update updated_at on row modification
create or replace function public.update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists set_updated_at on public.profiles;
create trigger set_updated_at before update on public.profiles
  for each row execute function public.update_updated_at();

drop trigger if exists set_updated_at on public.prompt_history;
create trigger set_updated_at before update on public.prompt_history
  for each row execute function public.update_updated_at();

drop trigger if exists set_updated_at on public.prompt_projects;
create trigger set_updated_at before update on public.prompt_projects
  for each row execute function public.update_updated_at();

drop trigger if exists set_updated_at on public.prompt_assets;
create trigger set_updated_at before update on public.prompt_assets
  for each row execute function public.update_updated_at();


-- ✅ Migration complete!
-- Tables: profiles, prompt_history, prompt_projects, prompt_assets, prompt_versions
-- RLS: All tables secured — users can only access their own data
-- Indexes: Optimized for user lookups, time-based queries, and asset discovery
