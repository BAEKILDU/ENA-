"""관리자 페이지 — 시청률/매출 Excel → Supabase 업로드."""

from __future__ import annotations

import gc
import tempfile
import time
from pathlib import Path

import streamlit as st

from data.nielsen_ingest import upload_nielsen_file
from data.revenue_ingest import build_revenue_template_bytes, upload_revenue_file
from utils.components import navigate_to, render_page_header, render_section_title


def _save_upload(uploaded, suffix: str) -> Path:
    raw = uploaded.getvalue()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(raw)
    tmp.close()
    return Path(tmp.name)


def _safe_unlink(path: Path) -> None:
    """Windows에서 Excel 핸들이 남아 있어도 업로드 흐름이 깨지지 않게 삭제."""
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


def _render_ratings_uploader() -> None:
    render_section_title("1. 시청률 데이터 업로드")
    st.caption(
        "닐슨 채널시청률 엑셀(`.xls` / `.xlsx`)을 업로드하세요. "
        "처리 시 `nielsen_channel_rankings` / `nielsen_competition_ratings` / "
        "`nielsen_target_details` 테이블에 적재됩니다."
    )
    file = st.file_uploader(
        "시청률 파일",
        type=["xls", "xlsx"],
        key="admin_ratings_file",
        help="예: 닐슨_채널시청률(260721).xls",
    )
    if st.button("시청률 처리 · Supabase 업로드", type="primary", key="admin_ratings_btn"):
        if file is None:
            st.error("시청률 파일을 선택해 주세요.")
            return
        suffix = Path(file.name).suffix.lower() or ".xlsx"
        path = _save_upload(file, suffix)
        try:
            with st.spinner("시청률 파싱 및 업로드 중…"):
                summary = upload_nielsen_file(path, original_name=file.name)
            _clear_data_caches()
            st.success(
                f"시청률 업로드 완료 · 분석일 {summary['report_date']} · "
                f"파일 {summary['source_file']}"
            )
            st.json(summary)
        except Exception as exc:  # noqa: BLE001
            st.error(f"시청률 업로드 실패: {exc}")
        finally:
            _safe_unlink(path)


def _render_revenue_uploader() -> None:
    render_section_title("2. 매출 데이터 업로드")
    st.caption(
        "매출/CAPEX 엑셀(`.xlsx` / `.xls`)을 업로드하세요. "
        "처리 시 `revenue_records` 테이블에 적재됩니다. "
        "지원: 일반 매출 템플릿, 오리지널 콘텐츠 관리(summary·CAPEX) 파일. "
        "일괄 적용: `python scripts/extract_and_apply_original_content.py` "
        "(CSV 생성 + revenue_records/original_programs 업로드)."
    )
    st.download_button(
        label="매출 템플릿 다운로드 (.xlsx)",
        data=build_revenue_template_bytes(),
        file_name="revenue_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="admin_revenue_template",
    )
    file = st.file_uploader(
        "매출 파일",
        type=["xls", "xlsx"],
        key="admin_revenue_file",
    )
    if st.button("매출 처리 · Supabase 업로드", type="primary", key="admin_revenue_btn"):
        if file is None:
            st.error("매출 파일을 선택해 주세요.")
            return
        suffix = Path(file.name).suffix.lower() or ".xlsx"
        path = _save_upload(file, suffix)
        try:
            with st.spinner("매출 파싱 및 업로드 중…"):
                summary = upload_revenue_file(path)
            _clear_data_caches()
            st.success(
                f"매출 업로드 완료 · 기준일 {summary['report_date']} · "
                f"파일 {summary['source_file']}"
            )
            st.json(summary)
        except Exception as exc:  # noqa: BLE001
            st.error(f"매출 업로드 실패: {exc}")
        finally:
            _safe_unlink(path)


def render() -> None:
    render_page_header("관리자", "시청률 · 매출 Excel 업로드 → Supabase 자동 적재")

    st.info(
        "최초 1회 Supabase SQL Editor에서 "
        "`sql/nielsen_channel_ratings.sql` 과 `sql/revenue_records.sql` 을 실행해 주세요."
    )

    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container(border=True):
            _render_ratings_uploader()
    with col2:
        with st.container(border=True):
            _render_revenue_uploader()

    st.markdown("---")
    if st.button("← 홈으로 돌아가기", key="admin_back_home"):
        navigate_to("home")
