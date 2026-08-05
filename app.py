"""
ENA 가치+ — 콘텐츠제작센터 성과 관리 · 콘텐츠 가치 확장 분석 대시보드
실행: streamlit run app.py
"""

import streamlit as st

from utils import config  # noqa: F401  — .env 로드
from utils.components import navigate_to, render_sidebar_header, render_sidebar_nav
from utils.theme import GLOBAL_CSS
from data import local_db
from views import (
    admin,
    analysis_result,
    home,
    new_content,
    nielsen_ratings,
    variety,
    variety_detail,
)

# ── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ENA 가치+",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
local_db.init_schema()  # SQL Editor 없이 로컬 스키마 자동 준비
try:
    from data.supabase_upload import sync_admin_metrics_from_supabase

    sync_admin_metrics_from_supabase()  # 목표·화제성 지표 Supabase → 로컬
except Exception:  # noqa: BLE001
    pass

# ── 네비게이션 ─────────────────────────────────────────────────────────────────
PAGES = {
    "home": ("홈", home),
    "nielsen_ratings": ("닐슨 채널 시청률", nielsen_ratings),
    "variety": ("예능 콘텐츠 가치+", variety),
    "variety_detail": ("예능 상세 분석", variety_detail),
    "new_content": ("신규 콘텐츠 가치+", new_content),
    "analysis_result": ("분석 결과", analysis_result),
    "admin": ("관리자", admin),
}

SIDEBAR_SECTIONS = [
    ("메인", ["home"]),
    ("예능 분석", ["variety", "variety_detail"]),
    ("신규 기획", ["new_content"]),
]
SIDEBAR_PAGES = [key for _, keys in SIDEBAR_SECTIONS for key in keys]

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "home"

if "nav_target" in st.session_state:
    st.session_state["current_page"] = st.session_state.pop("nav_target")

with st.sidebar:
    render_sidebar_header()
    st.divider()

    current = st.session_state["current_page"]
    display_page = current if current in SIDEBAR_PAGES else "home"
    page_key = render_sidebar_nav(PAGES, SIDEBAR_SECTIONS, display_page)

    if current in SIDEBAR_PAGES:
        st.session_state["current_page"] = page_key
    elif page_key != "home" and page_key in SIDEBAR_PAGES:
        # 관리자 등 비사이드바 페이지에서 다른 메뉴 클릭 시 이동
        st.session_state["current_page"] = page_key

    st.divider()
    st.markdown(
        '<div class="ena-sidebar-section">관리자 액션</div>',
        unsafe_allow_html=True,
    )
    st.caption("자료 업로드 · 자동 분류 · DB 반영")
    if st.button(
        "관리자 액션",
        key="sidebar_admin_btn",
        use_container_width=True,
        type="primary" if current == "admin" else "secondary",
    ):
        navigate_to("admin")
    st.caption("ENA 가치+ · v0.9")
    st.caption("작성: 콘텐츠제작센터")

# ── 페이지 렌더 ────────────────────────────────────────────────────────────────
PAGES[st.session_state["current_page"]][1].render()
