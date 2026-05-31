-- ============================================================
-- 005_indexes.sql
-- Performance indexes + auto-update updated_at trigger
-- ============================================================

-- ── Indexes ─────────────────────────────────────────────────

-- Prompt history
create index if not exists idx_prompt_history_user
  on public.prompt_history(user_id);
create index if not exists idx_prompt_history_created
  on public.prompt_history(created_at desc);
create index if not exists idx_prompt_history_intent_domain
  on public.prompt_history(detected_intent, detected_domain);
create index if not exists idx_prompt_history_level
  on public.prompt_history(enhancement_level);
create index if not exists idx_prompt_history_session
  on public.prompt_history(session_id)
  where session_id != '';

-- Prompt projects
create index if not exists idx_prompt_projects_user
  on public.prompt_projects(user_id);
create index if not exists idx_prompt_projects_updated
  on public.prompt_projects(updated_at desc);

-- Prompt assets
create index if not exists idx_prompt_assets_user
  on public.prompt_assets(user_id);
create index if not exists idx_prompt_assets_project
  on public.prompt_assets(project_id);
create index if not exists idx_prompt_assets_public
  on public.prompt_assets(is_public)
  where is_public = true;

-- Prompt versions
create index if not exists idx_prompt_versions_asset
  on public.prompt_versions(asset_id);
create index if not exists idx_prompt_versions_asset_number
  on public.prompt_versions(asset_id, version_number desc);

-- ── Auto-update updated_at trigger ──────────────────────────

create or replace function public.update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- Apply to all tables with updated_at
drop trigger if exists set_updated_at on public.profiles;
create trigger set_updated_at
  before update on public.profiles
  for each row execute function public.update_updated_at();

drop trigger if exists set_updated_at on public.prompt_history;
create trigger set_updated_at
  before update on public.prompt_history
  for each row execute function public.update_updated_at();

drop trigger if exists set_updated_at on public.prompt_projects;
create trigger set_updated_at
  before update on public.prompt_projects
  for each row execute function public.update_updated_at();

drop trigger if exists set_updated_at on public.prompt_assets;
create trigger set_updated_at
  before update on public.prompt_assets
  for each row execute function public.update_updated_at();
