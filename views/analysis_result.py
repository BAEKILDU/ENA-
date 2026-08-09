"""분석 결과 상세 페이지 (/analysis-result) — pro2 템플릿."""

import html
import re

import streamlit as st

from data.analysis_engine import get_revenue_ideas
from data.hybrid_data import analyze_new_proposal, nielsen_slot_options
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
from utils.format import format_rating
from utils.proposal_parse import FIELD_LABELS

_GENRES = ["푸드 예능", "서바이벌 예능", "퀴즈 예능", "리얼리티 예능", "코미디 예능", "드라마", "예능"]
_EDITABLE_KEYS = ("title", "genre", "channel", "slot", "cast", "logline")


def _overview_value(result: dict, key: str):
    overview = result.get("overview") or {}
    if key == "cast":
        cast = overview.get("cast") or result.get("cast") or []
        if isinstance(cast, list):
            return ", ".join(str(c) for c in cast if c)
        return str(cast or "")
    return overview.get(key) or result.get(key) or ""


def _is_missing_value(key: str, value) -> bool:
    if value is None:
        return True
    if isinstance(value, list):
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        return (not cleaned) or cleaned == ["미정"]
    text = str(value).strip()
    return (not text) or text == "미정"


def _incomplete_keys(result: dict) -> list[str]:
    missing_labels = set((result.get("extraction") or {}).get("missing_fields") or [])
    label_to_key = {v: k for k, v in FIELD_LABELS.items()}
    keys: list[str] = []
    for label in missing_labels:
        key = label_to_key.get(label)
        if key and key not in keys:
            keys.append(key)
    for key in _EDITABLE_KEYS:
        if key in keys:
            continue
        if _is_missing_value(key, _overview_value(result, key)):
            keys.append(key)
    return keys


def _apply_overrides(result: dict, overrides: dict) -> dict:
    title = str(overrides.get("title") or _overview_value(result, "title") or "미정").strip() or "미정"
    genre = str(overrides.get("genre") or _overview_value(result, "genre") or "리얼리티 예능").strip()
    if genre == "미정":
        genre = "리얼리티 예능"
    slot = str(overrides.get("slot") or _overview_value(result, "slot") or "수 22:00").strip()
    if slot == "미정":
        slot = "수 22:00"
    cast = str(overrides.get("cast") or _overview_value(result, "cast") or "미정").strip() or "미정"
    channel = str(overrides.get("channel") or _overview_value(result, "channel") or "ENA").strip() or "ENA"
    logline = str(overrides.get("logline") or _overview_value(result, "logline") or "미정").strip() or "미정"

    refreshed = analyze_new_proposal(title, genre, slot, cast)
    refreshed["source"] = result.get("source") or "upload"
    refreshed["source_file"] = result.get("source_file") or ""
    extraction = dict(result.get("extraction") or {})
    overview = refreshed.get("overview") or {}
    overview["title"] = title
    overview["genre"] = genre
    overview["slot"] = slot
    overview["channel"] = channel
    overview["cast"] = [c.strip() for c in cast.split(",") if c.strip()] or ["미정"]
    overview["logline"] = logline
    refreshed["overview"] = overview
    refreshed["title"] = title
    refreshed["genre"] = genre
    refreshed["slot"] = slot
    refreshed["cast"] = overview["cast"]

    still_missing = []
    for key in _EDITABLE_KEYS:
        label = FIELD_LABELS.get(key, key)
        if _is_missing_value(key, overview.get(key) if key != "cast" else overview.get("cast")):
            still_missing.append(label)
    extraction["missing_fields"] = still_missing
    refreshed["extraction"] = extraction

    if result.get("summary", {}).get("intent"):
        refreshed.setdefault("summary", {})
        refreshed["summary"]["intent"] = result["summary"]["intent"]
        if refreshed.get("swot") is not None:
            refreshed["swot"]["intent_summary"] = result["summary"]["intent"]
    return refreshed


def _render_override_actions(result: dict) -> None:
    """문서에서 확인되지 않은 항목 직접 입력 · 편성일정 수정 액션."""
    render_section_title("입력 보완 · 편성 수정")
    incomplete = _incomplete_keys(result)
    if incomplete:
        st.caption(
            "문서에서 확인되지 않은 항목: "
            + ", ".join(FIELD_LABELS.get(k, k) for k in incomplete)
        )
    else:
        st.caption("필수 항목은 확인되었습니다. 필요 시 값을 보완하거나 편성일정을 수정하세요.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "미확인 항목 직접 입력",
            key="btn_fill_missing",
            use_container_width=True,
            type="primary" if st.session_state.get("show_fill_missing") else "secondary",
        ):
            st.session_state["show_fill_missing"] = not st.session_state.get("show_fill_missing", False)
            st.session_state["show_edit_slot"] = False
            st.rerun()
    with c2:
        if st.button(
            "편성일정 수정",
            key="btn_edit_slot",
            use_container_width=True,
            type="primary" if st.session_state.get("show_edit_slot") else "secondary",
        ):
            st.session_state["show_edit_slot"] = not st.session_state.get("show_edit_slot", False)
            st.session_state["show_fill_missing"] = False
            st.rerun()

    if st.session_state.get("show_fill_missing"):
        keys = incomplete or list(_EDITABLE_KEYS)
        with st.container(border=True):
            st.markdown("**미확인·미정 항목 직접 입력**")
            overrides: dict = {}
            for key in keys:
                label = FIELD_LABELS.get(key, key)
                current = _overview_value(result, key)
                current_text = str(current).strip()
                if key == "genre":
                    idx = _GENRES.index(current_text) if current_text in _GENRES else 0
                    overrides[key] = st.selectbox(
                        label,
                        options=_GENRES,
                        index=idx,
                        key=f"fill_{key}",
                    )
                elif key == "slot":
                    slots = nielsen_slot_options()
                    options = list(slots)
                    if current_text and current_text not in options and current_text != "미정":
                        options = [current_text] + options
                    default = current_text if current_text in options else (options[0] if options else "수 22:00")
                    overrides[key] = st.selectbox(
                        label,
                        options=options or ["수 22:00"],
                        index=(options or ["수 22:00"]).index(default),
                        key=f"fill_{key}",
                    )
                else:
                    placeholder = "쉼표로 구분해 입력" if key == "cast" else f"{label} 입력"
                    overrides[key] = st.text_input(
                        label,
                        value="" if current_text == "미정" else current_text,
                        placeholder=placeholder,
                        key=f"fill_{key}",
                    )
            if st.button("입력 반영 · 재분석", type="primary", key="apply_fill_missing"):
                st.session_state["analysis_result"] = _apply_overrides(result, overrides)
                st.session_state["show_fill_missing"] = False
                st.success("입력 내용을 반영해 재분석했습니다.")
                st.rerun()

    if st.session_state.get("show_edit_slot"):
        with st.container(border=True):
            st.markdown("**편성일정 수정**")
            slots = nielsen_slot_options()
            current_slot = str(_overview_value(result, "slot") or "").strip() or "수 22:00"
            options = list(slots)
            if current_slot not in options:
                options = [current_slot] + options
            new_slot = st.selectbox(
                "편성 시간대",
                options=options or ["수 22:00"],
                index=(options or ["수 22:00"]).index(current_slot)
                if current_slot in (options or ["수 22:00"])
                else 0,
                key="edit_slot_select",
                help="닐슨 실데이터 기반 시간대가 포함됩니다.",
            )
            custom_slot = st.text_input(
                "직접 입력 (선택)",
                value="",
                placeholder="예: 목 22:30",
                key="edit_slot_custom",
            )
            if st.button("편성일정 반영 · 재분석", type="primary", key="apply_edit_slot"):
                slot_value = (custom_slot or "").strip() or new_slot
                st.session_state["analysis_result"] = _apply_overrides(result, {"slot": slot_value})
                st.session_state["show_edit_slot"] = False
                st.success(f"편성일정을 '{slot_value}'(으)로 반영해 재분석했습니다.")
                st.rerun()


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

    # 미확인 항목 직접 입력 · 편성일정 수정
    _render_override_actions(result)

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
            text_template="%{y:.0f}",
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
            rating = s.get("avg_rating", s.get("rating", None))
            st.markdown(
                f"- {s.get('title', '-')} · {s.get('genre', '')} · 시청률 {format_rating(rating)}"
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
