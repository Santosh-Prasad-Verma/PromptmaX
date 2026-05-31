-- ============================================================
-- 004_rls_policies.sql
-- Row Level Security — users can only access their own data
-- ============================================================

-- ── Enable RLS on all tables ────────────────────────────────
alter table public.profiles enable row level security;
alter table public.prompt_history enable row level security;
alter table public.prompt_projects enable row level security;
alter table public.prompt_assets enable row level security;
alter table public.prompt_versions enable row level security;

-- ── Profiles ────────────────────────────────────────────────
-- Users can read their own profile
create policy "profiles_select_own"
  on public.profiles for select
  using (auth.uid() = id);

-- Users can update their own profile
create policy "profiles_update_own"
  on public.profiles for update
  using (auth.uid() = id);

-- Insert is handled by the trigger (security definer), but allow
-- service_role writes from Django backend
create policy "profiles_insert_service"
  on public.profiles for insert
  with check (auth.uid() = id);

-- ── Prompt History ──────────────────────────────────────────
-- Users can view their own history
create policy "history_select_own"
  on public.prompt_history for select
  using (auth.uid() = user_id);

-- Users can insert their own history
create policy "history_insert_own"
  on public.prompt_history for insert
  with check (auth.uid() = user_id);

-- Users can update their own history (e.g., add rating/feedback)
create policy "history_update_own"
  on public.prompt_history for update
  using (auth.uid() = user_id);

-- ── Prompt Projects ─────────────────────────────────────────
create policy "projects_select_own"
  on public.prompt_projects for select
  using (auth.uid() = user_id);

create policy "projects_insert_own"
  on public.prompt_projects for insert
  with check (auth.uid() = user_id);

create policy "projects_update_own"
  on public.prompt_projects for update
  using (auth.uid() = user_id);

create policy "projects_delete_own"
  on public.prompt_projects for delete
  using (auth.uid() = user_id);

-- ── Prompt Assets ───────────────────────────────────────────
-- Users can view own assets + public assets from other users
create policy "assets_select_own_or_public"
  on public.prompt_assets for select
  using (auth.uid() = user_id or is_public = true);

create policy "assets_insert_own"
  on public.prompt_assets for insert
  with check (auth.uid() = user_id);

create policy "assets_update_own"
  on public.prompt_assets for update
  using (auth.uid() = user_id);

create policy "assets_delete_own"
  on public.prompt_assets for delete
  using (auth.uid() = user_id);

-- ── Prompt Versions ─────────────────────────────────────────
-- Users can view versions of their own assets or public assets
create policy "versions_select_accessible"
  on public.prompt_versions for select
  using (
    exists (
      select 1 from public.prompt_assets
      where id = prompt_versions.asset_id
        and (user_id = auth.uid() or is_public = true)
    )
  );

-- Users can create versions only on their own assets
create policy "versions_insert_own"
  on public.prompt_versions for insert
  with check (
    exists (
      select 1 from public.prompt_assets
      where id = prompt_versions.asset_id
        and user_id = auth.uid()
    )
  );

-- Users can update versions on their own assets
create policy "versions_update_own"
  on public.prompt_versions for update
  using (
    exists (
      select 1 from public.prompt_assets
      where id = prompt_versions.asset_id
        and user_id = auth.uid()
    )
  );

-- Users can delete versions on their own assets
create policy "versions_delete_own"
  on public.prompt_versions for delete
  using (
    exists (
      select 1 from public.prompt_assets
      where id = prompt_versions.asset_id
        and user_id = auth.uid()
    )
  );
