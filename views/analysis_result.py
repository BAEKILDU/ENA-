"""분석 결과 상세 페이지 (/analysis-result) — pro2 템플릿."""

import html
import re

import streamlit as st

from data.mock_data import get_revenue_ideas
from utils.charts import bar_chart, horizontal_bar_chart
from utils.components import (
    navigate_to,
    render_analysis_summary,
    render_metric_cards,
    render_page_header,
    render_section_title,
    render_summary_box,
)
from utils.export_docx import build_analysis_docx


def render() -> None:
    result = st.session_state.get("analysis_result")
    if not result:
        render_page_header("분석 결과", "경쟁력 분석 상세")
        render_summary_box("분석할 기획안이 없습니다. 신규 콘텐츠 가치+ 페이지에서 분석을 시작해 주세요.")
        if st.button("← 신규 콘텐츠 가치+로 이동", type="primary"):
            navigate_to("new_content")
        return

    render_page_header("경쟁력 분석 결과", "신규 콘텐츠 가치+ · 분석 상세 리포트")

    # 1~4
    render_analysis_summary(result)

    # 5. 주요 데이터 지표
    kpi = result.get("kpi") or {
        "overall": result.get("overall", 0),
        "required_cast": len(result.get("cast", [])),
        "best_slot": result.get("slot", "미정"),
        "competitor_count": len(result.get("competition", [])),
    }
    render_section_title("5. 주요 데이터 지표")
    render_metric_cards(
        [
            {"label": "종합 경쟁력 지수", "value": f"{kpi.get('overall', 0)}/10"},
            {"label": "필요 핵심 출연진 수", "value": f"{kpi.get('required_cast', 0)}명"},
            {"label": "최적 편성 시간 제안", "value": str(kpi.get("best_slot", "미정"))},
            {
                "label": "동시간대/유사 장르 경쟁",
                "value": f"{kpi.get('competitor_count', 0)}편",
            },
        ]
    )

    # 6. 10점 만점 경쟁력 세부 지표
    render_section_title("6. 10점 만점 경쟁력 세부 지표")
    scores = result.get("scores") or {}
    score_details = result.get("score_details") or {}
    st.plotly_chart(
        horizontal_bar_chart(
            labels=list(scores.keys()),
            values=list(scores.values()),
            title="",
            x_title="점수",
            text_suffix="/10",
            height=420,
        ),
        use_container_width=True,
    )
    st.plotly_chart(
        bar_chart(
            x=list(scores.keys()),
            y=list(scores.values()),
            title="",
            y_title="점수 (10점 만점)",
            text_template="%{y}",
            height=380,
        ),
        use_container_width=True,
    )
    with st.container(border=True):
        st.markdown("**세부 지표 평가 이유**")
        for name, detail in score_details.items():
            score = detail.get("score", scores.get(name, "-"))
            reason = detail.get("reason", "-")
            st.markdown(f"- **{name}** [{score}/10] — {reason}")

    if result.get("similar_shows"):
        st.caption("유사 콘텐츠 참고")
        for s in result["similar_shows"]:
            rating = s.get("avg_rating", s.get("rating", "-"))
            st.markdown(
                f"- {s.get('title', '-')} · {s.get('genre', '')} · 시청률 {rating}%"
            )

    # 7. 부가 사업 및 수익 창출 아이디어
    render_section_title("7. 부가 사업 및 수익 창출 아이디어")
    ideas = get_revenue_ideas(result.get("genre", ""))
    for group in ideas:
        with st.container(border=True):
            st.markdown(f"**{group['category']}**")
            for idea in group["ideas"]:
                st.markdown(f"- {idea}")

    # 8. 종합 결론 (강조 디자인)
    conclusion = result.get("final_conclusion") or result.get("swot", {}).get(
        "final_conclusion", "종합 결론을 생성하려면 분석을 다시 실행해 주세요."
    )
    safe_conclusion = html.escape(str(conclusion))
    st.markdown(
        '<div style="margin:1.75rem 0 0.75rem;display:flex;align-items:center;gap:0.75rem;">'
        '<div style="flex:1;height:1px;background:linear-gradient(90deg,transparent,'
        "rgba(255,45,149,0.55),rgba(0,212,255,0.35),transparent);\"></div>"
        '<div style="font-size:0.78rem;font-weight:800;letter-spacing:0.12em;color:#ff2d95;'
        'text-transform:uppercase;">Final Verdict</div>'
        '<div style="flex:1;height:1px;background:linear-gradient(90deg,transparent,'
        "rgba(0,212,255,0.35),rgba(255,45,149,0.55),transparent);\"></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="position:relative;border-radius:22px;overflow:hidden;margin-bottom:1.25rem;'
        "background:linear-gradient(145deg,rgba(255,45,149,0.18) 0%,rgba(13,20,36,0.95) 42%,"
        "rgba(0,212,255,0.12) 100%);"
        "border:1px solid rgba(255,45,149,0.45);"
        "box-shadow:0 0 0 1px rgba(0,212,255,0.12),0 16px 48px rgba(255,45,149,0.22),"
        'inset 0 1px 0 rgba(255,255,255,0.08);">'
        '<div style="background:linear-gradient(90deg,#ff2d95,#7c4dff,#00d4ff);'
        'padding:0.85rem 1.4rem;display:flex;align-items:center;justify-content:space-between;">'
        '<div style="color:#fff;font-size:1.05rem;font-weight:800;letter-spacing:-0.01em;">'
        "8. 종합 결론</div>"
        '<div style="color:rgba(255,255,255,0.92);font-size:0.72rem;font-weight:700;'
        "letter-spacing:0.08em;background:rgba(0,0,0,0.28);padding:0.28rem 0.7rem;"
        'border-radius:999px;border:1px solid rgba(255,255,255,0.18);">핵심 판정</div>'
        "</div>"
        '<div style="padding:1.45rem 1.55rem 1.55rem;">'
        '<div style="color:#f8fafc;font-size:1.12rem;font-weight:650;line-height:1.85;'
        'letter-spacing:-0.01em;">'
        f"{safe_conclusion}</div>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    overview = result.get("overview") or {}
    title = overview.get("title", result.get("title", "분석결과"))
    safe_name = re.sub(r'[\\/:*?"<>|]+', "_", str(title)).strip() or "분석결과"
    docx_bytes = build_analysis_docx(result)

    st.markdown(
        "<style>"
        'div[data-testid="stDownloadButton"] button {'
        "font-size:0.78rem !important;"
        "padding:0.35rem 0.85rem !important;"
        "min-height:2.1rem !important;"
        "border-radius:999px !important;"
        "background:linear-gradient(135deg,rgba(255,45,149,0.45),rgba(124,77,255,0.35)) !important;"
        "border:1px solid rgba(255,45,149,0.35) !important;"
        "color:#ffffff !important;"
        "box-shadow:0 0 14px rgba(255,45,149,0.18) !important;"
        "}"
        "</style>",
        unsafe_allow_html=True,
    )
    back_col, _, dl_col = st.columns([2.2, 1.5, 1.1])
    with back_col:
        if st.button("← 신규 콘텐츠 가치+로 돌아가기"):
            navigate_to("new_content")
    with dl_col:
        st.download_button(
            label="워드 다운로드",
            data=docx_bytes,
            file_name=f"ENA_경쟁력분석_{safe_name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            key="download_analysis_docx",
        )
