-- 매출 실적 Excel → Supabase 스키마
-- Supabase SQL Editor에서 실행하세요.

create table if not exists public.revenue_records (
  id               bigserial primary key,
  report_date      date        not null,
  program_name     text        not null,
  channel          text,
  category         text,                 -- 광고 / MD / 팝업 등
  revenue_million  numeric(14, 2),       -- 매출(백만원)
  note             text,
  source_file      text,
  created_at       timestamptz not null default now()
);

create index if not exists idx_revenue_records_date
  on public.revenue_records (report_date);

create index if not exists idx_revenue_records_program
  on public.revenue_records (program_name);

alter table public.revenue_records disable row level security;

grant select, insert, update, delete
  on public.revenue_records
  to anon, authenticated;

grant usage, select
  on sequence public.revenue_records_id_seq
  to anon, authenticated;
