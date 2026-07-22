"""닐슨 실데이터 + Mock 하이브리드 카탈로그/경쟁 데이터.

예능 분석·신규 기획은 이 모듈을 통해 실데이터와 가상 데이터를 함께 사용합니다.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from data import mock_data as mock
from data import nielsen as nd

PREFERRED_TARGET = "개인2049"
ENA_CHANNELS = {"ENA", "ENA PLAY", "ENA DRAMA", "ENA STORY"}
VARIETY_SHEETS = ("ENA경쟁채널시청률", "ENA PLAY경쟁채널시청률")


def _latest_report_date() -> str | None:
    if not nd.supabase_ready():
        return None
    try:
        dates = nd.get_report_dates()
        return dates[0] if dates else None
    except Exception:  # noqa: BLE001
        return None


def data_mode_label() -> str:
    """사이드바/캡션용."""
    return "닐슨+Mock 하이브리드" if _latest_report_date() else "Mock 데이터"


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
    revenue = int(max(50, round(r * 1200 + 80)))
    target_rating = round(max(0.05, r * 0.85), 4)
    history = [round(max(0, r * f), 4) for f in (0.7, 0.8, 0.85, 0.9, 0.95, 0.98, 1.0, 1.0)]
    trend = "상승" if r >= 0.2 else ("유지" if r >= 0.05 else "하락")
    return {
        "rating": round(r, 4),
        "buzz_index": buzz,
        "revenue_million": revenue,
        "trend": trend,
        "rating_history": history,
        "target_rating": target_rating,
        "target_buzz": max(30, buzz - 8),
        "target_revenue_million": max(40, int(revenue * 0.85)),
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
    """닐슨 ENA/ENA PLAY 프로그램을 예능 카탈로그 행으로 변환."""
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

    # 프로그램별 최고 시청률 회차
    idx = ena.groupby("program_name")["rating"].idxmax()
    best = ena.loc[idx].sort_values("rating", ascending=False).head(10)

    weekday = _weekday_ko(report_date)
    shows: list[dict] = []
    for row in best.itertuples():
        title = str(row.program_name)
        hhmm = _start_to_hhmm(row.start_time) or "22:00"
        channel = str(row.channel_name)
        metrics = _metrics_from_rating(float(row.rating))
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


def build_mock_shows() -> list[dict]:
    rows = []
    for show in mock.ENA_VARIETY_SHOWS:
        metrics = mock.PERFORMANCE_METRICS[show["id"]]
        rows.append(
            {
                **show,
                **metrics,
                "channel": "ENA",
                "data_source": "mock",
                "report_date": None,
                "start_time": None,
                "share": None,
            }
        )
    return rows


def get_variety_catalog() -> list[dict]:
    """Mock + 닐슨 프로그램 카탈로그 (실데이터 우선 정렬)."""
    nielsen_shows = build_nielsen_shows()
    mock_shows = build_mock_shows()
    # 동일 제목이면 닐슨 우선
    by_title = {s["title"]: s for s in mock_shows}
    for s in nielsen_shows:
        by_title[s["title"]] = s
    catalog = list(by_title.values())
    catalog.sort(
        key=lambda s: (
            0 if s.get("data_source") == "nielsen" else 1,
            -float(s.get("rating") or 0),
        )
    )
    return catalog


def get_ena_variety_df() -> pd.DataFrame:
    return pd.DataFrame(get_variety_catalog())


def get_competition_data(slot: str) -> pd.DataFrame:
    """동시간대 경쟁: Mock 슬롯 + 닐슨 동일 시각 실데이터."""
    rows: list[dict] = []

    # Mock
    ratings_map = {
        "ENA 먹을텐데": 1.8,
        "놀뭐": 3.2,
        "한끼줍쇼": 1.5,
        "전지적 참견": 2.8,
        "ENA 술래잡기": 2.4,
        "런닝맨": 2.9,
        "놀뭐 스핀오프": 1.7,
        "ENA 글로벌 퀴즈쇼": 1.1,
        "1박2일": 4.5,
        "나 혼자 산다": 3.8,
        "ENA 캠핑클럽": 2.8,
        "놀면 뭐하니": 2.1,
        "ENA 웃음공장": 0.9,
        "동상이몽": 2.3,
        "유퀴즈": 3.5,
    }
    for s in mock.COMPETITOR_SHOWS.get(slot, []):
        rows.append(
            {
                "channel": s["channel"],
                "title": s["title"],
                "is_ena": bool(s["is_ena"]),
                "rating": float(ratings_map.get(s["title"], 1.5)),
                "data_source": "mock",
            }
        )

    # Nielsen — 시각(HH:MM) 기준
    hhmm = _parse_slot_hhmm(slot)
    report_date = _latest_report_date()
    if hhmm and report_date:
        try:
            comp = _nielsen_competition_df(report_date)
        except Exception:  # noqa: BLE001
            comp = pd.DataFrame()

        if not comp.empty:
            prefix = hhmm
            matched = comp[comp["start_time"].astype(str).str.startswith(prefix)]
            if matched.empty:
                # 같은 시(hour)로 확장 후, ENA 최고 시청 시각의 경쟁 구도로 맞춤
                hour = hhmm[:2]
                hour_rows = comp[comp["start_time"].astype(str).str.startswith(f"{hour}:")]
                if not hour_rows.empty:
                    ena_best = (
                        hour_rows[hour_rows["channel_name"].isin(ENA_CHANNELS)]
                        .sort_values("rating", ascending=False)
                        .head(1)
                    )
                    if not ena_best.empty:
                        start = ena_best.iloc[0]["start_time"]
                        matched = comp[comp["start_time"] == start]
                    else:
                        # hour 내 채널별 최고
                        matched = (
                            hour_rows.sort_values("rating", ascending=False)
                            .groupby("channel_name", as_index=False)
                            .first()
                        )

            for _, r in matched.iterrows():
                ch = str(r["channel_name"])
                title = str(r.get("program_name") or "-")
                rows.append(
                    {
                        "channel": ch,
                        "title": title,
                        "is_ena": ch in ENA_CHANNELS,
                        "rating": round(float(r["rating"] or 0), 4),
                        "data_source": "nielsen",
                    }
                )

    if not rows:
        return pd.DataFrame(columns=["channel", "title", "is_ena", "rating", "data_source"])

    df = pd.DataFrame(rows)
    # channel+title 중복 시 닐슨 우선
    df["_prio"] = df["data_source"].map({"nielsen": 0, "mock": 1}).fillna(2)
    df = (
        df.sort_values(["_prio", "rating"], ascending=[True, False])
        .drop_duplicates(subset=["channel", "title"], keep="first")
        .drop(columns=["_prio"])
        .sort_values("rating", ascending=False)
        .reset_index(drop=True)
    )
    return df


def get_top_bottom_groups() -> tuple[list[dict], list[dict]]:
    df = get_ena_variety_df()
    df["value_score"] = df["rating"] * 30 + df["buzz_index"] * 0.7
    df = df.sort_values("value_score", ascending=False)
    return df.head(2).to_dict("records"), df.tail(2).to_dict("records")


def get_weekly_summary() -> dict:
    df = get_ena_variety_df()
    top_show = df.loc[df["rating"].idxmax()]
    rising = df[df["trend"] == "상승"]
    nielsen_count = int((df["data_source"] == "nielsen").sum()) if "data_source" in df.columns else 0
    mock_count = int((df["data_source"] == "mock").sum()) if "data_source" in df.columns else len(df)
    return {
        "top_title": top_show["title"],
        "top_rating": float(top_show["rating"]),
        "rising_count": int(len(rising)),
        "avg_rating": round(float(df["rating"].mean()), 4),
        "total_revenue": float(df["revenue_million"].sum()),
        "nielsen_count": nielsen_count,
        "mock_count": mock_count,
        "report_date": _latest_report_date(),
    }


def get_goal_vs_actual_df() -> pd.DataFrame:
    df = get_ena_variety_df().copy()
    df["rating_achv"] = (df["rating"] / df["target_rating"] * 100).round(1)
    df["buzz_achv"] = (df["buzz_index"] / df["target_buzz"] * 100).round(1)
    df["revenue_achv"] = (df["revenue_million"] / df["target_revenue_million"] * 100).round(1)
    df["overall_achv"] = ((df["rating_achv"] + df["buzz_achv"] + df["revenue_achv"]) / 3).round(1)
    df["goal_status"] = df["overall_achv"].apply(
        lambda x: "목표 달성" if x >= 100 else ("근접" if x >= 85 else "미달")
    )
    return df.sort_values("overall_achv", ascending=False)


def get_goal_summary() -> dict:
    df = get_goal_vs_actual_df()
    achieved = df[df["goal_status"] == "목표 달성"]
    return {
        "avg_achv": round(float(df["overall_achv"].mean()), 1),
        "achieved_count": int(len(achieved)),
        "total_count": int(len(df)),
        "avg_rating_achv": round(float(df["rating_achv"].mean()), 1),
        "avg_revenue_achv": round(float(df["revenue_achv"].mean()), 1),
        "top_title": df.iloc[0]["title"],
        "top_achv": float(df.iloc[0]["overall_achv"]),
        "bottom_title": df.iloc[-1]["title"],
        "bottom_achv": float(df.iloc[-1]["overall_achv"]),
    }


def get_trend_data(show_id: str, period: str = "week") -> pd.DataFrame:
    catalog = {s["id"]: s for s in get_variety_catalog()}
    show = catalog.get(show_id)
    if not show:
        # fallback mock
        return mock.get_trend_data(show_id, period)

    history = show.get("rating_history") or [show.get("rating", 0)]
    title = show["title"]

    if period == "week":
        labels = [f"{i + 1}주" for i in range(len(history))]
        values = list(history)
    elif period == "month":
        labels = ["1월", "2월", "3월", "4월", "5월", "6월"]
        base = float(np.mean(history))
        values = [round(base * f, 4) for f in (0.85, 0.9, 0.95, 1.0, 1.02, 1.0)]
    else:
        labels = ["2023", "2024", "2025", "2026"]
        base = float(np.mean(history))
        values = [round(base * f, 4) for f in (0.7, 0.85, 0.95, 1.0)]

    return pd.DataFrame({"period": labels, "rating": values, "title": title})


def nielsen_slot_options() -> list[str]:
    """신규 기획 편성 후보: Mock 슬롯 + 닐슨 주요 시각."""
    slots = list(mock.COMPETITOR_SHOWS.keys())
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
    """신규 기획 분석 — 경쟁 시청률에 닐슨 실데이터 반영."""
    cast_list = [c.strip() for c in cast.split(",") if c.strip()] or ["미정"]
    cast_score = min(
        10,
        max(3, len([c for c in cast_list if c != "미정"]) * 2 + 3),
    )

    slot_competition = get_competition_data(slot)
    if slot_competition.empty or "rating" not in slot_competition.columns:
        avg_comp_rating = 2.0
        competition_records = []
    else:
        avg_comp_rating = float(slot_competition["rating"].mean())
        competition_records = slot_competition.to_dict("records")

    # 닐슨 점유 비중이 있으면 경쟁 점수에 가중
    nielsen_rows = [r for r in competition_records if r.get("data_source") == "nielsen"]
    competition_score = max(1, min(10, round(10 - avg_comp_rating * 1.5, 1)))
    if nielsen_rows:
        # 케이블 시청률 스케일(대개 <1) → 점수 보정
        avg_n = float(np.mean([r["rating"] for r in nielsen_rows]))
        competition_score = max(1, min(10, round(10 - avg_n * 8, 1)))

    live = get_variety_catalog()
    similar = [
        s
        for s in mock.ENDED_SHOWS + live
        if genre.split()[0] in s.get("genre", "")
    ]
    format_score = 6.0
    if similar:
        avg_sim = float(np.mean([s.get("avg_rating", s.get("rating", 1.5)) for s in similar]))
        format_score = min(10, round(avg_sim * 3 if avg_sim >= 1 else avg_sim * 12, 1))

    scores, score_details = mock._build_score_details(cast_score, competition_score, format_score)
    overall = round(float(np.mean(list(scores.values()))), 1)
    logline = mock._build_logline(title, genre, cast_list)
    swot = mock._build_swot_analysis(
        title, genre, slot, cast_list, scores, overall, competition_records, logline
    )

    # SWOT에 닐슨 근거 한 줄 보강
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
    parsed = mock.parse_uploaded_proposal(filename, file_bytes)
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
