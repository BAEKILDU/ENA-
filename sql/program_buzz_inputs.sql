-- 화제성 구성 지표 (네이버·굿데이터·기사량·커뮤니티) → Supabase
-- SQL Editor에서 실행하세요.

create table if not exists public.program_buzz_inputs (
  id                 bigserial primary key,
  program_name       text        not null unique,
  category           text,
  naver_index        numeric(14, 4),
  gooddata_index     numeric(14, 4),
  article_count      numeric(14, 2),
  community_score    numeric(14, 4),
  note               text,
  updated_at         timestamptz not null default now()
);

create index if not exists idx_program_buzz_inputs_category
  on public.program_buzz_inputs (category);

alter table public.program_buzz_inputs disable row level security;

grant select, insert, update, delete
  on public.program_buzz_inputs
  to anon, authenticated;

grant usage, select
  on sequence public.program_buzz_inputs_id_seq
  to anon, authenticated;
