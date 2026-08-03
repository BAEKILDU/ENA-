-- 오리지널 콘텐츠 관리 요약 → Supabase
-- sql/revenue_records.sql 과 함께 실행하세요.

create table if not exists public.original_programs (
  id                    bigserial primary key,
  report_date           date        not null,
  category              text        not null,  -- 드라마 | 예능
  program_name          text        not null,
  episodes              integer,
  rating_target_p2049   numeric(12, 6),
  rating_household      numeric(12, 6),
  capex_million         numeric(14, 2),
  channel               text,
  note                  text,
  source_file           text,
  created_at            timestamptz not null default now()
);

create index if not exists idx_original_programs_date
  on public.original_programs (report_date);

create index if not exists idx_original_programs_name
  on public.original_programs (program_name);

create index if not exists idx_original_programs_category
  on public.original_programs (category);

alter table public.original_programs disable row level security;

grant select, insert, update, delete
  on public.original_programs
  to anon, authenticated;

grant usage, select
  on sequence public.original_programs_id_seq
  to anon, authenticated;
