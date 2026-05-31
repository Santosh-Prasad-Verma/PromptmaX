-- ============================================================
-- 003_prompt_projects.sql
-- Prompt projects, assets, and versions (Git-like versioning)
-- ============================================================

-- Projects — a collection of prompts
create table if not exists public.prompt_projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  description text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

comment on table public.prompt_projects is 'A collection of prompts managed by a user. Mirrors Django PromptProject.';

-- Assets — a single prompt idea (like a Git repository)
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

comment on table public.prompt_assets is 'A single prompt idea, like a Git repo. Mirrors Django PromptAsset.';

-- Versions — a specific version of a prompt (like a Git commit)
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

comment on table public.prompt_versions is 'A specific version of a prompt, like a Git commit. Mirrors Django PromptVersion.';
