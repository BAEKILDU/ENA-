"""예능 콘텐츠 가치+ 상세 페이지."""

import streamlit as st

from data.hybrid_data import (
    get_competition_data,
    get_ena_variety_df,
    get_trend_data,
    get_variety_catalog,
)
from utils.format import format_rating, format_revenue_won
from utils.charts import bar_chart, grouped_bar_chart
from utils.components import navigate_to, render_page_header, render_section_title, render_summary_box


def render() -> None:
    render_page_header("예능 콘텐츠 상세 분석", "세부 지표 · 동시간대 경쟁 · 주/월/연 트렌드")

    df = get_ena_variety_df()
    catalog = get_variety_catalog()
    if df.empty or not catalog:
        st.info("표시할 닐슨 예능 데이터가 없습니다. 관리자 페이지에서 데이터를 업로드하세요.")
        if st.button("← 예능 가치+로 돌아가기", key="back_variety_empty"):
            navigate_to("variety")
        return

    show_id = st.selectbox(
        "콘텐츠 선택",
        options=df["id"].tolist(),
        format_func=lambda x: next(
            (s["title"] for s in catalog if s["id"] == x),
            x,
        ),
        key="detail_show",
    )
    show = next(s for s in catalog if s["id"] == show_id)
    metrics = df[df["id"] == show_id].iloc[0]

    render_summary_box(
        f"'{show['title']}' ({show['genre']}, {show['slot']}) — "
        f"시청률 {format_rating(metrics['rating'])}, "
        f"화제성 {metrics['buzz_index']}점, "
        f"부가매출 {format_revenue_won(metrics['revenue_million'])}, 트렌드 {metrics['trend']}. "
        f"방송 {show['weeks_on_air']}주차 · 출연: {', '.join(show['cast'])}. "
        f"데이터 출처: 닐슨 실데이터."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("시청률", format_rating(metrics["rating"]))
    c2.metric("화제성", f"{metrics['buzz_index']}점")
    c3.metric("부가매출", format_revenue_won(metrics["revenue_million"]))
    c4.metric("출처", "닐슨")

    period = st.radio("트렌드 기간", ["주", "월", "연"], horizontal=True, key="detail_period")
    period_map = {"주": "week", "월": "month", "연": "year"}
    trend_df = get_trend_data(show_id, period_map[period])

    render_section_title("시청률 추이")
    st.plotly_chart(
        bar_chart(
            x=trend_df["period"].tolist(),
            y=trend_df["rating"].tolist(),
            title="",
            y_title="시청률 (%)",
            text_template="%{y:.3f}%",
        ),
        use_container_width=True,
    )

    render_section_title("가치 레이더")
    st.plotly_chart(
        grouped_bar_chart(
            categories=["시청률", "화제성", "부가매출"],
            series={
                "실적": [
                    float(metrics["rating"]),
                    float(metrics["buzz_index"]) / 10,
                    float(metrics["revenue_million"]) / 100,
                ],
                "목표": [
                    float(metrics["target_rating"]),
                    float(metrics["target_buzz"]) / 10,
                    float(metrics["target_revenue_million"]) / 100,
                ],
            },
            title="",
            y_title="정규화 지표",
        ),
        use_container_width=True,
    )

    render_section_title("동시간대 경쟁")
    comp_df = get_competition_data(show["slot"])
    if comp_df.empty:
        st.info("해당 시간대 경쟁 데이터가 없습니다.")
    else:
        highlight = {i for i, ena in enumerate(comp_df["is_ena"].tolist()) if ena}
        labels = [
            f"{r.channel} · {r.title}"
            for r in comp_df.itertuples()
        ]
        st.plotly_chart(
            bar_chart(
                x=labels,
                y=comp_df["rating"].tolist(),
                title="",
                y_title="시청률 (%)",
                text_template="%{y:.3f}%",
                highlight_indices=highlight,
            ),
            use_container_width=True,
        )
        st.dataframe(
            comp_df.rename(
                columns={
                    "channel": "채널",
                    "title": "프로그램",
                    "rating": "시청률(%)",
                    "is_ena": "ENA",
                    "data_source": "출처",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    if st.button("← 예능 가치+로 돌아가기", key="back_variety"):
        navigate_to("variety")
