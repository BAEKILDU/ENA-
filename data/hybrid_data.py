"""닐슨 실데이터 기반 카탈로그/경쟁 데이터 (Mock 없음)."""

from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from data import analysis_engine as engine
from data import buzz_engine
from data import nielsen as nd
from data import local_db
from data import original_content as oc

PREFERRED_TARGET = "개인2049"
ENA_CHANNELS = {"ENA", "ENA PLAY", "ENA DRAMA", "ENA STORY"}
VARIETY_SHEETS = ("ENA경쟁채널시청률", "ENA PLAY경쟁채널시청률")
MAJOR_CHANNELS = {
    "KBS1",
    "KBS2",
    "MBC",
    "SBS",
    "tvN",
    "JTBC",
    "TV CHOSUN",
    "TV조선",
    "채널A",
    "MBN",
    "ENA",
    "ENA PLAY",
    "ENA DRAMA",
    "ENA STORY",
}
DEFAULT_SLOTS = ["월 22:00", "화 22:00", "수 22:00", "목 22:30", "금 23:00", "토 21:00", "일 19:30"]


def _latest_report_date() -> str | None:
    if not nd.supabase_ready():
        return None
    try:
        dates = nd.get_report_dates()
        return dates[0] if dates else None
    except Exception:  # noqa: BLE001
        return None


def data_mode_label() -> str:
    return "닐슨 실데이터" if _latest_report_date() else "실데이터 없음"


def _weekday_ko(report_date: str) -> str:
    days = ["월", "화", "수", "목", "금", "토", "일"]
    try:
        d = date.fromisoformat(report_date)
        return days[d.weekday()]
    except ValueError:
        return "화"


def _parse_slot_hhmm(slot: str) -> str | None:
    m = re.search(r"(\d{1,2}):(\d{2})", str(slot or ""))
    if not m:
        return None
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def _start_to_hhmm(start_time: Any) -> str | None:
    if start_time is None or (isinstance(start_time, float) and pd.isna(start_time)):
        return None
    s = str(start_time).strip()
    m = re.match(r"^(\d{1,2}):(\d{2})", s)
    if not m:
        return None
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def _infer_genre(program_name: str) -> str:
    name = program_name or ""
    if any(k in name for k in ("SOLO", "서바이벌", "언더커버", "길치")):
        return "서바이벌 예능"
    if any(k in name for k in ("먹", "몇끼", "푸드", "맛집")):
        return "푸드 예능"
    if any(k in name for k in ("퀴즈", "지식")):
        return "퀴즈 예능"
    if any(k in name for k in ("드림", "김부장", "해리", "드라마")):
        return "드라마"
    if any(k in name for k in ("나혼자", "혼밥", "리얼")):
        return "리얼리티 예능"
    return "예능"


def _stable_id(prefix: str, name: str) -> str:
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{digest}"


def _metrics_from_rating(rating: float) -> dict[str, Any]:
    r = float(rating or 0)
    buzz = int(min(99, max(20, round(r * 80 + 35))))
    revenue = round(max(50.0, r * 1200 + 80), 1)
    target_rating = round(max(0.05, r * 0.85), 3)
    history = [round(max(0, r * f), 3) for f in (0.7, 0.8, 0.85, 0.9, 0.95, 0.98, 1.0, 1.0)]
    trend = "상승" if r >= 0.2 else ("유지" if r >= 0.05 else "하락")
    return {
        "rating": round(r, 3),
        "buzz_index": buzz,
        "revenue_million": revenue,
        "trend": trend,
        "rating_history": history,
        "target_rating": target_rating,
        "target_buzz": max(30, buzz - 8),
        "target_revenue_million": round(max(40.0, float(revenue) * 0.85), 1),
    }


def _nielsen_competition_df(report_date: str) -> pd.DataFrame:
    df = nd.get_competition_ratings(report_date)
    if df.empty:
        return df
    return df[
        (df["sheet_name"].isin(VARIETY_SHEETS))
        & (df["target"] == PREFERRED_TARGET)
        & (~df["is_daily_total"].fillna(False))
    ].copy()


def build_nielsen_shows(report_date: str | None = None) -> list[dict]:
    report_date = report_date or _latest_report_date()
    if not report_date:
        return []

    try:
        comp = _nielsen_competition_df(report_date)
    except Exception:  # noqa: BLE001
        return []

    if comp.empty:
        return []

    ena = comp[comp["channel_name"].isin({"ENA", "ENA PLAY"})].copy()
    ena = ena.dropna(subset=["program_name", "rating"])
    ena = ena[ena["rating"] > 0]
    if ena.empty:
        return []

    idx = ena.groupby("program_name")["rating"].idxmax()
    best = ena.loc[idx].sort_values("rating", ascending=False).head(10)

    weekday = _weekday_ko(report_date)
    revenue_map = oc.fetch_revenue_map()
    shows: list[dict] = []
    for row in best.itertuples():
        title = str(row.program_name)
        hhmm = _start_to_hhmm(row.start_time) or "22:00"
        channel = str(row.channel_name)
        metrics = _metrics_from_rating(float(row.rating))
        # 오리지널 콘텐츠 CAPEX(백만)가 있으면 매출에 반영
        real_rev = oc.match_revenue(title, revenue_map)
        if real_rev is not None:
            metrics["revenue_million"] = round(float(real_rev), 1)
            metrics["target_revenue_million"] = round(max(40.0, float(real_rev) * 0.85), 1)
            metrics["revenue_source"] = "original_capex"
        show_id = _stable_id("nls", f"{channel}:{title}")
        shows.append(
            {
                "id": show_id,
                "title": title,
                "genre": _infer_genre(title),
                "slot": f"{weekday} {hhmm}",
                "day": weekday,
                "time": hhmm,
                "status": "방송중",
                "cast": ["닐슨 실데이터"],
                "weeks_on_air": 1,
                "channel": channel,
                "data_source": "nielsen",
                "report_date": report_date,
                "start_time": str(row.start_time) if row.start_time else None,
                "share": float(row.share) if pd.notna(row.share) else None,
                **metrics,
            }
        )
    return shows


def get_original_variety_shows() -> list[dict]:
    """오리지널 예능 summary → 예능 카탈로그 보강용."""
    catalog = oc.fetch_program_catalog(category="예능")
    shows: list[dict] = []
    for item in catalog:
        rating = float(item.get("rating") or 0)
        # 목표만 있는 기획 행은 시청률 0으로 두고 target_rating만 사용
        has_actual = item.get("rating") is not None or item.get("revenue_million") is not None
        metrics = _metrics_from_rating(rating if has_actual else 0)
        rev = item.get("revenue_million")
        if rev is not None:
            metrics["revenue_million"] = round(float(rev), 1)
            metrics["target_revenue_million"] = round(max(40.0, float(rev) * 0.85), 1)
            metrics["revenue_source"] = "original_capex"
        else:
            metrics["revenue_million"] = 0
            metrics["target_revenue_million"] = 0
            metrics["revenue_source"] = "none"
        tgt = item.get("target_rating")
        if tgt is not None and not (isinstance(tgt, float) and pd.isna(tgt)):
            metrics["target_rating"] = round(float(tgt), 3)
        if not has_actual and rating == 0 and item.get("rating") is None:
            metrics["rating"] = round(float(tgt or 0), 3) if tgt is not None else 0.0
        title = str(item["program_name"])
        ep = item.get("episodes")
        try:
            weeks = int(ep) if ep is not None and not (isinstance(ep, float) and pd.isna(ep)) else 1
        except (TypeError, ValueError):
            weeks = 1
        day = item.get("day") or "-"
        time = item.get("time") or "-"
        slot = item.get("slot") or (f"{day} {time}" if day != "-" and time != "-" else "-")
        status = "방송중" if item.get("rating") or item.get("revenue_million") else "목표/기획"
        shows.append(
            {
                "id": _stable_id("org", title),
                "title": title,
                "genre": _infer_genre(title),
                "slot": slot,
                "day": day,
                "time": time,
                "status": status,
                "cast": ["오리지널 콘텐츠"],
                "weeks_on_air": weeks,
                "channel": item.get("channel") or "ENA",
                "data_source": "original_content",
                "report_date": item.get("report_date"),
                "start_time": None,
                "share": None,
                "category": "예능",
                **metrics,
            }
        )
    return shows


def get_original_drama_shows() -> list[dict]:
    """오리지널 드라마 summary."""
    catalog = oc.fetch_program_catalog(category="드라마")
    shows: list[dict] = []
    for item in catalog:
        rating = float(item.get("rating") or 0)
        metrics = _metrics_from_rating(rating)
        rev = item.get("revenue_million")
        if rev is not None:
            metrics["revenue_million"] = round(float(rev), 1)
            metrics["target_revenue_million"] = round(max(40.0, float(rev) * 0.85), 1)
            metrics["revenue_source"] = "original_capex"
        title = str(item["program_name"])
        ep = item.get("episodes")
        try:
            weeks = int(ep) if ep is not None and not (isinstance(ep, float) and pd.isna(ep)) else 1
        except (TypeError, ValueError):
            weeks = 1
        shows.append(
            {
                "id": _stable_id("orgd", title),
                "title": title,
                "genre": "드라마",
                "slot": item.get("slot") or "-",
                "day": item.get("day") or "-",
                "time": item.get("time") or "-",
                "status": "방송중",
                "cast": ["오리지널 콘텐츠"],
                "weeks_on_air": weeks,
                "channel": item.get("channel") or "ENA",
                "data_source": "original_content",
                "report_date": item.get("report_date"),
                "start_time": None,
                "share": None,
                "category": "드라마",
                **metrics,
            }
        )
    return shows


def get_content_catalog() -> list[dict]:
    """홈·성과 분석용: 예능 중심 카탈로그."""
    return get_variety_catalog()


def get_drama_comparison_catalog() -> list[dict]:
    """비교군: 드라마 콘텐츠 (예능 성과 대비 참고용)."""
    catalog = get_original_drama_shows()
    catalog = _apply_admin_target_ratings(catalog)
    catalog = _apply_buzz_scores(catalog)
    catalog = _apply_admin_exclusions(catalog)
    catalog.sort(key=lambda s: -float(s.get("rating") or 0))
    return catalog


def _apply_admin_target_ratings(shows: list[dict]) -> list[dict]:
    """관리자에서 입력한 목표 시청률·화제성·매출을 각 프로그램에 반영."""
    targets = local_db.load_admin_targets_map()
    if not targets or not shows:
        return shows
    for show in shows:
        matched = local_db.match_admin_targets(str(show.get("title") or ""), targets)
        if not matched:
            continue
        if matched.get("target_rating") is not None:
            show["target_rating"] = round(float(matched["target_rating"]), 3)
        if matched.get("target_buzz") is not None:
            show["target_buzz"] = int(round(float(matched["target_buzz"])))
        if matched.get("target_revenue_million") is not None:
            show["target_revenue_million"] = round(float(matched["target_revenue_million"]), 1)
    return shows


def _apply_buzz_scores(shows: list[dict]) -> list[dict]:
    """네이버·굿데이터·기사량·커뮤니티 종합 화제성 점수 반영."""
    if not shows:
        return shows
    inputs_map = local_db.load_buzz_inputs_map()
    for show in shows:
        title = str(show.get("title") or "")
        inp = buzz_engine.match_buzz_inputs(title, inputs_map) or {}
        gooddata = inp.get("gooddata_index")
        if gooddata is None:
            gooddata = local_db.lookup_fundex_buzz_share(title)
        result = buzz_engine.compute_buzz_score(
            naver_index=inp.get("naver_index"),
            gooddata_index=gooddata,
            article_count=inp.get("article_count"),
            community_score=inp.get("community_score"),
            rating=show.get("rating"),
        )
        show["buzz_index"] = int(result["buzz_index"])
        show["buzz_breakdown"] = result
        if show.get("target_buzz") is None:
            show["target_buzz"] = max(30, int(result["buzz_index"]) - 8)
    return shows


def _apply_admin_exclusions(shows: list[dict]) -> list[dict]:
    """관리자에서 제외한 타이틀을 카탈로그에서 제거."""
    excluded = local_db.list_excluded_titles()
    if not excluded or not shows:
        return shows
    return [
        s
        for s in shows
        if not local_db.is_title_excluded(str(s.get("title") or ""), excluded)
    ]


def get_variety_catalog() -> list[dict]:
    nielsen = build_nielsen_shows()
    original = get_original_variety_shows()
    # 닐슨 우선, 없는 타이틀만 오리지널로 보강
    by_key: dict[str, dict] = {}
    for s in original + nielsen:
        key = str(s.get("title") or "").replace(" ", "").upper()
        if not key:
            continue
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = s
            continue
        # nielsen 이 있으면 시청률 유지 + CAPEX 매출 병합
        if s.get("data_source") == "nielsen":
            if existing.get("revenue_source") == "original_capex":
                s = {**s, "revenue_million": existing["revenue_million"],
                     "target_revenue_million": existing["target_revenue_million"],
                     "revenue_source": "original_capex"}
            by_key[key] = s
        elif existing.get("data_source") != "nielsen" and s.get("revenue_source") == "original_capex":
            existing["revenue_million"] = s["revenue_million"]
            existing["target_revenue_million"] = s["target_revenue_million"]
            existing["revenue_source"] = "original_capex"
    catalog = list(by_key.values())
    catalog = _apply_admin_target_ratings(catalog)
    catalog = _apply_buzz_scores(catalog)
    catalog = _apply_admin_exclusions(catalog)
    catalog.sort(key=lambda s: -float(s.get("rating") or 0))
    return catalog


def get_buzz_breakdown(title: str, rating: float | None = None) -> dict[str, Any]:
    """타이틀별 화제성 세부 산정 내역."""
    inputs_map = local_db.load_buzz_inputs_map()
    inp = buzz_engine.match_buzz_inputs(title, inputs_map) or {}
    gooddata = inp.get("gooddata_index")
    if gooddata is None:
        gooddata = local_db.lookup_fundex_buzz_share(title)
    return buzz_engine.compute_buzz_score(
        naver_index=inp.get("naver_index"),
        gooddata_index=gooddata,
        article_count=inp.get("article_count"),
        community_score=inp.get("community_score"),
        rating=rating,
    )


def get_ena_variety_df() -> pd.DataFrame:
    catalog = get_variety_catalog()
    if not catalog:
        return pd.DataFrame(
            columns=[
                "id",
                "title",
                "genre",
                "slot",
                "day",
                "time",
                "status",
                "cast",
                "weeks_on_air",
                "channel",
                "data_source",
                "report_date",
                "rating",
                "buzz_index",
                "revenue_million",
                "trend",
                "rating_history",
                "target_rating",
                "target_buzz",
                "target_revenue_million",
            ]
        )
    return pd.DataFrame(catalog)


def _start_to_minutes(start_time: Any) -> int | None:
    hhmm = _start_to_hhmm(start_time)
    if not hhmm:
        return None
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _titles_match(a: str, b: str) -> bool:
    def _norm(s: str) -> str:
        t = re.sub(r"<[^>]+>", "", str(s or ""))
        t = re.sub(r"\s+", "", t).lower()
        # 한글/영문 표기 통일 (나는 솔로 ↔ 나는SOLO)
        t = t.replace("solo", "솔로")
        return t

    x, y = _norm(a), _norm(b)
    if not x or not y:
        return False
    return x == y or x in y or y in x


def _window_rows(comp: pd.DataFrame, center_min: int, window_minutes: int = 30) -> pd.DataFrame:
    mins = comp["start_time"].map(_start_to_minutes)
    mask = mins.notna() & ((mins - center_min).abs() <= window_minutes)
    return comp.loc[mask].copy()


def _best_per_channel(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return (
        df.sort_values("rating", ascending=False)
        .drop_duplicates(subset=["channel_name"], keep="first")
        .reset_index(drop=True)
    )


def get_competition_program_options(slot: str) -> pd.DataFrame:
    """동시간대에서 선택 가능한 기준 콘텐츠(ENA 우선) 목록."""
    empty = pd.DataFrame(columns=["channel", "title", "rating", "start_time"])
    hhmm = _parse_slot_hhmm(slot)
    report_date = _latest_report_date()
    if not hhmm or not report_date:
        return empty
    try:
        comp = _nielsen_competition_df(report_date)
    except Exception:  # noqa: BLE001
        return empty
    if comp.empty:
        return empty

    center = _start_to_minutes(hhmm)
    if center is None:
        return empty
    window = _window_rows(comp, center, 30)
    if window.empty:
        hour = hhmm[:2]
        window = comp[comp["start_time"].astype(str).str.startswith(f"{hour}:")].copy()
    if window.empty:
        return empty

    ena = window[window["channel_name"].isin(ENA_CHANNELS)].copy()
    pool = ena if not ena.empty else window[window["channel_name"].isin(MAJOR_CHANNELS)].copy()
    if pool.empty:
        pool = window
    best = _best_per_channel(pool).sort_values("rating", ascending=False)
    rows = [
        {
            "channel": str(r.channel_name),
            "title": str(r.program_name or "-"),
            "rating": round(float(r.rating or 0), 3),
            "start_time": str(r.start_time) if r.start_time else None,
        }
        for r in best.itertuples()
    ]
    return pd.DataFrame(rows)


def get_competition_data(slot: str, selected_title: str | None = None) -> pd.DataFrame:
    """선택된 기준 콘텐츠(좌측) + 주요채널 동시간대 상위 7개 경쟁 콘텐츠."""
    cols = ["channel", "title", "is_ena", "is_selected", "rating", "data_source"]
    hhmm = _parse_slot_hhmm(slot)
    report_date = _latest_report_date()
    if not hhmm or not report_date:
        return pd.DataFrame(columns=cols)

    try:
        comp = _nielsen_competition_df(report_date)
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=cols)
    if comp.empty:
        return pd.DataFrame(columns=cols)

    center = _start_to_minutes(hhmm)
    if center is None:
        return pd.DataFrame(columns=cols)

    window = _window_rows(comp, center, 30)
    if window.empty:
        hour = hhmm[:2]
        window = comp[comp["start_time"].astype(str).str.startswith(f"{hour}:")].copy()
    if window.empty:
        return pd.DataFrame(columns=cols)

    baseline_row = None
    if selected_title:
        title_hits = window[
            window["program_name"].astype(str).map(lambda t: _titles_match(t, selected_title))
        ]
        if not title_hits.empty:
            ena_hits = title_hits[title_hits["channel_name"].isin(ENA_CHANNELS)]
            baseline_row = (ena_hits if not ena_hits.empty else title_hits).sort_values(
                "rating", ascending=False
            ).iloc[0]

    if baseline_row is None:
        ena_pool = window[window["channel_name"].isin(ENA_CHANNELS)]
        if not ena_pool.empty:
            baseline_row = ena_pool.sort_values("rating", ascending=False).iloc[0]
        else:
            major_pool = window[window["channel_name"].isin(MAJOR_CHANNELS)]
            pool = major_pool if not major_pool.empty else window
            baseline_row = pool.sort_values("rating", ascending=False).iloc[0]

    base_min = _start_to_minutes(baseline_row["start_time"]) or center
    rival_window = _window_rows(comp, base_min, 30)
    if rival_window.empty:
        rival_window = window

    majors = rival_window[rival_window["channel_name"].isin(MAJOR_CHANNELS)].copy()
    if majors.empty:
        majors = rival_window.copy()

    base_ch = str(baseline_row["channel_name"])
    base_title = str(baseline_row.get("program_name") or "-")
    rivals = majors[
        ~(
            (majors["channel_name"].astype(str) == base_ch)
            & majors["program_name"].astype(str).map(lambda t: _titles_match(t, base_title))
        )
    ]
    rivals_best = _best_per_channel(rivals).sort_values("rating", ascending=False).head(7)

    def _row(r: Any, *, selected: bool) -> dict:
        ch = str(r["channel_name"] if isinstance(r, pd.Series) else r.channel_name)
        title = str(
            (r.get("program_name") if isinstance(r, pd.Series) else r.program_name) or "-"
        )
        rating = float(r["rating"] if isinstance(r, pd.Series) else r.rating or 0)
        return {
            "channel": ch,
            "title": title,
            "is_ena": ch in ENA_CHANNELS,
            "is_selected": selected,
            "rating": round(rating, 3),
            "data_source": "nielsen",
        }

    rows = [_row(baseline_row, selected=True)]
    for r in rivals_best.itertuples():
        rows.append(_row(r, selected=False))
    return pd.DataFrame(rows, columns=cols)


def get_top_bottom_groups() -> tuple[list[dict], list[dict]]:
    df = get_ena_variety_df()
    if df.empty:
        return [], []
    df = df.copy()
    df["value_score"] = df["rating"] * 30 + df["buzz_index"] * 0.7
    df = df.sort_values("value_score", ascending=False)
    return df.head(2).to_dict("records"), df.tail(2).to_dict("records")


def get_weekly_summary() -> dict:
    df = get_ena_variety_df()
    if df.empty:
        return {
            "top_title": "-",
            "top_rating": 0.0,
            "rising_count": 0,
            "avg_rating": 0.0,
            "total_revenue": 0.0,
            "nielsen_count": 0,
            "report_date": _latest_report_date(),
        }
    top_show = df.loc[df["rating"].idxmax()]
    rising = df[df["trend"] == "상승"]
    nielsen_count = int((df["data_source"] == "nielsen").sum()) if "data_source" in df.columns else len(df)
    return {
        "top_title": top_show["title"],
        "top_rating": round(float(top_show["rating"]), 3),
        "rising_count": int(len(rising)),
        "avg_rating": round(float(df["rating"].mean()), 3),
        "total_revenue": round(float(df["revenue_million"].sum()), 1),
        "nielsen_count": nielsen_count,
        "report_date": _latest_report_date(),
    }


def get_goal_vs_actual_df() -> pd.DataFrame:
    df = get_ena_variety_df().copy()
    if df.empty:
        return df
    df["rating_achv"] = (df["rating"] / df["target_rating"] * 100).round(0)
    df["buzz_achv"] = (df["buzz_index"] / df["target_buzz"] * 100).round(0)
    df["revenue_achv"] = (df["revenue_million"] / df["target_revenue_million"] * 100).round(0)
    df["overall_achv"] = ((df["rating_achv"] + df["buzz_achv"] + df["revenue_achv"]) / 3).round(0)
    df["goal_status"] = df["overall_achv"].apply(
        lambda x: "목표 달성" if x >= 100 else ("근접" if x >= 85 else "미달")
    )
    return df.sort_values("overall_achv", ascending=False)


def get_goal_summary() -> dict:
    df = get_goal_vs_actual_df()
    if df.empty:
        return {
            "avg_achv": 0.0,
            "achieved_count": 0,
            "total_count": 0,
            "avg_rating_achv": 0.0,
            "avg_revenue_achv": 0.0,
            "top_title": "-",
            "top_achv": 0.0,
            "bottom_title": "-",
            "bottom_achv": 0.0,
        }
    achieved = df[df["goal_status"] == "목표 달성"]
    return {
        "avg_achv": int(round(float(df["overall_achv"].mean()))),
        "achieved_count": int(len(achieved)),
        "total_count": int(len(df)),
        "avg_rating_achv": int(round(float(df["rating_achv"].mean()))),
        "avg_revenue_achv": int(round(float(df["revenue_achv"].mean()))),
        "top_title": df.iloc[0]["title"],
        "top_achv": int(round(float(df.iloc[0]["overall_achv"]))),
        "bottom_title": df.iloc[-1]["title"],
        "bottom_achv": int(round(float(df.iloc[-1]["overall_achv"]))),
    }


def _program_daily_ratings(title: str) -> pd.DataFrame:
    """Supabase(로컬) 닐슨 경쟁표에서 프로그램별 일자 시청률(일별 최고)."""
    empty = pd.DataFrame(columns=["report_date", "rating"])
    try:
        raw = nd.get_all_competition_ratings()
    except Exception:  # noqa: BLE001
        return empty
    if raw.empty:
        return empty

    mask = (
        raw["sheet_name"].isin(VARIETY_SHEETS)
        & (raw["target"] == PREFERRED_TARGET)
        & (~raw["is_daily_total"].fillna(False))
    )
    comp = raw.loc[mask].copy()
    if comp.empty:
        return empty

    hits = comp[comp["program_name"].astype(str).map(lambda t: _titles_match(t, title))]
    if hits.empty:
        return empty

    ena = hits[hits["channel_name"].isin(ENA_CHANNELS)]
    pool = ena if not ena.empty else hits
    daily = (
        pool.groupby("report_date", as_index=False)["rating"]
        .max()
        .sort_values("report_date")
        .reset_index(drop=True)
    )
    daily["rating"] = daily["rating"].map(lambda v: round(float(v or 0), 3))
    return daily


def get_trend_data(show_id: str, period: str = "week") -> pd.DataFrame:
    """콘텐츠별 주/월/연 시청률 트렌드 (닐슨 리포트일 실데이터 집계)."""
    cols = ["period", "rating", "title", "avg_rating", "period_type", "report_dates"]
    catalog = {s["id"]: s for s in get_variety_catalog()}
    show = catalog.get(show_id)
    if not show:
        return pd.DataFrame(columns=cols)

    title = str(show["title"])
    daily = _program_daily_ratings(title)
    if daily.empty:
        # 카탈로그에만 있는 콘텐츠: 단일 실적 포인트
        rating = round(float(show.get("rating") or 0), 3)
        label = {"week": "현재", "month": "현재", "year": "현재"}.get(period, "현재")
        return pd.DataFrame(
            [
                {
                    "period": label,
                    "rating": rating,
                    "title": title,
                    "avg_rating": rating,
                    "period_type": period,
                    "report_dates": 1,
                }
            ]
        )

    frame = daily.copy()
    frame["dt"] = pd.to_datetime(frame["report_date"], errors="coerce")
    frame = frame.dropna(subset=["dt"])
    if frame.empty:
        return pd.DataFrame(columns=cols)

    overall_avg = round(float(frame["rating"].mean()), 3)

    if period == "week":
        # 업로드된 닐슨 리포트일 = 주차 포인트 (시간순 1주, 2주, …)
        ordered = frame.sort_values("dt").reset_index(drop=True)
        labels = [
            f"{i + 1}주({d.strftime('%m/%d')})"
            for i, d in enumerate(ordered["dt"].tolist())
        ]
        values = [round(float(v), 3) for v in ordered["rating"].tolist()]
        counts = [1] * len(ordered)
    elif period == "month":
        frame["bucket"] = frame["dt"].dt.strftime("%Y-%m")
        frame["label"] = frame["dt"].dt.month.astype(int).astype(str) + "월"
        grouped = (
            frame.groupby(["bucket", "label"], as_index=False)
            .agg(rating=("rating", "mean"), report_dates=("report_date", "nunique"))
            .sort_values("bucket")
        )
        grouped["rating"] = grouped["rating"].map(lambda v: round(float(v), 3))
        labels = grouped["label"].tolist()
        values = grouped["rating"].tolist()
        counts = grouped["report_dates"].tolist()
    else:
        frame["bucket"] = frame["dt"].dt.strftime("%Y")
        frame["label"] = frame["dt"].dt.year.astype(int).astype(str) + "년"
        grouped = (
            frame.groupby(["bucket", "label"], as_index=False)
            .agg(rating=("rating", "mean"), report_dates=("report_date", "nunique"))
            .sort_values("bucket")
        )
        grouped["rating"] = grouped["rating"].map(lambda v: round(float(v), 3))
        labels = grouped["label"].tolist()
        values = grouped["rating"].tolist()
        counts = grouped["report_dates"].tolist()

    return pd.DataFrame(
        {
            "period": labels,
            "rating": values,
            "title": title,
            "avg_rating": overall_avg,
            "period_type": period,
            "report_dates": counts,
        }
    )


def nielsen_slot_options() -> list[str]:
    slots = list(DEFAULT_SLOTS)
    report_date = _latest_report_date()
    if not report_date:
        return slots
    try:
        shows = build_nielsen_shows(report_date)
    except Exception:  # noqa: BLE001
        return slots
    for s in shows:
        slot = s.get("slot")
        if slot and slot not in slots:
            slots.append(slot)
    return slots


def analyze_new_proposal(title: str, genre: str, slot: str, cast: str) -> dict:
    cast_list = [c.strip() for c in cast.split(",") if c.strip()] or ["미정"]
    cast_score = min(
        10,
        max(3, len([c for c in cast_list if c != "미정"]) * 2 + 3),
    )

    slot_competition = get_competition_data(slot)
    if slot_competition.empty or "rating" not in slot_competition.columns:
        avg_comp_rating = 0.0
        competition_records = []
    else:
        avg_comp_rating = float(slot_competition["rating"].mean())
        competition_records = slot_competition.to_dict("records")

    nielsen_rows = [r for r in competition_records if r.get("data_source") == "nielsen"]
    competition_score = max(1, min(10, int(round(10 - avg_comp_rating * 1.5))))
    if nielsen_rows:
        avg_n = float(np.mean([r["rating"] for r in nielsen_rows]))
        competition_score = max(1, min(10, int(round(10 - avg_n * 8))))

    live = get_variety_catalog()
    similar = [s for s in live if genre.split()[0] in s.get("genre", "")]
    format_score = 6
    if similar:
        avg_sim = float(np.mean([s.get("avg_rating", s.get("rating", 0.2)) for s in similar]))
        format_score = min(10, int(round(avg_sim * 3 if avg_sim >= 1 else avg_sim * 12)))

    scores, score_details = engine._build_score_details(cast_score, competition_score, format_score)
    overall = int(round(float(np.mean(list(scores.values())))))
    logline = engine._build_logline(title, genre, cast_list)
    swot = engine._build_swot_analysis(
        title, genre, slot, cast_list, scores, overall, competition_records, logline
    )

    if nielsen_rows:
        top_rival = max(nielsen_rows, key=lambda r: r.get("rating", 0))
        swot["neutral"] = list(swot.get("neutral") or [])
        swot["neutral"].insert(
            0,
            f"닐슨 실데이터 기준 동시간대 경쟁 {len(nielsen_rows)}편 "
            f"(최고 {top_rival.get('channel')} '{top_rival.get('title')}' "
            f"{float(top_rival.get('rating') or 0):.3f}%)",
        )
        report_date = _latest_report_date()
        if report_date:
            swot["intent_summary"] = (
                f"{swot['intent_summary']} (경쟁 분석 기준일: 닐슨 {report_date})"
            )

    return {
        "title": title,
        "genre": genre,
        "slot": slot,
        "cast": cast_list,
        "scores": scores,
        "score_details": score_details,
        "overall": overall,
        "competition": competition_records,
        "similar_shows": similar[:3],
        "source": "manual",
        "data_mode": data_mode_label(),
        "overview": {
            "title": title or "미정",
            "genre": genre or "미정",
            "slot": slot or "미정",
            "channel": "ENA",
            "cast": cast_list,
            "logline": logline,
        },
        "swot": swot,
        "summary": {
            "intent": swot["intent_summary"],
            "one_liner": swot["one_liner"],
            "overall": overall,
            "key_strength": swot["key_strength"],
            "key_risk": swot["key_risk"],
        },
        "kpi": {
            "overall": overall,
            "required_cast": max(2, len([c for c in cast_list if c != "미정"])),
            "best_slot": slot or "미정",
            "competitor_count": max(len(competition_records), len(similar[:3]), 1),
        },
        "final_conclusion": swot["final_conclusion"],
    }


def analyze_uploaded_proposal(filename: str, file_bytes: bytes | None = None) -> dict:
    parsed = engine.parse_uploaded_proposal(filename, file_bytes)
    result = analyze_new_proposal(
        parsed["title"],
        parsed["genre"] if parsed["genre"] != "미정" else "리얼리티 예능",
        parsed["slot"] if parsed["slot"] != "미정" else "수 22:00",
        parsed["cast"],
    )
    result["source"] = "upload"
    result["source_file"] = parsed["source_file"]
    result["extraction"] = parsed.get("extraction", {})

    overview = result.get("overview") or {}
    overview["title"] = parsed["title"]
    overview["genre"] = parsed["genre"]
    overview["slot"] = parsed["slot"]
    overview["channel"] = parsed.get("channel") or overview.get("channel") or "ENA"
    overview["cast"] = [c.strip() for c in str(parsed["cast"]).split(",") if c.strip()] or ["미정"]
    if parsed.get("logline") and parsed["logline"] != "미정":
        overview["logline"] = parsed["logline"]
    result["overview"] = overview
    result["title"] = parsed["title"]
    result["genre"] = overview["genre"]
    result["slot"] = overview["slot"]
    result["cast"] = overview["cast"]

    if parsed.get("intent"):
        result.setdefault("summary", {})
        result["summary"]["intent"] = parsed["intent"]
        if result.get("swot") is not None:
            result["swot"]["intent_summary"] = parsed["intent"]

    return result
