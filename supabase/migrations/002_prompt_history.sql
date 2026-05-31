-- ============================================================
-- 002_prompt_history.sql
-- Prompt enhancement history — mirrors Django PromptHistory
-- ============================================================

create table if not exists public.prompt_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete set null,
  session_id text default '',

  -- Prompts
  original_prompt text not null,
  enhanced_prompt text not null,
  enhancement_level text default 'basic'
    check (enhancement_level in ('basic', 'intermediate', 'advanced', 'expert')),

  -- Analysis results
  detected_intent text default '',
  detected_domain text default '',
  detected_task_type text default '',
  complexity_level text default 'medium',

  -- Quality scores
  original_quality_score float default 0.0,
  enhanced_quality_score float default 0.0,
  improvement_delta float default 0.0,

  -- Detailed scores (JSON blobs)
  original_scores_detail jsonb default '{}'::jsonb,
  enhanced_scores_detail jsonb default '{}'::jsonb,

  -- Validation
  validation_passed boolean default true,
  validation_issues jsonb default '[]'::jsonb,
  validation_warnings jsonb default '[]'::jsonb,

  -- Processing metadata
  processing_time_ms float default 0.0,
  enhancement_method text default 'rule_based',
  pipeline_stages_completed jsonb default '[]'::jsonb,
  rules_applied jsonb default '[]'::jsonb,

  -- User feedback
  user_rating integer check (user_rating is null or (user_rating >= 1 and user_rating <= 5)),
  user_feedback text default '',

  -- Timestamps
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

comment on table public.prompt_history is 'Complete audit trail of all prompt enhancements. Mirrors Django PromptHistory.';
