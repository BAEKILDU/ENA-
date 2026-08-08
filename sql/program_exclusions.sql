-- 관리자 제외 타이틀 → Supabase
-- SQL Editor에서 실행 후 앱에서 저장하면 자동 upsert 됩니다.

create table if not exists public.program_exclusions (
  id            bigserial primary key,
  program_name  text        not null unique,
  note          text,
  updated_at    timestamptz not null default now()
);

create index if not exists idx_program_exclusions_name
  on public.program_exclusions (program_name);

alter table public.program_exclusions disable row level security;

grant select, insert, update, delete
  on public.program_exclusions
  to anon, authenticated;

grant usage, select
  on sequence public.program_exclusions_id_seq
  to anon, authenticated;
