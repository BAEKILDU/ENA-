"""닐슨 채널시청률 조회 — Supabase 우선, 실패 시 로컬 SQLite."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import pandas as pd
import streamlit as st
from supabase import Client, create_client

from data import local_db
from data.supabase_upload import check_supabase_dns, supabase_reachable
from utils.config import get_supabase_anon_key, get_supabase_url

PAGE_SIZE = 1000


@lru_cache(maxsize=1)
def _client() -> Client | None:
    if not supabase_reachable():
        return None
    url = get_supabase_url()
    key = get_supabase_anon_key()
    if not url or not key:
        return None
    return create_client(url, key)


def supabase_ready() -> bool:
    """데이터가 조회 가능한 백엔드가 있으면 True (로컬 포함)."""
    local_db.init_schema()
    return True


def active_backend() -> str:
    return "supabase" if supabase_reachable() else "local"


def _fetch_all(table: str, filters: dict[str, Any] | None = None) -> list[dict]:
    client = _client()
    if client is not None:
        try:
            rows: list[dict] = []
            start = 0
            while True:
                q = client.table(table).select("*")
                if filters:
                    for col, val in filters.items():
                        if val is None:
                            continue
                        if isinstance(val, (list, tuple, set)):
                            q = q.in_(col, list(val))
                        else:
                            q = q.eq(col, val)
                resp = q.range(start, start + PAGE_SIZE - 1).execute()
                batch = resp.data or []
                rows.extend(batch)
                if len(batch) < PAGE_SIZE:
                    break
                start += PAGE_SIZE
            if rows:
                return rows
        except Exception:  # noqa: BLE001
            pass
    return local_db.fetch_all_local(table, filters)


@st.cache_data(ttl=300, show_spinner=False)
def get_report_dates() -> list[str]:
    rows = _fetch_all("nielsen_channel_rankings")
    if not rows:
        rows = _fetch_all("nielsen_competition_ratings")
    dates = sorted({r["report_date"] for r in rows if r.get("report_date")}, reverse=True)
    return dates


@st.cache_data(ttl=300, show_spinner=False)
def get_channel_rankings(report_date: str) -> pd.DataFrame:
    rows = _fetch_all("nielsen_channel_rankings", {"report_date": report_date})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for col in ("rating", "share", "reach", "rank"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def get_competition_ratings(report_date: str) -> pd.DataFrame:
    rows = _fetch_all("nielsen_competition_ratings", {"report_date": report_date})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for col in ("rating", "share"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "is_daily_total" in df.columns:
        df["is_daily_total"] = df["is_daily_total"].astype(bool)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def get_target_details(report_date: str) -> pd.DataFrame:
    rows = _fetch_all("nielsen_target_details", {"report_date": report_date})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for col in ("rating", "share", "reach", "watch_time_ratio"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "is_daily_total" in df.columns:
        df["is_daily_total"] = df["is_daily_total"].astype(bool)
    return df


def ranking_segments(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    return sorted(df["segment"].dropna().unique().tolist())


def competition_sheets(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    return sorted(df["sheet_name"].dropna().unique().tolist())


def competition_targets(df: pd.DataFrame, sheet_name: str | None = None) -> list[str]:
    if df.empty:
        return []
    subset = df if not sheet_name else df[df["sheet_name"] == sheet_name]
    return sorted(subset["target"].dropna().unique().tolist())


def top_channels(df: pd.DataFrame, segment: str, n: int = 20) -> pd.DataFrame:
    if df.empty:
        return df
    out = df[df["segment"] == segment].sort_values("rank").head(n).copy()
    return out


def channel_rank_in_segment(df: pd.DataFrame, segment: str, channel: str = "ENA") -> dict | None:
    if df.empty:
        return None
    hit = df[(df["segment"] == segment) & (df["channel_name"] == channel)]
    if hit.empty:
        return None
    row = hit.iloc[0]
    return {
        "rank": int(row["rank"]) if pd.notna(row["rank"]) else None,
        "rating": float(row["rating"]) if pd.notna(row["rating"]) else None,
        "share": float(row["share"]) if pd.notna(row["share"]) else None,
        "reach": float(row["reach"]) if pd.notna(row["reach"]) else None,
        "watch_time": row.get("watch_time"),
    }


def top_programs(
    df: pd.DataFrame,
    *,
    channel: str = "ENA",
    target: str | None = None,
    sheet_name: str | None = None,
    n: int = 10,
    exclude_daily: bool = True,
) -> pd.DataFrame:
    if df.empty:
        return df
    q = df[df["channel_name"] == channel].copy()
    if sheet_name:
        q = q[q["sheet_name"] == sheet_name]
    if target:
        q = q[q["target"] == target]
    if exclude_daily:
        q = q[~q["is_daily_total"].fillna(False)]
    q = q.dropna(subset=["program_name", "rating"])
    return q.sort_values("rating", ascending=False).head(n)


def same_slot_competitors(
    df: pd.DataFrame,
    *,
    sheet_name: str,
    target: str,
    start_time: str,
    focus_channel: str = "ENA",
) -> pd.DataFrame:
    if df.empty:
        return df
    q = df[
        (df["sheet_name"] == sheet_name)
        & (df["target"] == target)
        & (df["start_time"] == start_time)
        & (~df["is_daily_total"].fillna(False))
    ].copy()
    if q.empty:
        return q
    q = q.sort_values("rating", ascending=False)
    q["is_focus"] = q["channel_name"] == focus_channel
    return q


def target_breakdown(
    df: pd.DataFrame,
    *,
    channel: str,
    program_name: str,
    start_time: str | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df
    q = df[(df["channel_name"] == channel) & (df["program_name"] == program_name)].copy()
    if start_time:
        q = q[q["start_time"] == start_time]
    q = q[~q["is_daily_total"].fillna(False)]
    return q.sort_values("rating", ascending=False)


def connection_hint() -> str:
    ok, msg = check_supabase_dns()
    if ok:
        return "Supabase 연결 가능"
    return f"로컬 DB 사용 중 — {msg}"
