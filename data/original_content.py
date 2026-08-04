"""오리지널 콘텐츠 processed CSV / Supabase 로더."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from utils.config import get_supabase_anon_key, get_supabase_url

PROCESSED = Path(__file__).resolve().parent / "processed"


def _read_csv(name: str) -> pd.DataFrame:
    path = PROCESSED / f"{name}.csv"
    if not path.exists():
        return pd.DataFrame()
    # 손상/비텍스트 파일·인코딩 차이 방어
    raw = path.read_bytes()[:8]
    if raw.startswith(b"SCDSA") or b"\x00" in raw:
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception:  # noqa: BLE001
            break
    return pd.DataFrame()


def load_programs_summary() -> pd.DataFrame:
    return _read_csv("programs_summary")


def load_revenue_records_csv() -> pd.DataFrame:
    return _read_csv("revenue_records")


def load_capex_monthly() -> pd.DataFrame:
    return _read_csv("capex_monthly")


def load_target_ratings() -> pd.DataFrame:
    return _read_csv("target_ratings")


def load_drama_compare() -> pd.DataFrame:
    return _read_csv("drama_title_compare")


def load_variety_compare() -> pd.DataFrame:
    return _read_csv("variety_title_compare")


def load_episode_ratings_drama() -> pd.DataFrame:
    return _read_csv("episode_ratings_drama")


@lru_cache(maxsize=1)
def _supabase_client():
    url = get_supabase_url()
    key = get_supabase_anon_key()
    if not url or not key:
        return None
    from supabase import create_client

    return create_client(url, key)


def fetch_revenue_map() -> dict[str, float]:
    """프로그램명 → 매출/CAPEX(백만). Supabase 우선, CSV 폴백."""
    client = _supabase_client()
    if client is not None:
        try:
            res = (
                client.table("revenue_records")
                .select("program_name,revenue_million,report_date")
                .order("report_date", desc=True)
                .limit(500)
                .execute()
            )
            rows = res.data or []
            out: dict[str, float] = {}
            for r in rows:
                name = str(r.get("program_name") or "").strip()
                if not name or name in out:
                    continue
                val = r.get("revenue_million")
                if val is None:
                    continue
                out[name] = float(val)
            if out:
                return out
        except Exception:  # noqa: BLE001
            pass

    df = load_revenue_records_csv()
    if df.empty:
        df = load_programs_summary()
        if not df.empty and "capex_million" in df.columns:
            df = df.rename(columns={"capex_million": "revenue_million"})
    out = {}
    if df.empty:
        return out
    for _, r in df.iterrows():
        name = str(r.get("program_name") or "").strip()
        if not name or name in out:
            continue
        val = r.get("revenue_million")
        if pd.isna(val):
            continue
        out[name] = float(val)
    return out


def fetch_program_catalog(category: str | None = None) -> list[dict[str, Any]]:
    """홈/예능/드라마용 프로그램 카탈로그. CSV 우선(업로드 즉시 반영), Supabase 보조."""
    rows: list[dict] = []
    df = load_programs_summary()
    if not df.empty:
        if category:
            df = df[df["category"] == category]
        rows = df.to_dict(orient="records")

    if not rows:
        client = _supabase_client()
        if client is not None:
            try:
                q = client.table("original_programs").select("*").order("report_date", desc=True)
                if category:
                    q = q.eq("category", category)
                res = q.limit(200).execute()
                rows = res.data or []
            except Exception:  # noqa: BLE001
                rows = []

    seen: set[str] = set()
    catalog: list[dict[str, Any]] = []
    for r in rows:
        name = str(r.get("program_name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        rating = r.get("rating_target_p2049")
        capex = r.get("capex_million")
        target_rating = r.get("target_rating")
        catalog.append(
            {
                "program_name": name,
                "category": r.get("category"),
                "episodes": r.get("episodes"),
                "rating": float(rating) if rating is not None and not pd.isna(rating) else None,
                "rating_household": r.get("rating_household"),
                "target_rating": (
                    float(target_rating)
                    if target_rating is not None and not pd.isna(target_rating)
                    else None
                ),
                "revenue_million": float(capex) if capex is not None and not pd.isna(capex) else None,
                "channel": r.get("channel") or "ENA",
                "note": r.get("note"),
                "slot": r.get("slot"),
                "day": r.get("day"),
                "time": r.get("time"),
                "report_date": r.get("report_date"),
                "data_source": "original_content",
            }
        )
    return catalog


def match_revenue(program_name: str, revenue_map: dict[str, float] | None = None) -> float | None:
    """느슨한 프로그램명 매칭으로 CAPEX/매출 조회."""
    revenue_map = revenue_map if revenue_map is not None else fetch_revenue_map()
    if not program_name or not revenue_map:
        return None
    name = program_name.strip()
    if name in revenue_map:
        return revenue_map[name]
    # normalize spaces / SOLO
    norm = name.replace(" ", "").replace("나는SOLO", "나는솔로").upper()
    for k, v in revenue_map.items():
        kk = k.replace(" ", "").upper()
        if norm == kk or norm in kk or kk in norm:
            return v
    return None
