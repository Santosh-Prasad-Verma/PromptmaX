-- ============================================================
-- 001_profiles.sql
-- User profiles table — auto-created on Supabase Auth signup
-- ============================================================

-- Profiles table linked to auth.users
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

-- Add table comment for documentation
comment on table public.profiles is 'User profiles auto-created on signup. Mirrors Django UserPlan.';

-- Trigger function: auto-create profile row when a new user signs up
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

-- Attach trigger to auth.users
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
