"""공통 UI 컴포넌트."""

import html

import streamlit as st

from utils.theme import COLORS


def navigate_to(page_key: str) -> None:
    """프로그래매틱 페이지 이동."""
    st.session_state["nav_target"] = page_key
    st.rerun()


def render_sidebar_header() -> None:
    """사이드바 브랜드 헤더."""
    header_html = (
        '<div style="padding:0.35rem 0.15rem 0.85rem;">'
        f'<div style="font-size:1.35rem;font-weight:800;color:#ffffff;'
        f'letter-spacing:-0.02em;line-height:1.25;">ENA 가치+</div>'
        f'<div style="font-size:0.75rem;color:{COLORS["text_muted"]};margin-top:0.4rem;'
        f'font-weight:500;letter-spacing:0.02em;">콘텐츠제작센터</div></div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


def render_sidebar_nav(pages: dict, sections: list[tuple[str, list[str]]], current_page: str) -> str:
    """섹션 구분형 사이드바 네비게이션 (이모지 없음)."""
    page_keys = [key for _, keys in sections for key in keys]
    active_key = current_page if current_page in page_keys else page_keys[0]
    selected = active_key

    for section_label, keys in sections:
        st.markdown(
            f'<div class="ena-sidebar-section">{section_label}</div>',
            unsafe_allow_html=True,
        )
        for key in keys:
            label = pages[key][0]
            is_active = key == active_key
            if st.button(
                label,
                key=f"sidebar_btn_{key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if not is_active:
                    selected = key
                    st.session_state["current_page"] = key
                    st.rerun()

    return selected


def render_hero_header(title: str, subtitle: str = "", badge: str = "콘텐츠제작센터") -> None:
    """다크 네온 그라데이션 헤더."""
    subtitle_html = (
        f'<div style="color:rgba(255,255,255,0.78);font-size:0.95rem;margin-top:0.55rem;">{subtitle}</div>'
        if subtitle
        else ""
    )
    html = (
        '<div style="background:linear-gradient(135deg,rgba(255,45,149,0.22) 0%,rgba(124,77,255,0.18) 45%,'
        'rgba(0,212,255,0.16) 100%);border:1px solid rgba(255,255,255,0.12);border-radius:22px;'
        'padding:2rem 2.5rem;margin-bottom:1.5rem;position:relative;overflow:hidden;'
        'box-shadow:0 12px 40px rgba(0,0,0,0.35),inset 0 1px 0 rgba(255,255,255,0.08);'
        'backdrop-filter:blur(16px);">'
        '<div style="position:absolute;right:-30px;top:-30px;width:180px;height:180px;'
        'background:radial-gradient(circle,rgba(255,45,149,0.25) 0%,transparent 70%);border-radius:50%;"></div>'
        '<div style="position:absolute;left:40px;bottom:-50px;width:140px;height:140px;'
        'background:radial-gradient(circle,rgba(0,212,255,0.18) 0%,transparent 70%);border-radius:50%;"></div>'
        f'<div style="color:{COLORS["magenta"]};font-size:0.8rem;font-weight:700;'
        f'letter-spacing:0.06em;margin-bottom:0.5rem;">[{badge}]</div>'
        f'<div style="color:#ffffff;font-size:1.85rem;font-weight:800;line-height:1.3;">{title}</div>'
        f"{subtitle_html}</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_summary_box(summary: str, icon: str = "📋") -> None:
    """리포트 상단 핵심 요약 박스."""
    safe_summary = html.escape(summary)
    box_html = (
        '<div style="background:rgba(255,255,255,0.05);border-radius:18px;overflow:hidden;'
        'margin-bottom:1.5rem;border:1px solid rgba(255,255,255,0.10);'
        'box-shadow:0 8px 32px rgba(0,0,0,0.25);backdrop-filter:blur(12px);">'
        '<div style="background:linear-gradient(90deg,rgba(255,45,149,0.35),rgba(124,77,255,0.25));'
        'color:white;padding:0.8rem 1.25rem;font-weight:700;font-size:0.9rem;'
        'border-bottom:1px solid rgba(255,255,255,0.08);">'
        f"{icon} 핵심 요약</div>"
        '<div style="padding:1.25rem 1.5rem;color:#e2e8f0;font-size:1rem;line-height:1.75;">'
        f"{safe_summary}</div></div>"
    )
    st.markdown(box_html, unsafe_allow_html=True)


def render_analysis_summary(result: dict) -> None:
    """pro2 템플릿 — 핵심 요약 / 개요 / 강·약점 / 분석 의견."""
    overview = result.get("overview") or {
        "title": result.get("title", "미정"),
        "genre": result.get("genre", "미정"),
        "slot": result.get("slot", "미정"),
        "channel": "ENA",
        "cast": result.get("cast", []),
        "logline": "미정",
    }
    swot = result.get("swot") or {}
    summary = result.get("summary") or {}
    source_label = "업로드 기획안" if result.get("source") == "upload" else "직접 작성"
    source_file = result.get("source_file", "")
    source_info = f"{source_label} · {source_file}" if source_file else source_label

    title = overview.get("title") or "미정"
    genre = overview.get("genre") or "미정"
    channel = overview.get("channel") or "ENA"
    slot = overview.get("slot") or "미정"
    cast_list = overview.get("cast", result.get("cast", []))
    cast_str = ", ".join(cast_list) if cast_list else "미정"
    logline = overview.get("logline") or "미정"
    overall = summary.get("overall", result.get("overall", 0))
    intent = summary.get("intent", swot.get("intent_summary", logline))
    one_liner = summary.get("one_liner", swot.get("one_liner", "-"))
    key_strength = summary.get("key_strength", (swot.get("strengths") or ["-"])[0])
    key_risk = summary.get("key_risk", (swot.get("weaknesses") or ["-"])[0])

    # 1. 기획안 핵심 요약 (항목별 구분)
    st.markdown("##### 1. 기획안 핵심 요약")
    extraction = result.get("extraction") or {}
    if extraction.get("warnings") or extraction.get("missing_fields"):
        with st.container(border=True):
            st.markdown("**기획안 추출·검증 결과**")
            if extraction.get("drm_locked"):
                st.error("DRM 암호화 문서로 본문 추출이 제한되었습니다.")
            if extraction.get("extractable"):
                st.caption("본문 텍스트 추출 완료 — 개요 필드 검증을 수행했습니다.")
            for warn in extraction.get("warnings") or []:
                st.warning(warn)
            missing = extraction.get("missing_fields") or []
            if missing:
                st.markdown("확인되지 않은 항목(미정): **" + ", ".join(missing) + "**")
            else:
                st.success("필수 개요 항목(콘텐츠명·장르·채널·편성시간·출연자·로그라인) 검증 완료")

    summary_header = (
        '<div style="background:rgba(255,255,255,0.05);border-radius:18px;overflow:hidden;'
        'margin-bottom:0.75rem;border:1px solid rgba(255,255,255,0.10);'
        'box-shadow:0 8px 32px rgba(0,0,0,0.25);backdrop-filter:blur(12px);">'
        '<div style="background:linear-gradient(90deg,rgba(255,45,149,0.35),rgba(124,77,255,0.25));'
        'color:white;padding:0.8rem 1.25rem;font-weight:700;font-size:0.9rem;'
        'border-bottom:1px solid rgba(255,255,255,0.08);">핵심 요약</div></div>'
    )
    st.markdown(summary_header, unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(f"**출처**  \n{source_info}")
        st.markdown("---")
        st.markdown(f"**기획의도 · 내용 요약**  \n{intent}")
        st.markdown("---")
        st.markdown(f"**총평**  \n{one_liner}")
        st.markdown("---")
        s1, s2 = st.columns(2)
        with s1:
            st.markdown(f"**종합 경쟁력 점수**  \n{overall}/10")
            st.markdown(f"**핵심 강점**  \n{key_strength}")
        with s2:
            st.markdown(f"**치명적 약점 / 리스크**  \n{key_risk}")
            st.markdown(f"**콘텐츠명**  \n{title}")

    # 2. 콘텐츠 개요
    st.markdown("##### 2. 콘텐츠 개요")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**콘텐츠명**  \n{title}")
            st.markdown(f"**장르**  \n{genre}")
            st.markdown(f"**편성채널**  \n{channel}")
        with c2:
            st.markdown(f"**편성시간**  \n{slot}")
            st.markdown(f"**주요출연자**  \n{cast_str}")
            st.markdown(f"**로그라인**  \n{logline}")

    # 3. 강점 및 약점
    st.markdown("##### 3. 기획안 분석 — 강점 및 약점")
    sc1, sc2 = st.columns(2)
    with sc1:
        with st.container(border=True):
            st.success("**강점 (Strengths)**")
            for item in swot.get("strengths") or ["도출된 강점 항목이 없습니다."]:
                st.markdown(f"- {item}")
    with sc2:
        with st.container(border=True):
            st.error("**약점 (Weaknesses)**")
            for item in swot.get("weaknesses") or ["도출된 약점 항목이 없습니다."]:
                st.markdown(f"- {item}")

    # 4. 분석 결론 제안
    st.markdown("##### 4. 분석 결론 제안")
    oc1, oc2, oc3 = st.columns(3)
    with oc1:
        with st.container(border=True):
            st.success("**긍정 의견**")
            for item in swot.get("positive", []):
                st.markdown(f"- {item}")
    with oc2:
        with st.container(border=True):
            st.info("**중립 의견**")
            for item in swot.get("neutral", []):
                st.markdown(f"- {item}")
    with oc3:
        with st.container(border=True):
            st.warning("**부정 의견**")
            for item in swot.get("negative", []):
                st.markdown(f"- {item}")


def render_metric_cards(metrics: list[dict]) -> None:
    """KPI 메트릭 카드 행."""
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            delta = m.get("delta")
            st.metric(label=m["label"], value=m["value"], delta=delta)


def render_page_header(title: str, subtitle: str = "") -> None:
    """서브 페이지 헤더."""
    render_hero_header(title, subtitle)


def render_section_title(title: str) -> None:
    """섹션 타이틀."""
    st.markdown(f"##### » {title}")


def render_content_card(
    card_title: str,
    items: list[str],
    highlight: str = "",
    highlight_color: str | None = None,
    accent: str | None = None,
) -> None:
    """2열 카드 레이아웃용 콘텐츠 카드."""
    accent = accent or COLORS["purple"]
    highlight_color = highlight_color or COLORS["magenta"]

    items_html = "".join(
        f'<p style="margin:0 0 0.55rem 0;"><strong>{item.split(".", 1)[0]}.</strong> '
        f'{item.split(".", 1)[1].strip() if "." in item else item}</p>'
        for item in items
    )
    highlight_html = (
        f'<p style="margin:0.75rem 0 0;color:{highlight_color};font-weight:700;">{highlight}</p>'
        if highlight
        else ""
    )

    # Streamlit HTML 블록은 빈 줄이 있으면 파싱이 끊기므로 한 줄로 출력
    html = (
        f'<div style="background:rgba(255,255,255,0.05);border-radius:18px;'
        f'border:1px solid rgba(255,255,255,0.10);box-shadow:0 8px 32px rgba(0,0,0,0.22);'
        f'backdrop-filter:blur(12px);">'
        f'<div style="background:linear-gradient(90deg,{accent}55,rgba(255,255,255,0.02));'
        f'color:white;padding:0.85rem 1.25rem;font-weight:700;font-size:0.95rem;'
        f'border-bottom:1px solid rgba(255,255,255,0.08);">{card_title}</div>'
        f'<div style="padding:1.25rem;color:#cbd5e1;font-size:0.92rem;line-height:1.75;">'
        f"{items_html}{highlight_html}</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_action_card(title: str, description: str, button_key: str, page_key: str) -> None:
    """액션 카드 + 이동 버튼."""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(description)
    if st.button(f"{title} 바로가기 →", key=button_key, use_container_width=True, type="primary"):
        navigate_to(page_key)


def render_group_item(rank: str, title: str, details: str, highlight: str = "") -> None:
    """번호 목록 아이템."""
    st.markdown(f"**{rank}. {title}**")
    detail_text = f"{details} · **{highlight}**" if highlight else details
    st.caption(detail_text)
    st.divider()
