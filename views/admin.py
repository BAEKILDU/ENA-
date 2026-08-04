"""관리자 페이지 — 시청률/오리지널/매출 Excel → 자동 분류 · Supabase · 앱 반영."""

from __future__ import annotations

import gc
import tempfile
import time
from pathlib import Path

import streamlit as st

from data.nielsen_ingest import upload_nielsen_file
from data.original_content_ingest import apply_original_workbook, detect_workbook_kind
from data.revenue_ingest import build_revenue_template_bytes, upload_revenue_file
from data.supabase_upload import storage_status
from data import local_db
from utils.components import navigate_to, render_page_header, render_section_title


def _save_upload(uploaded, suffix: str) -> Path:
    raw = uploaded.getvalue()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(raw)
    tmp.close()
    return Path(tmp.name)


def _safe_unlink(path: Path) -> None:
    gc.collect()
    for _ in range(5):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError:
            time.sleep(0.15)
            gc.collect()
        except OSError:
            return


def _clear_data_caches() -> None:
    try:
        st.cache_data.clear()
    except Exception:  # noqa: BLE001
        pass
    try:
        from data.original_content import _supabase_client
        from data import nielsen as nd

        _supabase_client.cache_clear()
        if hasattr(nd, "_client"):
            pass
        # lru_cache clear if present
        for fn in (
            getattr(nd, "get_report_dates", None),
            getattr(nd, "get_competition_ratings", None),
        ):
            if fn is not None and hasattr(fn, "clear"):
                fn.clear()
    except Exception:  # noqa: BLE001
        pass


def _render_auto_uploader() -> None:
    render_section_title("1. 통합 업로드 (자동 분류)")
    st.caption(
        "오리지널 콘텐츠 관리 / 닐슨 시청률 / 매출 엑셀을 올리면 "
        "파일 종류를 판별해 CSV 분류 → Supabase 적재 → 대시보드에 바로 반영합니다."
    )
    file = st.file_uploader(
        "업데이트 자료 (.xls / .xlsx)",
        type=["xls", "xlsx"],
        key="admin_auto_file",
        help="예: ◎ _26년 오리지널 콘텐츠 관리 (260101~0802 현재).xlsx",
    )
    if st.button("자동 분류 · Supabase 업로드 · 앱 반영", type="primary", key="admin_auto_btn"):
        if file is None:
            st.error("파일을 선택해 주세요.")
            return
        suffix = Path(file.name).suffix.lower() or ".xlsx"
        path = _save_upload(file, suffix)
        try:
            kind = detect_workbook_kind(path, original_name=file.name)
            with st.spinner(f"처리 중… (감지: {kind})"):
                if kind == "original_content":
                    summary = apply_original_workbook(path, original_name=file.name)
                elif kind == "nielsen":
                    summary = upload_nielsen_file(path, original_name=file.name)
                    summary = {"kind": "nielsen", **summary}
                else:
                    summary = upload_revenue_file(path)
                    summary = {"kind": "revenue_simple", **summary}
            _clear_data_caches()
            st.success(
                f"업로드 완료 · 유형 `{summary.get('kind')}` · "
                f"기준일 {summary.get('report_date')} · 파일 {summary.get('source_file')}"
            )
            if summary.get("kind") == "original_content":
                c = summary.get("counts") or {}
                st.info(
                    f"프로그램 {c.get('programs_total', 0)}건 "
                    f"(드라마 {c.get('drama', 0)} · 예능 {c.get('variety', 0)}) · "
                    f"회차 {c.get('drama_episodes', 0)} · 목표 {c.get('targets', 0)}"
                )
                uploaded = summary.get("uploaded") or {}
                if uploaded.get("errors"):
                    st.warning("CSV는 저장됨. Supabase 일부 실패: " + "; ".join(uploaded["errors"]))
                else:
                    st.caption(
                        f"Supabase: revenue {uploaded.get('revenue_records', 0)} · "
                        f"original_programs {uploaded.get('original_programs', 0)}"
                    )
            st.json(summary)
        except Exception as exc:  # noqa: BLE001
            st.error(f"업로드 실패: {exc}")
        finally:
            _safe_unlink(path)


def _render_ratings_uploader() -> None:
    render_section_title("2. 닐슨 시청률 (전용)")
    st.caption("닐슨 채널시청률 엑셀 → nielsen_* 테이블")
    file = st.file_uploader("시청률 파일", type=["xls", "xlsx"], key="admin_ratings_file")
    if st.button("시청률 처리 · 업로드", type="primary", key="admin_ratings_btn"):
        if file is None:
            st.error("시청률 파일을 선택해 주세요.")
            return
        path = _save_upload(file, Path(file.name).suffix.lower() or ".xlsx")
        try:
            with st.spinner("시청률 파싱 및 업로드 중…"):
                summary = upload_nielsen_file(path, original_name=file.name)
            _clear_data_caches()
            backend = summary.get("backend") or (
                (summary.get("uploaded") or {}).get("backend")
            )
            st.success(
                f"시청률 업로드 완료 · {summary['report_date']} · "
                f"저장소 `{backend or 'local'}`"
            )
            if summary.get("warnings"):
                st.warning(" · ".join(summary["warnings"]))
            st.json(summary)
        except Exception as exc:  # noqa: BLE001
            st.error(f"시청률 업로드 실패: {exc}")
        finally:
            _safe_unlink(path)


def _render_revenue_uploader() -> None:
    render_section_title("3. 매출 템플릿 / CAPEX (전용)")
    st.caption("단순 매출 템플릿 또는 CAPEX 시트 → revenue_records")
    st.download_button(
        label="매출 템플릿 다운로드 (.xlsx)",
        data=build_revenue_template_bytes(),
        file_name="revenue_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="admin_revenue_template",
    )
    file = st.file_uploader("매출 파일", type=["xls", "xlsx"], key="admin_revenue_file")
    if st.button("매출 처리 · 업로드", type="primary", key="admin_revenue_btn"):
        if file is None:
            st.error("매출 파일을 선택해 주세요.")
            return
        path = _save_upload(file, Path(file.name).suffix.lower() or ".xlsx")
        try:
            kind = detect_workbook_kind(path, original_name=file.name)
            with st.spinner("매출/오리지널 처리 중…"):
                if kind == "original_content":
                    summary = apply_original_workbook(path, original_name=file.name)
                else:
                    summary = upload_revenue_file(path)
            _clear_data_caches()
            st.success(
                f"처리 완료 · 기준일 {summary.get('report_date')} · "
                f"저장소 `{summary.get('backend') or ((summary.get('uploaded') or {}).get('backend')) or 'local'}`"
            )
            if summary.get("warnings"):
                st.warning(" · ".join(summary["warnings"]))
            st.json(summary)
        except Exception as exc:  # noqa: BLE001
            st.error(f"매출 업로드 실패: {exc}")
        finally:
            _safe_unlink(path)


def _render_storage_banner() -> None:
    local_db.init_schema()
    status = storage_status()
    if status["active_backend"] == "supabase":
        st.success(
            "저장소: Supabase 연결됨 · 스키마는 로컬에도 자동 준비됩니다. "
            "SQL Editor 수동 실행은 더 이상 필요하지 않습니다."
        )
    else:
        st.warning(
            "저장소: **로컬 SQLite** 자동 사용 중 (시청률·매출 업로드 가능). "
            f"{status['supabase_message']} "
            "Supabase Dashboard → Project Settings → API 의 Project URL / anon key 를 "
            "`.env` 의 `SUPABASE_URL`, `SUPABASE_ANON_KEY` 에 다시 넣으면 클라우드로 전환됩니다."
        )
        st.caption(f"로컬 DB: `{status['local_db']}` · 테이블 자동 생성 완료")


def _render_target_rating_editor() -> None:
    render_section_title("4. 콘텐츠별 목표 시청률")
    st.caption(
        "업로드된 데이터 타이틀을 선택해 목표 시청률(%)·화제성·매출을 입력하면 "
        "홈·예능·상세·목표달성 등 각 섹션에 자동 반영됩니다."
    )
    local_db.init_schema()
    titles = local_db.list_uploaded_program_titles()
    saved = {r["program_name"]: r for r in local_db.list_target_ratings()}

    if not titles:
        st.info("먼저 위에서 오리지널/닐슨/매출 데이터를 업로드해 주세요.")
        return

    options = [t["program_name"] for t in titles]
    title_meta = {t["program_name"]: t.get("category") or "" for t in titles}

    selected = st.selectbox("타이틀 선택", options=options, key="admin_target_title")
    current = saved.get(selected) or {}
    default_val = float(current["target_rating"]) if current.get("target_rating") is not None else 0.0
    default_buzz = float(current["target_buzz"]) if current.get("target_buzz") is not None else 0.0
    default_rev_eok = (
        float(current["target_revenue_million"]) / 100.0
        if current.get("target_revenue_million") is not None
        else 0.0
    )
    category_options = ["예능", "드라마"]
    raw_cat = str(current.get("category") or title_meta.get(selected) or "").strip()
    default_cat = raw_cat if raw_cat in category_options else "예능"

    c1, c2 = st.columns([2, 1])
    with c1:
        target_val = st.number_input(
            "목표 시청률 (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(default_val),
            step=0.001,
            format="%.3f",
            key="admin_target_value",
        )
    with c2:
        category = st.selectbox(
            "구분",
            options=category_options,
            index=category_options.index(default_cat),
            key="admin_target_cat",
        )

    b1, b2 = st.columns(2)
    with b1:
        target_buzz = st.number_input(
            "목표 화제성 (점)",
            min_value=0.0,
            max_value=100.0,
            value=float(default_buzz),
            step=1.0,
            format="%.0f",
            key="admin_target_buzz",
        )
    with b2:
        target_rev_eok = st.number_input(
            "목표 매출 (억원)",
            min_value=0.0,
            max_value=100000.0,
            value=float(default_rev_eok),
            step=0.01,
            format="%.2f",
            key="admin_target_revenue",
        )

    if st.button("목표 저장 · 섹션 반영", type="primary", key="admin_target_save"):
        local_db.upsert_target_ratings(
            [
                {
                    "program_name": selected,
                    "category": category,
                    "target_rating": round(float(target_val), 3),
                    "target_buzz": float(target_buzz),
                    "target_revenue_million": round(float(target_rev_eok) * 100.0, 2),
                    "note": "admin",
                }
            ]
        )
        _clear_data_caches()
        st.success(
            f"'{selected}' 목표 시청률 {float(target_val):.3f}% · "
            f"화제성 {int(target_buzz)}점 · 매출 {float(target_rev_eok):.2f}억원 저장 · 각 섹션에 반영됨"
        )
        st.rerun()

    rows = local_db.list_target_ratings()
    if rows:
        st.dataframe(
            [
                {
                    "타이틀": r["program_name"],
                    "구분": r.get("category") or "-",
                    "목표 시청률(%)": (
                        round(float(r["target_rating"]), 3)
                        if r.get("target_rating") is not None
                        else None
                    ),
                    "목표 화제성": (
                        int(round(float(r["target_buzz"])))
                        if r.get("target_buzz") is not None
                        else None
                    ),
                    "목표 매출(억)": (
                        round(float(r["target_revenue_million"]) / 100.0, 2)
                        if r.get("target_revenue_million") is not None
                        else None
                    ),
                    "수정시각": r.get("updated_at"),
                }
                for r in rows
            ],
            use_container_width=True,
            hide_index=True,
        )


def _render_title_exclusion_editor() -> None:
    render_section_title("5. 제외 타이틀")
    st.caption(
        "분석·집계에서 빼고 싶은 타이틀을 선택하면 "
        "홈·예능·상세·목표달성 등 전체 섹션 결과에 반영됩니다."
    )
    local_db.init_schema()
    titles = local_db.list_uploaded_program_titles()
    if not titles:
        st.info("먼저 위에서 오리지널/닐슨/매출 데이터를 업로드해 주세요.")
        return

    options = [t["program_name"] for t in titles]
    current = local_db.list_excluded_titles()
    default = [t for t in current if t in options]

    selected = st.multiselect(
        "제외할 타이틀 선택",
        options=options,
        default=default,
        key="admin_exclude_titles",
    )

    if st.button("제외 목록 저장 · 전체 섹션 반영", type="primary", key="admin_exclude_save"):
        local_db.set_excluded_titles(selected)
        _clear_data_caches()
        if selected:
            st.success(f"{len(selected)}개 타이틀 제외 · 전체 섹션에 반영됨")
        else:
            st.success("제외 목록을 비웠습니다 · 전체 타이틀이 다시 포함됩니다")
        st.rerun()

    if current:
        st.caption(f"현재 제외 중: {', '.join(current)}")


def render() -> None:
    render_page_header("관리자 액션", "자료 업로드 → 자동 분류 → DB 적재 → 대시보드 반영")
    _render_storage_banner()

    with st.container(border=True):
        _render_auto_uploader()

    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container(border=True):
            _render_ratings_uploader()
    with col2:
        with st.container(border=True):
            _render_revenue_uploader()

    with st.container(border=True):
        _render_target_rating_editor()

    with st.container(border=True):
        _render_title_exclusion_editor()

    st.markdown("---")
    if st.button("← 홈으로 돌아가기", key="admin_back_home"):
        navigate_to("home")
