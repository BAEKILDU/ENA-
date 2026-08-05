"""메인 홈 대시보드 — 예능 성과 분석 중심, 드라마는 비교군."""

import pandas as pd
import streamlit as st

from data.hybrid_data import (
    get_drama_comparison_catalog,
    get_ena_variety_df,
    get_weekly_summary,
)
from utils.charts import bar_chart, grouped_bar_chart
from utils.components import (
    render_action_card,
    render_content_card,
    render_metric_cards,
    render_section_title,
    render_summary_box,
)
from utils.format import format_rating, format_revenue_won
from utils.theme import COLORS


def _render_home_hero() -> None:
    """홈 전용 브랜드 헤더 — ENA 가치+."""
    html = (
        '<div style="background:linear-gradient(135deg,rgba(255,45,149,0.22) 0%,rgba(124,77,255,0.18) 45%,'
        'rgba(0,212,255,0.16) 100%);border:1px solid rgba(255,255,255,0.12);border-radius:22px;'
        'padding:2.1rem 2.5rem;margin-bottom:1.5rem;position:relative;overflow:hidden;'
        'box-shadow:0 12px 40px rgba(0,0,0,0.35),inset 0 1px 0 rgba(255,255,255,0.08);'
        'backdrop-filter:blur(16px);">'
        '<div style="position:absolute;right:-30px;top:-30px;width:180px;height:180px;'
        'background:radial-gradient(circle,rgba(255,45,149,0.25) 0%,transparent 70%);border-radius:50%;"></div>'
        '<div style="position:absolute;left:12%;bottom:-55px;width:150px;height:150px;'
        'background:radial-gradient(circle,rgba(0,212,255,0.16) 0%,transparent 70%);border-radius:50%;"></div>'
        '<div style="display:flex;align-items:center;gap:1.75rem;flex-wrap:wrap;position:relative;">'
        '<div style="display:flex;align-items:baseline;gap:0.35rem;line-height:1;">'
        f'<span style="font-size:2.85rem;font-weight:900;letter-spacing:-0.04em;color:#ffffff;'
        "text-shadow:0 0 24px rgba(255,45,149,0.35);\">ENA</span>"
        f'<span style="font-size:2.55rem;font-weight:800;letter-spacing:-0.03em;'
        f'background:linear-gradient(90deg,{COLORS["magenta"]},#ff8ac4 45%,{COLORS["cyan"]});'
        '-webkit-background-clip:text;background-clip:text;color:transparent;">가치</span>'
        f'<span style="font-size:2.9rem;font-weight:900;color:{COLORS["magenta"]};'
        "line-height:0.85;margin-left:0.05rem;"
        'text-shadow:0 0 18px rgba(255,45,149,0.55);">+</span>'
        "</div>"
        '<div style="width:1px;height:42px;background:rgba(255,255,255,0.18);"></div>'
        '<div style="flex:1;min-width:220px;">'
        '<div style="color:rgba(255,255,255,0.92);font-size:0.78rem;font-weight:700;'
        'letter-spacing:0.12em;margin-bottom:0.35rem;">CONTENT VALUE PLUS</div>'
        '<div style="color:rgba(255,255,255,0.78);font-size:1rem;line-height:1.55;">'
        "예능 콘텐츠 성과 관리 · 콘텐츠 가치 확장 분석</div>"
        "</div></div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render() -> None:
    _render_home_hero()

    summary_data = get_weekly_summary()
    variety_df = get_ena_variety_df().sort_values("rating", ascending=False)
    drama_df = pd.DataFrame(get_drama_comparison_catalog())
    if not drama_df.empty and "rating" in drama_df.columns:
        drama_df = drama_df.sort_values("rating", ascending=False)

    variety_n = len(variety_df)
    drama_n = len(drama_df)
    total_capex = float(summary_data.get("total_revenue") or 0)
    if not variety_df.empty and "revenue_million" in variety_df.columns:
        total_capex = float(variety_df["revenue_million"].fillna(0).sum())

    df = variety_df
    top_title = summary_data["top_title"]
    top_rating = summary_data["top_rating"]
    if not df.empty and "rating" in df.columns and df["rating"].notna().any():
        top_row = df.loc[df["rating"].idxmax()]
        top_title = top_row["title"]
        top_rating = float(top_row["rating"])

    drama_avg = None
    if not drama_df.empty and "rating" in drama_df.columns and drama_df["rating"].notna().any():
        drama_avg = float(drama_df["rating"].mean())

    render_summary_box(
        f"ENA 예능 {variety_n}편 성과 분석 기준, "
        f"최고 성과 '{top_title}' ({format_rating(top_rating)}) · "
        f"예능 누적 CAPEX 약 {format_revenue_won(total_capex)}. "
        + (
            f"드라마 {drama_n}편은 비교군으로 참고합니다"
            + (f" (평균 시청률 {format_rating(drama_avg)})" if drama_avg is not None else "")
            + ". "
            if drama_n
            else ""
        )
        + "사이드바 관리자 액션에서 자료를 업로드하면 자동 분류·반영됩니다."
        + (f" · 기준일 {summary_data['report_date']}" if summary_data.get("report_date") else "")
    )

    render_metric_cards(
        [
            {"label": "예능 분석 대상", "value": f"{variety_n}편"},
            {"label": "예능 최고 시청률", "value": format_rating(top_rating)},
            {"label": "예능 누적 CAPEX", "value": format_revenue_won(total_capex)},
            {
                "label": "드라마 비교군",
                "value": f"{drama_n}편" if drama_n else "-",
            },
        ]
    )

    if df.empty:
        st.info("표시할 예능 데이터가 없습니다. 사이드바 **관리자 액션**에서 오리지널/닐슨 자료를 업로드하세요.")
    else:
        chart_df = df.dropna(subset=["rating"]) if "rating" in df.columns else df
        render_section_title("예능 프로그램별 성과")
        st.plotly_chart(
            bar_chart(
                x=chart_df["title"].tolist(),
                y=chart_df["rating"].tolist(),
                title="",
                y_title="시청률 (%)",
                text_template="%{y:.3f}%",
                highlight_indices={0},
            ),
            use_container_width=True,
        )

        render_section_title("예능 시청률 · 화제성 비교")
        st.plotly_chart(
            grouped_bar_chart(
                categories=chart_df["title"].tolist(),
                series={
                    "시청률(%)": chart_df["rating"].tolist(),
                    "화제성(점)": chart_df["buzz_index"].tolist(),
                },
                title="",
                y_title="지표",
            ),
            use_container_width=True,
        )

    if not drama_df.empty and "rating" in drama_df.columns:
        render_section_title("비교군 · 드라마 참고")
        st.caption("드라마는 예능 성과 분석의 비교 기준으로만 활용합니다.")
        d_chart = drama_df.dropna(subset=["rating"]).head(10)
        if not d_chart.empty:
            avg_v = float(df["rating"].mean()) if not df.empty and "rating" in df.columns else 0.0
            avg_d = float(d_chart["rating"].mean())
            st.plotly_chart(
                grouped_bar_chart(
                    categories=["예능 평균", "드라마 비교군 평균"],
                    series={"시청률(%)": [avg_v, avg_d]},
                    title="",
                    y_title="시청률 (%)",
                ),
                use_container_width=True,
            )
            st.plotly_chart(
                bar_chart(
                    x=d_chart["title"].tolist(),
                    y=d_chart["rating"].tolist(),
                    title="",
                    y_title="시청률 (%)",
                    text_template="%{y:.3f}%",
                ),
                use_container_width=True,
            )

    render_section_title("주요 분석 모듈")
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        render_content_card(
            "관리자 액션",
            items=[
                "01. 오리지널 콘텐츠 관리 엑셀 자동 분류",
                "02. 닐슨 시청률 · 매출 CAPEX 업로드",
                "03. 목표 시청률·화제성·매출 Supabase 반영",
            ],
            highlight="사이드바에서 이동",
            highlight_color=COLORS["cyan"],
            accent=COLORS["cyan"],
        )
    with c2:
        render_content_card(
            "예능 콘텐츠 가치+",
            items=[
                "01. ENA 예능 동시간대 경쟁 비교 분석",
                "02. 시청률·화제성 기준 상·하위 그룹 분류",
                "03. 주/월/연 단위 트렌드 및 가치 매트릭스",
            ],
            highlight="예능 성과 중심",
            highlight_color=COLORS["magenta"],
            accent=COLORS["magenta"],
        )
    with c3:
        render_content_card(
            "신규 콘텐츠 가치+",
            items=[
                "01. 신규 기획안 업로드 및 경쟁력 분석",
                "02. 출연진·편성·동시간 경쟁 10점 만점 지표",
                "03. 유사 콘텐츠 벤치마크 및 부가 가치 제안",
            ],
            highlight="경쟁 실데이터 반영",
            highlight_color=COLORS["purple"],
            accent=COLORS["purple"],
        )

    render_section_title("빠른 이동")
    ac1, ac2 = st.columns(2, gap="large")
    with ac1:
        render_action_card(
            "예능 콘텐츠 분석",
            "방송 중 ENA 예능의 동시간대 경쟁 비교, 상·하위 분류, 트렌드 분석을 확인합니다.",
            "go_variety",
            "variety",
        )
    with ac2:
        render_action_card(
            "신규 콘텐츠 분석",
            "기획안 업로드 · 10점 만점 경쟁력 분석 · 부가 가치 수익 제안을 확인합니다.",
            "go_new",
            "new_content",
        )

    st.caption("※ 관리자 액션(사이드바)에서 자료 업로드 → 예능 중심 대시보드 반영")
