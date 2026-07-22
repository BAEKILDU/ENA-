-- 닐슨 채널시청률 Excel → Supabase 스키마
-- Supabase SQL Editor에서 실행하세요.

-- ─────────────────────────────────────────────────────────────
-- 1) 채널 순위 (시트: 유료방송가입가구, 개인)
-- ─────────────────────────────────────────────────────────────
create table if not exists public.nielsen_channel_rankings (
  id            bigserial primary key,
  report_date   date        not null,
  sheet_name    text        not null,  -- 유료방송가입가구 | 개인
  segment       text        not null,  -- 예: 수도권 유료방송가입가구
  rank          integer     not null,
  channel_name  text        not null,
  rating        numeric(12, 6),        -- 시청률(%)
  share         numeric(12, 6),        -- 점유율(%)
  reach         numeric(12, 6),        -- 도달율(Reach %)
  watch_time    text,                  -- 시청시간 (HH:MM:SS)
  source_file   text,
  created_at    timestamptz not null default now(),
  unique (report_date, sheet_name, segment, channel_name)
);

create index if not exists idx_nielsen_channel_rankings_date
  on public.nielsen_channel_rankings (report_date);

create index if not exists idx_nielsen_channel_rankings_channel
  on public.nielsen_channel_rankings (channel_name);


-- ─────────────────────────────────────────────────────────────
-- 2) 경쟁채널 프로그램 시청률 (시트: *경쟁채널시청률)
--    타깃별 시청률·점유율을 long format으로 저장
-- ─────────────────────────────────────────────────────────────
create table if not exists public.nielsen_competition_ratings (
  id             bigserial primary key,
  report_date    date        not null,
  sheet_name     text        not null,  -- 예: ENA경쟁채널시청률
  channel_name   text        not null,  -- 예: ENA, tvN, SBS
  start_time     text,                  -- 시작시간 (25:xx 가능 → text)
  end_time       text,                  -- 끝시간
  program_name   text,
  is_daily_total boolean     not null default false,  -- 하루전체 행
  target         text        not null,  -- 예: 개인2049, 유료방송가구
  rating         numeric(12, 6),        -- 시청률
  share          numeric(12, 6),        -- 점유율
  source_file    text,
  created_at     timestamptz not null default now()
);

create index if not exists idx_nielsen_competition_ratings_date
  on public.nielsen_competition_ratings (report_date);

create index if not exists idx_nielsen_competition_ratings_channel
  on public.nielsen_competition_ratings (report_date, channel_name);

create index if not exists idx_nielsen_competition_ratings_program
  on public.nielsen_competition_ratings (program_name);


-- ─────────────────────────────────────────────────────────────
-- 3) 타깃 상세 (시트: *타깃상세)
--    타깃×지표를 long format으로 저장
-- ─────────────────────────────────────────────────────────────
create table if not exists public.nielsen_target_details (
  id                bigserial primary key,
  report_date       date        not null,
  sheet_name        text        not null,  -- 예: ENA타깃상세
  channel_name      text        not null,  -- 예: ENA, ONCE, OLIFE
  start_time        text,
  end_time          text,
  program_name      text,
  is_daily_total    boolean     not null default false,
  target            text        not null,  -- 예: 수도권 2049, 전국 유료가구
  rating            numeric(12, 6),        -- 시청률
  share             numeric(12, 6),        -- 점유율
  reach             numeric(12, 6),        -- 도달율
  watch_time        text,                  -- 시청시간 (HH:MM:SS)
  watch_time_ratio  numeric(12, 6),        -- 시청시간비율
  source_file       text,
  created_at        timestamptz not null default now()
);

create index if not exists idx_nielsen_target_details_date
  on public.nielsen_target_details (report_date);

create index if not exists idx_nielsen_target_details_channel
  on public.nielsen_target_details (report_date, channel_name);

create index if not exists idx_nielsen_target_details_program
  on public.nielsen_target_details (program_name);


-- ─────────────────────────────────────────────────────────────
-- RLS 비활성화 + anon 키로 조회/업로드 가능하도록 권한 부여
-- (이미 RLS를 켠 적이 있으면 policy 정리 후 끕니다)
-- ─────────────────────────────────────────────────────────────
drop policy if exists "nielsen_channel_rankings_select_anon"
  on public.nielsen_channel_rankings;
drop policy if exists "nielsen_competition_ratings_select_anon"
  on public.nielsen_competition_ratings;
drop policy if exists "nielsen_target_details_select_anon"
  on public.nielsen_target_details;

alter table public.nielsen_channel_rankings disable row level security;
alter table public.nielsen_competition_ratings disable row level security;
alter table public.nielsen_target_details disable row level security;

grant select, insert, update, delete
  on public.nielsen_channel_rankings
  to anon, authenticated;

grant select, insert, update, delete
  on public.nielsen_competition_ratings
  to anon, authenticated;

grant select, insert, update, delete
  on public.nielsen_target_details
  to anon, authenticated;

grant usage, select
  on sequence public.nielsen_channel_rankings_id_seq
  to anon, authenticated;

grant usage, select
  on sequence public.nielsen_competition_ratings_id_seq
  to anon, authenticated;

grant usage, select
  on sequence public.nielsen_target_details_id_seq
  to anon, authenticated;
