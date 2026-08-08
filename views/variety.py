"""예능 콘텐츠 가치+ 메인 대시보드."""

import streamlit as st

from data.hybrid_data import (
    get_competition_data,
    get_competition_program_options,
    get_ena_variety_df,
    get_goal_summary,
    get_goal_vs_actual_df,
    get_top_bottom_groups,
    get_trend_data,
    get_variety_catalog,
    get_weekly_summary,
)
from utils.format import format_pct, format_rating, format_revenue_won
from utils.charts import bar_chart, grouped_bar_chart
from utils.components import (
    navigate_to,
    render_group_item,
    render_metric_cards,
    render_page_header,
    render_section_title,
    render_summary_box,
)


def _competition_chart(df):
    if df is None or df.empty:
        return None
    if "is_selected" in df.columns:
        highlight = {i for i, sel in enumerate(df["is_selected"]) if sel}
    elif "is_ena" in df.columns:
        highlight = {i for i, ena in enumerate(df["is_ena"]) if ena}
    else:
        highlight = {0}
    if "channel" in df.columns:
        labels = [f"{c} · {t}" for c, t in zip(df["channel"].tolist(), df["title"].tolist())]
    else:
        labels = df["title"].tolist()
    y_vals = [float(v) for v in df["rating"].tolist()]
    fig = bar_chart(
        x=labels,
        y=y_vals,
        title="",
        y_title="시청률 (%)",
        text_template="%{y:.3f}%",
        highlight_indices=highlight,
    )
    y_max = max(y_vals) if y_vals else 1.0
    fig.update_yaxes(rangemode="tozero", range=[0, y_max * 1.25])
    return fig


def _default_competition_slot(df):
    """카탈로그 상위 프로그램의 요일/시/분을 기본 슬롯으로 사용."""
    days = ["월", "화", "수", "목", "금", "토", "일"]
    for row in df.sort_values("rating", ascending=False).itertuples():
        day = getattr(row, "day", None) or "-"
        time = getattr(row, "time", None) or "-"
        if day in days and isinstance(time, str) and ":" in time:
            hh, mm = time.split(":")[:2]
            try:
                h, m = int(hh), int(mm)
            except ValueError:
                continue
            m = (m // 5) * 5
            return day, f"{h:02d}", f"{m:02d}"
    return "수", "22", "30"

def _trend_chart(show_id: str, period: str):
    df = get_trend_data(show_id, period)
    if df.empty:
        return None, df
    fig = bar_chart(
        x=df["period"].tolist(),
        y=df["rating"].tolist(),
        title="",
        y_title="시청률 (%)",
        text_template="%{y:.3f}%",
    )
    y_vals = [float(v) for v in df["rating"].tolist()]
    y_max = max(y_vals) if y_vals else 1.0
    fig.update_yaxes(rangemode="tozero", range=[0, y_max * 1.25])
    return fig, df


def _value_bar_chart(df):
    return grouped_bar_chart(
        categories=df["title"].tolist(),
        series={
            "시청률(%)": df["rating"].tolist(),
            "화제성(점)": df["buzz_index"].tolist(),
            "부가매출(억)": (df["revenue_million"] / 100).round(1).tolist(),
        },
        title="",
        y_title="지표",
    )


def _goal_rating_chart(goal_df):
    return grouped_bar_chart(
        categories=goal_df["title"].tolist(),
        series={
            "목표 시청률(%)": goal_df["target_rating"].tolist(),
            "실적 시청률(%)": goal_df["rating"].tolist(),
        },
        title="",
        y_title="시청률 (%)",
    )


def _goal_achv_chart(goal_df):
    return bar_chart(
        x=goal_df["title"].tolist(),
        y=goal_df["rating_achv"].tolist(),
        title="",
        y_title="목표시청률 달성률 (%)",
        text_template="%{y:.3f}%",
        highlight_indices={i for i, v in enumerate(goal_df["rating_achv"]) if v >= 100},
    )


def render() -> None:
    render_page_header("예능 콘텐츠 가치+", "ENA 예능 · 주/월/연 단위 가치 분석 · 동시간대 경쟁 비교")

    summary = get_weekly_summary()
    df = get_ena_variety_df()
    top, bottom = get_top_bottom_groups()
    goal_df = get_goal_vs_actual_df()
    goal_summary = get_goal_summary()

    if df.empty:
        render_summary_box(
            "표시할 ENA 예능 닐슨 데이터가 없습니다. "
            "관리자 페이지에서 닐슨 파일을 업로드하거나 Supabase 연결을 확인하세요."
            + (f" (최근 리포트일: {summary.get('report_date')})" if summary.get("report_date") else "")
        )
        return

    render_summary_box(
        f"ENA 예능 {len(df)}편 중 '{summary['top_title']}'이 "
        f"시청률·화제성 종합 1위. "
        f"상위 그룹({', '.join(s['title'] for s in top)})은 동시간대 경쟁에서도 우위, "
        f"하위 그룹({', '.join(s['title'] for s in bottom)})은 편성·포맷 재검토 필요. "
        f"평균 시청률 {format_rating(summary['avg_rating'])}, "
        f"누적 부가매출 {format_revenue_won(summary['total_revenue'])}. "
        f"목표 대비 목표시청률 달성률 평균 {format_pct(goal_summary['avg_achv'])} "
        f"({goal_summary['achieved_count']}/{goal_summary['total_count']}편 목표 달성). "
        f"데이터: 닐슨 실데이터 {summary.get('nielsen_count', 0)}편"
        + (f" · 기준일 {summary['report_date']}" if summary.get("report_date") else "")
        + "."
    )

    if "variety_period" not in st.session_state:
        st.session_state["variety_period"] = "주"
    st.markdown("**분석 기간**")
    p1, p2, p3 = st.columns(3)
    for col, opt in zip((p1, p2, p3), ("주", "월", "연")):
        with col:
            is_active = st.session_state["variety_period"] == opt
            if st.button(
                opt,
                key=f"variety_period_btn_{opt}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if not is_active:
                    st.session_state["variety_period"] = opt
                    st.rerun()
    period = st.session_state["variety_period"]
    period_map = {"주": "week", "월": "month", "연": "year"}

    render_metric_cards(
        [
            {
                "label": "분석 대상",
                "value": f"{len(df)}편",
            },
            {"label": "평균 시청률", "value": format_rating(summary["avg_rating"])},
            {"label": "상승 트렌드", "value": f"{len(df[df['trend'] == '상승'])}편"},
            {"label": "평균 화제성", "value": f"{round(df['buzz_index'].mean())}점"},
        ]
    )

    render_section_title("목표 대비 실적")
    render_metric_cards(
        [
            {"label": "목표시청률 달성률", "value": format_pct(goal_summary["avg_achv"])},
            {
                "label": "목표 달성",
                "value": f"{goal_summary['achieved_count']}/{goal_summary['total_count']}편",
            },
            {"label": "시청률 달성률", "value": format_pct(goal_summary["avg_rating_achv"])},
            {"label": "부가매출 달성률", "value": format_pct(goal_summary["avg_revenue_achv"])},
        ]
    )
    g1, g2 = st.columns(2, gap="large")
    with g1:
        st.caption("프로그램별 목표 · 실적 시청률")
        st.plotly_chart(_goal_rating_chart(goal_df), use_container_width=True)
    with g2:
        st.caption("프로그램별 목표시청률 달성 (100% 이상 = 목표 달성)")
        st.plotly_chart(_goal_achv_chart(goal_df), use_container_width=True)

    table_df = goal_df[
        [
            "title",
            "target_rating",
            "rating",
            "rating_achv",
            "target_buzz",
            "buzz_index",
            "buzz_achv",
            "target_revenue_million",
            "revenue_million",
            "revenue_achv",
            "overall_achv",
            "goal_status",
        ]
    ].copy()
    table_df["target_revenue_million"] = (table_df["target_revenue_million"] / 100).round(1)
    table_df["revenue_million"] = (table_df["revenue_million"] / 100).round(1)
    table_df["target_rating"] = table_df["target_rating"].round(3)
    table_df["rating"] = table_df["rating"].round(3)
    if "rating_achv" in table_df.columns:
        table_df["rating_achv"] = table_df["rating_achv"].round(0).astype(int)
    if "buzz_achv" in table_df.columns:
        table_df["buzz_achv"] = table_df["buzz_achv"].round(0).astype(int)
    if "revenue_achv" in table_df.columns:
        table_df["revenue_achv"] = table_df["revenue_achv"].round(0).astype(int)
    if "overall_achv" in table_df.columns:
        table_df["overall_achv"] = table_df["overall_achv"].round(0).astype(int)
    if "target_buzz" in table_df.columns:
        table_df["target_buzz"] = table_df["target_buzz"].round(0).astype(int)
    if "buzz_index" in table_df.columns:
        table_df["buzz_index"] = table_df["buzz_index"].round(0).astype(int)
    table_df = table_df.rename(
        columns={
            "title": "프로그램",
            "target_rating": "목표 시청률(%)",
            "rating": "실적 시청률(%)",
            "rating_achv": "시청률 달성(%)",
            "target_buzz": "목표 화제성",
            "buzz_index": "실적 화제성",
            "buzz_achv": "화제성 달성(%)",
            "target_revenue_million": "목표 매출(억)",
            "revenue_million": "실적 매출(억)",
            "revenue_achv": "매출 달성(%)",
            "overall_achv": "목표시청률 달성(%)",
            "goal_status": "상태",
        }
    )
    st.dataframe(table_df, use_container_width=True, hide_index=True)
    st.caption(
        f"최고 달성: {goal_summary['top_title']} ({format_pct(goal_summary['top_achv'])}) · "
        f"최저 달성: {goal_summary['bottom_title']} ({format_pct(goal_summary['bottom_achv'])})"
    )

    render_section_title("가치 지표 비교")
    st.plotly_chart(_value_bar_chart(df), use_container_width=True)

    col1, col2 = st.columns(2, gap="large")
    with col1:
        render_section_title("상위 그룹")
        for i, s in enumerate(top, 1):
            render_group_item(
                f"0{i}",
                s["title"],
                f"{s['slot']} · 시청률 {format_rating(s['rating'])} · 화제성 {s['buzz_index']} · 트렌드 {s['trend']}",
                highlight="우수",
            )
        if top:
            st.plotly_chart(
                bar_chart(
                    x=[s["title"] for s in top],
                    y=[s["rating"] for s in top],
                    title="",
                    y_title="시청률 (%)",
                    text_template="%{y:.3f}%",
                ),
                use_container_width=True,
            )
    with col2:
        render_section_title("하위 그룹")
        for i, s in enumerate(bottom, 1):
            render_group_item(
                f"0{i}",
                s["title"],
                f"{s['slot']} · 시청률 {format_rating(s['rating'])} · 화제성 {s['buzz_index']} · 트렌드 {s['trend']}",
                highlight="재검토 필요",
            )
        if bottom:
            st.plotly_chart(
                bar_chart(
                    x=[s["title"] for s in bottom],
                    y=[s["rating"] for s in bottom],
                    title="",
                    y_title="시청률 (%)",
                    text_template="%{y:.3f}%",
                ),
                use_container_width=True,
            )

    render_section_title("동시간대 경쟁 비교")
    _days = ["월", "화", "수", "목", "금", "토", "일"]
    _hours = [f"{h:02d}" for h in range(0, 25)]
    _minutes = [f"{m:02d}" for m in range(0, 60, 5)]
    def_day, def_hour, def_min = _default_competition_slot(df)
    if "comp_day_v2" not in st.session_state:
        st.session_state["comp_day_v2"] = def_day
    if "comp_hour_v2" not in st.session_state:
        st.session_state["comp_hour_v2"] = def_hour
    if "comp_minute_v2" not in st.session_state:
        st.session_state["comp_minute_v2"] = def_min if def_min in _minutes else "00"
    day_col, hour_col, min_col = st.columns(3)
    with day_col:
        selected_day = st.selectbox(
            "요일 선택",
            _days,
            key="comp_day_v2",
        )
    with hour_col:
        selected_hour = st.selectbox(
            "시간 선택 (시)",
            _hours,
            key="comp_hour_v2",
        )
    with min_col:
        selected_minute = st.selectbox(
            "분 선택 (5분 단위)",
            _minutes,
            key="comp_minute_v2",
        )
    slot = f"{selected_day} {selected_hour}:{selected_minute}"

    options_df = get_competition_program_options(slot)
    selected_title = None
    if not options_df.empty:
        option_labels = [
            f"{r.channel} · {r.title} ({format_rating(r.rating)})"
            for r in options_df.itertuples()
        ]
        picked = st.selectbox(
            "기준 콘텐츠 선택",
            options=list(range(len(option_labels))),
            format_func=lambda i: option_labels[i],
            key=f"comp_baseline_{slot}",
        )
        selected_title = options_df.iloc[picked]["title"]

    comp_df = get_competition_data(slot, selected_title=selected_title)
    comp_fig = _competition_chart(comp_df)
    if comp_fig is None:
        st.info(f"'{slot}' 시간대에 닐슨 경쟁 데이터가 없습니다.")
    else:
        st.caption(
            f"기준 콘텐츠(좌측) + 주요채널 동시간대 상위 {max(0, len(comp_df) - 1)}개 비교 · "
            f"시청률 소수점 3자리"
        )
        st.plotly_chart(comp_fig, use_container_width=True)
        show_cols = {
            "channel": "채널",
            "title": "프로그램",
            "rating": "시청률(%)",
            "is_selected": "기준",
            "is_ena": "ENA",
            "data_source": "출처",
        }
        table_df = comp_df.rename(columns={k: v for k, v in show_cols.items() if k in comp_df.columns})
        if "시청률(%)" in table_df.columns:
            table_df["시청률(%)"] = table_df["시청률(%)"].map(lambda v: round(float(v), 3))
        st.dataframe(table_df, use_container_width=True, hide_index=True)

    render_section_title("트렌드 분석")
    top_show = df.loc[df["rating"].idxmax()]
    buzz_show = df.loc[df["buzz_index"].idxmax()]
    catalog = get_variety_catalog()

    st.markdown("**트렌드 기간**")
    t1, t2, t3 = st.columns(3)
    for col, opt in zip((t1, t2, t3), ("주", "월", "연")):
        with col:
            is_active = st.session_state["variety_period"] == opt
            if st.button(
                opt,
                key=f"trend_period_btn_{opt}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if not is_active:
                    st.session_state["variety_period"] = opt
                    st.rerun()
    period = st.session_state["variety_period"]
    period_label = {"week": "주", "month": "월", "year": "연"}[period_map[period]]

    ids = df["id"].tolist()
    if "trend_show" not in st.session_state or st.session_state["trend_show"] not in ids:
        st.session_state["trend_show"] = top_show["id"]
    trend_show_id = st.selectbox(
        "콘텐츠 선택",
        options=ids,
        format_func=lambda x: next(
            (s["title"] for s in catalog if s["id"] == x),
            x,
        ),
        key="trend_show",
    )
    trend_fig, trend_df = _trend_chart(trend_show_id, period_map[period])
    if trend_fig is None or trend_df.empty:
        st.info("선택한 콘텐츠의 닐슨 시청률 트렌드 데이터가 없습니다.")
    else:
        avg_rating = (
            float(trend_df["avg_rating"].iloc[0])
            if "avg_rating" in trend_df.columns
            else float(trend_df["rating"].mean())
        )
        m1, m2, m3 = st.columns(3)
        m1.metric("콘텐츠 시청률 전체 평균", format_rating(avg_rating))
        m2.metric(f"{period_label}별 구간 수", f"{len(trend_df)}개")
        m3.metric(
            "최근 구간 시청률",
            format_rating(float(trend_df["rating"].iloc[-1])),
        )
        st.caption("Supabase 닐슨 리포트일 실데이터 기준 · 시청률 소수점 3자리")
        st.plotly_chart(trend_fig, use_container_width=True)
        table = trend_df[["period", "rating"]].rename(
            columns={"period": f"{period_label} 구간", "rating": "시청률(%)"}
        )
        table["시청률(%)"] = table["시청률(%)"].map(lambda v: round(float(v), 3))
        table["전체 평균(%)"] = round(avg_rating, 3)
        st.dataframe(table, use_container_width=True, hide_index=True)

    st.caption(
        f"시청률 1위: {top_show['title']} ({format_rating(top_show['rating'])}) · "
        f"화제성 1위: {buzz_show['title']} ({buzz_show['buzz_index']}점) · "
        f"닐슨 실데이터 {summary.get('nielsen_count', 0)}편"
        + (f" · 기준일 {summary.get('report_date')}" if summary.get("report_date") else "")
    )

    if st.button("세부 데이터 보기 →", key="go_variety_detail", type="primary"):
        navigate_to("variety_detail")
