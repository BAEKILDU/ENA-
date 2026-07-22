"""예능 콘텐츠 가치+ 메인 대시보드."""

import hashlib
import random

import pandas as pd
import streamlit as st

from data.hybrid_data import (
    get_competition_data,
    get_ena_variety_df,
    get_goal_summary,
    get_goal_vs_actual_df,
    get_top_bottom_groups,
    get_trend_data,
    get_variety_catalog,
    get_weekly_summary,
)
from utils.format import format_revenue_won
from utils.charts import bar_chart, grouped_bar_chart
from utils.components import (
    navigate_to,
    render_group_item,
    render_metric_cards,
    render_page_header,
    render_section_title,
    render_summary_box,
)


def _competition_chart(slot: str):
    df = get_competition_data(slot)
    if df.empty or "is_ena" not in df.columns:
        # 선택 시간대에 Mock이 없을 때 샘플 경쟁 데이터 표시
        seed = int(hashlib.md5(slot.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        df = pd.DataFrame(
            [
                {"title": f"ENA ({slot})", "is_ena": True, "rating": round(rng.uniform(1.0, 2.2), 1)},
                {"title": "동시간대 A", "is_ena": False, "rating": round(rng.uniform(1.5, 3.5), 1)},
                {"title": "동시간대 B", "is_ena": False, "rating": round(rng.uniform(1.2, 3.0), 1)},
                {"title": "동시간대 C", "is_ena": False, "rating": round(rng.uniform(0.8, 2.8), 1)},
            ]
        )
    highlight = {i for i, ena in enumerate(df["is_ena"]) if ena}
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
        text_template="%{y}%",
        highlight_indices=highlight,
    )
    y_max = max(y_vals) if y_vals else 1.0
    fig.update_yaxes(rangemode="tozero", range=[0, y_max * 1.25])
    return fig


def _trend_chart(show_id: str, period: str):
    df = get_trend_data(show_id, period)
    return bar_chart(
        x=df["period"].tolist(),
        y=df["rating"].tolist(),
        title="",
        y_title="시청률 (%)",
        text_template="%{y}%",
    )


def _value_bar_chart(df):
    return grouped_bar_chart(
        categories=df["title"].tolist(),
        series={
            "시청률(%)": df["rating"].tolist(),
            "화제성(점)": df["buzz_index"].tolist(),
            "부가매출(억)": (df["revenue_million"] / 100).round(2).tolist(),
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
        y=goal_df["overall_achv"].tolist(),
        title="",
        y_title="종합 달성률 (%)",
        text_template="%{y}%",
        highlight_indices={i for i, v in enumerate(goal_df["overall_achv"]) if v >= 100},
    )


def render() -> None:
    render_page_header("예능 콘텐츠 가치+", "ENA 예능 · 주/월/연 단위 가치 분석 · 동시간대 경쟁 비교")

    summary = get_weekly_summary()
    df = get_ena_variety_df()
    top, bottom = get_top_bottom_groups()
    goal_df = get_goal_vs_actual_df()
    goal_summary = get_goal_summary()

    render_summary_box(
        f"ENA 예능 {len(df)}편 중 '{summary['top_title']}'이 "
        f"시청률·화제성 종합 1위. "
        f"상위 그룹({', '.join(s['title'] for s in top)})은 동시간대 경쟁에서도 우위, "
        f"하위 그룹({', '.join(s['title'] for s in bottom)})은 편성·포맷 재검토 필요. "
        f"평균 시청률 {summary['avg_rating']}%, "
        f"누적 부가매출 {format_revenue_won(summary['total_revenue'])}. "
        f"목표 대비 종합 달성률 평균 {goal_summary['avg_achv']}% "
        f"({goal_summary['achieved_count']}/{goal_summary['total_count']}편 목표 달성). "
        f"데이터: 닐슨 {summary.get('nielsen_count', 0)}편 + Mock {summary.get('mock_count', 0)}편"
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
            {"label": "평균 시청률", "value": f"{summary['avg_rating']}%"},
            {"label": "상승 트렌드", "value": f"{len(df[df['trend'] == '상승'])}편"},
            {"label": "평균 화제성", "value": f"{round(df['buzz_index'].mean())}점"},
        ]
    )

    render_section_title("목표 대비 실적")
    render_metric_cards(
        [
            {"label": "종합 달성률", "value": f"{goal_summary['avg_achv']}%"},
            {
                "label": "목표 달성",
                "value": f"{goal_summary['achieved_count']}/{goal_summary['total_count']}편",
            },
            {"label": "시청률 달성률", "value": f"{goal_summary['avg_rating_achv']}%"},
            {"label": "부가매출 달성률", "value": f"{goal_summary['avg_revenue_achv']}%"},
        ]
    )
    g1, g2 = st.columns(2, gap="large")
    with g1:
        st.caption("프로그램별 목표 · 실적 시청률")
        st.plotly_chart(_goal_rating_chart(goal_df), use_container_width=True)
    with g2:
        st.caption("프로그램별 종합 달성률 (100% 이상 = 목표 달성)")
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
    table_df["target_revenue_million"] = (table_df["target_revenue_million"] / 100).round(2)
    table_df["revenue_million"] = (table_df["revenue_million"] / 100).round(2)
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
            "overall_achv": "종합 달성(%)",
            "goal_status": "상태",
        }
    )
    st.dataframe(table_df, use_container_width=True, hide_index=True)
    st.caption(
        f"최고 달성: {goal_summary['top_title']} ({goal_summary['top_achv']}%) · "
        f"최저 달성: {goal_summary['bottom_title']} ({goal_summary['bottom_achv']}%)"
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
                f"{s['slot']} · 시청률 {s['rating']}% · 화제성 {s['buzz_index']} · 트렌드 {s['trend']}",
                highlight="우수",
            )
        st.plotly_chart(
            bar_chart(
                x=[s["title"] for s in top],
                y=[s["rating"] for s in top],
                title="",
                y_title="시청률 (%)",
                text_template="%{y}%",
            ),
            use_container_width=True,
        )
    with col2:
        render_section_title("하위 그룹")
        for i, s in enumerate(bottom, 1):
            render_group_item(
                f"0{i}",
                s["title"],
                f"{s['slot']} · 시청률 {s['rating']}% · 화제성 {s['buzz_index']} · 트렌드 {s['trend']}",
                highlight="재검토 필요",
            )
        st.plotly_chart(
            bar_chart(
                x=[s["title"] for s in bottom],
                y=[s["rating"] for s in bottom],
                title="",
                y_title="시청률 (%)",
                text_template="%{y}%",
            ),
            use_container_width=True,
        )

    render_section_title("동시간대 경쟁 비교")
    _days = ["월", "화", "수", "목", "금", "토", "일"]
    _hours = [f"{h:02d}" for h in range(0, 25)]
    _minutes = [f"{m:02d}" for m in range(0, 60, 5)]
    day_col, hour_col, min_col = st.columns(3)
    with day_col:
        selected_day = st.selectbox("요일 선택", _days, key="comp_day")
    with hour_col:
        selected_hour = st.selectbox("시간 선택 (시)", _hours, key="comp_hour")
    with min_col:
        selected_minute = st.selectbox("분 선택 (5분 단위)", _minutes, key="comp_minute")
    slot = f"{selected_day} {selected_hour}:{selected_minute}"
    st.plotly_chart(_competition_chart(slot), use_container_width=True)

    render_section_title("트렌드 분석")
    top_show = df.loc[df["rating"].idxmax()]
    buzz_show = df.loc[df["buzz_index"].idxmax()]
    catalog = get_variety_catalog()
    trend_show_id = st.selectbox(
        "콘텐츠 선택",
        options=df["id"].tolist(),
        format_func=lambda x: next(
            (f"{s['title']} [{s.get('data_source', 'mock')}]" for s in catalog if s["id"] == x),
            x,
        ),
        index=list(df["id"]).index(top_show["id"]),
        key="trend_show",
    )
    st.plotly_chart(_trend_chart(trend_show_id, period_map[period]), use_container_width=True)

    st.caption(
        f"시청률 1위: {top_show['title']} ({top_show['rating']}%) · "
        f"화제성 1위: {buzz_show['title']} ({buzz_show['buzz_index']}점) · "
        f"닐슨 {summary.get('nielsen_count', 0)}편 + Mock {summary.get('mock_count', 0)}편"
    )

    if st.button("세부 데이터 보기 →", key="go_variety_detail", type="primary"):
        navigate_to("variety_detail")
