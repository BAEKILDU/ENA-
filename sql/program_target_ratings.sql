-- 관리자 목표 시청률·화제성·매출 → Supabase
-- SQL Editor에서 실행 후 앱에서 저장하면 자동 upsert 됩니다.

create table if not exists public.program_target_ratings (
  id                       bigserial primary key,
  program_name             text        not null unique,
  category                 text,
  target_rating            numeric(12, 6),
  target_buzz              numeric(12, 2),
  target_revenue_million   numeric(14, 2),
  note                     text,
  updated_at               timestamptz not null default now()
);

create index if not exists idx_program_target_ratings_category
  on public.program_target_ratings (category);


alter table public.program_target_ratings disable row level security;

grant select, insert, update, delete
  on public.program_target_ratings
  to anon, authenticated;

grant usage, select
  on sequence public.program_target_ratings_id_seq
  to anon, authenticated;
