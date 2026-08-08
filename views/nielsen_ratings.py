"""닐슨 채널시청률 — Supabase 실데이터 대시보드."""

from __future__ import annotations

import streamlit as st

from data import nielsen as nd
from utils.charts import bar_chart, grouped_bar_chart, horizontal_bar_chart
from utils.components import (
    render_metric_cards,
    render_page_header,
    render_section_title,
    render_summary_box,
)
from utils.theme import COLORS


def _fmt_pct(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "-"
    return f"{value:.{digits}f}%"


def render() -> None:
    render_page_header(
        "닐슨 채널 시청률",
        "Supabase에 업로드된 닐슨 채널시청률 실데이터 시각화",
    )

    if not nd.supabase_ready():
        st.error("SUPABASE_URL / SUPABASE_ANON_KEY 설정을 확인하세요.")
        return

    try:
        dates = nd.get_report_dates()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Supabase 조회 실패: {exc}")
        return

    if not dates:
        st.warning("업로드된 닐슨 데이터가 없습니다. 업로드 스크립트를 먼저 실행하세요.")
        return

    report_date = st.selectbox("분석일", dates, index=0)

    with st.spinner("닐슨 데이터 로딩 중…"):
        rankings = nd.get_channel_rankings(report_date)
        competition = nd.get_competition_ratings(report_date)
        targets = nd.get_target_details(report_date)

    segments = nd.ranking_segments(rankings)
    default_seg = (
        "수도권 유료방송가입가구"
        if "수도권 유료방송가입가구" in segments
        else (segments[0] if segments else None)
    )
    segment = st.selectbox(
        "채널 순위 세그먼트",
        segments,
        index=segments.index(default_seg) if default_seg in segments else 0,
    )

    ena = nd.channel_rank_in_segment(rankings, segment, "ENA")
    top20 = nd.top_channels(rankings, segment, n=20)

    sheets = nd.competition_sheets(competition)
    default_sheet = "ENA경쟁채널시청률" if "ENA경쟁채널시청률" in sheets else (sheets[0] if sheets else None)
    sheet_name = st.selectbox(
        "경쟁채널 시트",
        sheets,
        index=sheets.index(default_sheet) if default_sheet in sheets else 0,
    ) if sheets else None

    targets_list = nd.competition_targets(competition, sheet_name) if sheet_name else []
    preferred = [t for t in ("개인2049", "유료방송가구", "개인2039") if t in targets_list]
    target = st.selectbox(
        "타깃",
        targets_list,
        index=targets_list.index(preferred[0]) if preferred else 0,
    ) if targets_list else None

    # ── 요약 ──────────────────────────────────────────────────────────────
    top_prog = None
    if sheet_name and target:
        top_df = nd.top_programs(
            competition, channel="ENA", target=target, sheet_name=sheet_name, n=1
        )
        if not top_df.empty:
            top_prog = top_df.iloc[0]

    summary_bits = [f"{report_date} 기준"]
    if ena:
        summary_bits.append(
            f"ENA는 '{segment}'에서 {ena['rank']}위 · 시청률 {_fmt_pct(ena['rating'])}"
        )
    if top_prog is not None:
        summary_bits.append(
            f"최고 프로그램 '{top_prog['program_name']}' "
            f"({target} {_fmt_pct(float(top_prog['rating']))})"
        )
    render_summary_box(" · ".join(summary_bits) + ".")

    metrics = [
        {"label": "분석일", "value": report_date},
        {
            "label": "ENA 순위",
            "value": f"{ena['rank']}위" if ena and ena.get("rank") else "-",
        },
        {
            "label": "ENA 시청률",
            "value": _fmt_pct(ena.get("rating") if ena else None),
        },
        {
            "label": "ENA 점유율",
            "value": _fmt_pct(ena.get("share") if ena else None, 2),
        },
    ]
    render_metric_cards(metrics)

    # ── 채널 순위 ──────────────────────────────────────────────────────────
    render_section_title(f"채널 시청률 TOP 20 — {segment}")
    if top20.empty:
        st.info("해당 세그먼트 데이터가 없습니다.")
    else:
        highlight = {
            i for i, name in enumerate(top20["channel_name"].tolist()) if name == "ENA"
        }
        st.plotly_chart(
            bar_chart(
                x=top20["channel_name"].tolist(),
                y=top20["rating"].fillna(0).tolist(),
                title="",
                y_title="시청률 (%)",
                text_template="%{y:.3f}%",
                highlight_indices=highlight,
                height=420,
            ),
            use_container_width=True,
        )
        show_cols = ["rank", "channel_name", "rating", "share", "reach", "watch_time"]
        st.dataframe(
            top20[show_cols].rename(
                columns={
                    "rank": "순위",
                    "channel_name": "채널",
                    "rating": "시청률(%)",
                    "share": "점유율(%)",
                    "reach": "도달율(%)",
                    "watch_time": "시청시간",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    # ── ENA 프로그램 TOP ───────────────────────────────────────────────────
    if sheet_name and target:
        render_section_title(f"ENA 프로그램 TOP 10 — {target}")
        prog_df = nd.top_programs(
            competition, channel="ENA", target=target, sheet_name=sheet_name, n=10
        )
        if prog_df.empty:
            st.info("프로그램 데이터가 없습니다.")
        else:
            labels = [
                f"{r.program_name}\n({r.start_time or '-'})"
                for r in prog_df.itertuples()
            ]
            st.plotly_chart(
                horizontal_bar_chart(
                    labels=labels[::-1],
                    values=prog_df["rating"].fillna(0).tolist()[::-1],
                    title="",
                    x_title="시청률 (%)",
                    text_suffix="%",
                    height=420,
                ),
                use_container_width=True,
            )

            # 최고 시청 슬롯 경쟁 비교
            best = prog_df.iloc[0]
            slot = best.get("start_time")
            if slot:
                render_section_title(
                    f"동시간대 경쟁 비교 — {best['program_name']} ({slot})"
                )
                slot_df = nd.same_slot_competitors(
                    competition,
                    sheet_name=sheet_name,
                    target=target,
                    start_time=slot,
                    focus_channel="ENA",
                )
                if slot_df.empty:
                    # 시작시간이 채널마다 다를 수 있어, 시트 내 상위 채널 일일/피크 비교로 대체
                    peers = (
                        competition[
                            (competition["sheet_name"] == sheet_name)
                            & (competition["target"] == target)
                            & (~competition["is_daily_total"].fillna(False))
                        ]
                        .sort_values("rating", ascending=False)
                        .groupby("channel_name", as_index=False)
                        .first()
                        .sort_values("rating", ascending=False)
                        .head(10)
                    )
                    if not peers.empty:
                        hl = {
                            i
                            for i, c in enumerate(peers["channel_name"].tolist())
                            if c == "ENA"
                        }
                        st.caption("동일 시작시간 매칭이 없어, 시트 내 채널별 최고 시청률로 비교합니다.")
                        st.plotly_chart(
                            bar_chart(
                                x=peers["channel_name"].tolist(),
                                y=peers["rating"].fillna(0).tolist(),
                                title="",
                                y_title="시청률 (%)",
                                text_template="%{y:.3f}%",
                                highlight_indices=hl,
                            ),
                            use_container_width=True,
                        )
                else:
                    labels = [
                        f"{r.channel_name}\n{r.program_name}"
                        for r in slot_df.itertuples()
                    ]
                    hl = {i for i, ena in enumerate(slot_df["is_focus"].tolist()) if ena}
                    st.plotly_chart(
                        bar_chart(
                            x=labels,
                            y=slot_df["rating"].fillna(0).tolist(),
                            title="",
                            y_title="시청률 (%)",
                            text_template="%{y:.3f}%",
                            highlight_indices=hl,
                        ),
                        use_container_width=True,
                    )

    # ── 타깃별 상세 ────────────────────────────────────────────────────────
    render_section_title("ENA 타깃별 시청률")
    ena_targets = targets[targets["channel_name"] == "ENA"] if not targets.empty else targets
    if ena_targets.empty:
        st.info("타깃 상세 데이터가 없습니다.")
    else:
        programs = (
            ena_targets[~ena_targets["is_daily_total"].fillna(False)]["program_name"]
            .dropna()
            .unique()
            .tolist()
        )
        # 시청률 합 기준 상위 프로그램 우선
        ranked_programs = (
            ena_targets[~ena_targets["is_daily_total"].fillna(False)]
            .groupby("program_name", as_index=False)["rating"]
            .max()
            .sort_values("rating", ascending=False)["program_name"]
            .tolist()
        )
        program = st.selectbox(
            "프로그램",
            ranked_programs or programs,
            index=0 if ranked_programs or programs else None,
        ) if (ranked_programs or programs) else None

        if program:
            # 동일 프로그램의 여러 회차(시작시간) 중 최고 시청 회차
            cand = ena_targets[
                (ena_targets["program_name"] == program)
                & (~ena_targets["is_daily_total"].fillna(False))
            ]
            best_start = (
                cand.groupby("start_time")["rating"].max().sort_values(ascending=False).index[0]
                if not cand.empty
                else None
            )
            breakdown = nd.target_breakdown(
                targets, channel="ENA", program_name=program, start_time=best_start
            )
            # 주요 타깃만 (수도권/전국 핵심)
            priority = [
                "수도권 2049",
                "수도권 2039",
                "수도권 여3049",
                "전국 유료가구",
                "수도권 여20대",
                "수도권 여30대",
                "수도권 여40대",
                "수도권 남20대",
                "수도권 남30대",
                "수도권 남40대",
            ]
            ordered = [t for t in priority if t in set(breakdown["target"])]
            rest = [t for t in breakdown["target"].tolist() if t not in ordered]
            keep = ordered + rest[: max(0, 12 - len(ordered))]
            view = breakdown[breakdown["target"].isin(keep)].copy()
            view = view.set_index("target").loc[[t for t in keep if t in set(view["target"])]].reset_index()

            if not view.empty:
                st.caption(
                    f"{program}"
                    + (f" · {best_start}" if best_start else "")
                    + " · 타깃별 시청률/점유율"
                )
                st.plotly_chart(
                    grouped_bar_chart(
                        categories=view["target"].tolist(),
                        series={
                            "시청률(%)": view["rating"].fillna(0).round(3).tolist(),
                            "점유율(%)": view["share"].fillna(0).round(3).tolist(),
                        },
                        title="",
                        y_title="지표",
                        height=420,
                    ),
                    use_container_width=True,
                )

    st.caption(
        f"데이터 소스: Supabase · 분석일 {report_date} · "
        f'<span style="color:{COLORS["cyan"]}">실데이터</span>',
        unsafe_allow_html=True,
    )
