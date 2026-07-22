"""신규 콘텐츠 가치+ — 기획안 입력 페이지."""

import time

import streamlit as st

from data.hybrid_data import analyze_new_proposal, analyze_uploaded_proposal, nielsen_slot_options
from utils.components import navigate_to, render_page_header

GENRES = ["푸드 예능", "서바이벌 예능", "퀴즈 예능", "리얼리티 예능", "코미디 예능", "드라마", "예능"]
TAB_UPLOAD = "파일 업로드"
TAB_MANUAL = "직접 작성"


def _init_tab_state() -> None:
    if "proposal_input_tab" not in st.session_state:
        st.session_state["proposal_input_tab"] = TAB_UPLOAD


def _render_tab_menu() -> str:
    """상단 탭 메뉴 — 선택된 탭만 입력 영역 렌더링."""
    _init_tab_state()
    current = st.session_state["proposal_input_tab"]

    st.caption("입력 방식 선택")

    tab1, tab2 = st.columns(2)
    with tab1:
        if st.button(
            "📎 파일 업로드",
            use_container_width=True,
            type="primary" if current == TAB_UPLOAD else "secondary",
            key="tab_btn_upload",
        ):
            st.session_state["proposal_input_tab"] = TAB_UPLOAD
            st.rerun()
    with tab2:
        if st.button(
            "✏️ 직접 작성",
            use_container_width=True,
            type="primary" if current == TAB_MANUAL else "secondary",
            key="tab_btn_manual",
        ):
            st.session_state["proposal_input_tab"] = TAB_MANUAL
            st.rerun()

    return st.session_state["proposal_input_tab"]


def _render_upload_section() -> None:
    st.caption("신규 기획안 문서를 첨부하세요. (PDF, DOCX, TXT, MD)")
    st.file_uploader(
        "신규 기획안 문서를 첨부하세요",
        type=["pdf", "docx", "txt", "md"],
        key="proposal_upload",
        help="기획안 파일을 선택한 뒤 하단 「경쟁력 분석 시작」 버튼을 눌러 주세요.",
    )


def _render_manual_section() -> None:
    slots = nielsen_slot_options()
    st.caption("프로그램 정보를 입력하세요. 편성 시간대는 닐슨 실데이터 시각이 포함됩니다.")
    st.text_input("프로그램명", placeholder="예: ENA 미식 로드", key="manual_title")
    st.selectbox("장르", GENRES, key="manual_genre")
    st.selectbox("편성 시간대", slots, key="manual_slot")
    st.text_input("출연진 (쉼표 구분)", placeholder="예: 유재석, 박나래, 이영자", key="manual_cast")


def _start_analysis(input_mode: str) -> None:
    slots = nielsen_slot_options()
    default_slot = slots[0] if slots else "수 22:00"

    if input_mode == TAB_UPLOAD:
        uploaded = st.session_state.get("proposal_upload")
        if uploaded is None:
            st.error("기획안 파일을 업로드해 주세요.")
            return
        file_bytes = uploaded.getvalue()
        if file_bytes[:5] == b"SCDSA":
            st.error(
                "첨부하신 PDF가 SoftCamp DRM(암호화) 상태라 본문 텍스트를 읽을 수 없습니다. "
                "암호 해제본(일반 PDF/DOCX/TXT)을 업로드하거나 「직접 작성」 탭으로 정보를 입력해 주세요."
            )
            return
        with st.spinner(f"'{uploaded.name}' 기획안 본문 분석·검증 중… (닐슨 경쟁 데이터 반영)"):
            time.sleep(0.6)
            result = analyze_uploaded_proposal(uploaded.name, file_bytes)
            missing = (result.get("extraction") or {}).get("missing_fields") or []
            if missing:
                st.warning(
                    "기획안에서 일부 정보가 확인되지 않아 '미정'으로 표시됩니다: "
                    + ", ".join(missing)
                )
    else:
        title = (st.session_state.get("manual_title") or "").strip()
        cast = (st.session_state.get("manual_cast") or "").strip()
        genre = st.session_state.get("manual_genre", GENRES[0])
        slot = st.session_state.get("manual_slot", default_slot)
        if not title or not cast:
            st.error("프로그램명과 출연진을 입력해 주세요.")
            return
        with st.spinner("기획안 분석 중… (닐슨 경쟁 데이터 반영)"):
            time.sleep(0.6)
            result = analyze_new_proposal(title, genre, slot, cast)

    st.session_state["analysis_result"] = result
    navigate_to("analysis_result")


def render() -> None:
    render_page_header(
        "신규 콘텐츠 가치+",
        "기획안 업로드 · 경쟁력 분석 · 부가 가치 수익 제안 (닐슨 실데이터 반영)",
    )

    input_mode = _render_tab_menu()

    with st.container(border=True):
        if input_mode == TAB_UPLOAD:
            _render_upload_section()
        else:
            _render_manual_section()

    st.markdown("---")
    if st.button("경쟁력 분석 시작", type="primary", use_container_width=True, key="start_analysis_btn"):
        _start_analysis(input_mode)
