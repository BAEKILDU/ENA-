"""Supabase 업로드 공통 유틸 + 연결 진단 + 로컬 폴백."""

from __future__ import annotations

import socket
from typing import Any, Iterable
from urllib.parse import urlparse

from supabase import Client, create_client

from data import local_db
from utils.config import get_supabase_anon_key, get_supabase_url

BATCH_SIZE = 500


def chunked(rows: list[dict], size: int = BATCH_SIZE) -> Iterable[list[dict]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def supabase_host() -> str | None:
    url = get_supabase_url()
    if not url:
        return None
    try:
        return urlparse(url).hostname
    except Exception:  # noqa: BLE001
        return None


def check_supabase_dns() -> tuple[bool, str]:
    """DNS 해석 가능 여부. (ok, message)"""
    host = supabase_host()
    if not host:
        return False, "SUPABASE_URL 이 비어 있습니다."
    try:
        socket.getaddrinfo(host, 443)
        return True, f"DNS OK · {host}"
    except socket.gaierror as exc:
        return False, (
            f"Supabase 호스트를 찾을 수 없습니다 ({host}). "
            f"프로젝트가 삭제·정지되었거나 URL이 잘못되었습니다. "
            f"Dashboard에서 새 Project URL을 .env 의 SUPABASE_URL 에 넣어 주세요. ({exc})"
        )


def supabase_reachable() -> bool:
    ok, _ = check_supabase_dns()
    return ok and bool(get_supabase_anon_key())


def get_supabase_client() -> Client:
    url = get_supabase_url()
    key = get_supabase_anon_key()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_ANON_KEY 가 .env 에 없습니다.")
    ok, msg = check_supabase_dns()
    if not ok:
        raise RuntimeError(msg)
    return create_client(url, key)


def replace_and_upload(
    client: Client | None,
    table: str,
    report_date: str,
    rows: list[dict[str, Any]],
    date_column: str = "report_date",
    *,
    allow_local_fallback: bool = True,
) -> int:
    """동일 일자 데이터 삭제 후 insert. Supabase 실패 시 로컬 SQLite 폴백."""
    if not rows:
        return 0

    if client is not None:
        try:
            client.table(table).delete().eq(date_column, report_date).execute()
            uploaded = 0
            for batch in chunked(rows):
                client.table(table).insert(batch).execute()
                uploaded += len(batch)
            return uploaded
        except Exception:
            if not allow_local_fallback:
                raise

    return local_db.replace_and_upload_local(table, report_date, rows, date_column=date_column)


def upload_table(
    table: str,
    report_date: str,
    rows: list[dict[str, Any]],
    date_column: str = "report_date",
) -> dict[str, Any]:
    """권장 업로드 엔트리. backend=supabase|local."""
    local_db.init_schema()
    if not rows:
        return {"uploaded": 0, "backend": "none"}

    if supabase_reachable():
        try:
            client = get_supabase_client()
            n = replace_and_upload(
                client, table, report_date, rows, date_column, allow_local_fallback=False
            )
            return {"uploaded": n, "backend": "supabase"}
        except Exception as exc:  # noqa: BLE001
            n = local_db.replace_and_upload_local(table, report_date, rows, date_column)
            return {"uploaded": n, "backend": "local", "warning": str(exc)}

    n = local_db.replace_and_upload_local(table, report_date, rows, date_column)
    ok, msg = check_supabase_dns()
    return {
        "uploaded": n,
        "backend": "local",
        "warning": None if ok else msg,
    }


def storage_status() -> dict[str, Any]:
    local_db.init_schema()
    dns_ok, dns_msg = check_supabase_dns()
    return {
        "supabase_configured": bool(get_supabase_url() and get_supabase_anon_key()),
        "supabase_dns_ok": dns_ok,
        "supabase_message": dns_msg,
        "active_backend": "supabase" if dns_ok else "local",
        "local_db": str(local_db.db_path()),
        "schema_ready": True,
    }


def _target_row_for_supabase(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "program_name": row.get("program_name"),
        "category": row.get("category"),
        "target_rating": row.get("target_rating"),
        "target_buzz": row.get("target_buzz"),
        "target_revenue_million": row.get("target_revenue_million"),
        "note": row.get("note") or "admin",
    }


def push_program_targets(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """관리자 목표(시청률·화제성·매출)를 Supabase에 upsert. 실패 시 로컬만 유지."""
    local_db.init_schema()
    if not rows:
        return {"uploaded": 0, "backend": "none"}

    payload = [_target_row_for_supabase(r) for r in rows if r.get("program_name")]
    if not payload:
        return {"uploaded": 0, "backend": "none"}

    if not supabase_reachable():
        ok, msg = check_supabase_dns()
        return {
            "uploaded": 0,
            "backend": "local",
            "warning": None if ok else msg,
        }

    try:
        client = get_supabase_client()
        client.table("program_target_ratings").upsert(
            payload,
            on_conflict="program_name",
        ).execute()
        return {"uploaded": len(payload), "backend": "supabase"}
    except Exception as exc:  # noqa: BLE001
        return {"uploaded": 0, "backend": "local", "warning": str(exc)}


def pull_program_targets_into_local() -> dict[str, Any]:
    """Supabase 목표값을 로컬 DB에 동기화 (앱 재실행 시 동일 데이터 적용)."""
    local_db.init_schema()
    if not supabase_reachable():
        return {"pulled": 0, "backend": "local"}

    try:
        client = get_supabase_client()
        res = (
            client.table("program_target_ratings")
            .select(
                "program_name,category,target_rating,target_buzz,target_revenue_million,note"
            )
            .execute()
        )
        rows = res.data or []
        if not rows:
            local_rows = local_db.list_target_ratings()
            if local_rows:
                pushed = push_program_targets(local_rows)
                return {
                    "pulled": 0,
                    "pushed": pushed.get("uploaded", 0),
                    "backend": pushed.get("backend", "supabase"),
                    "warning": pushed.get("warning"),
                }
            return {"pulled": 0, "backend": "supabase"}
        local_db.upsert_target_ratings(
            [
                {
                    "program_name": r.get("program_name"),
                    "category": r.get("category"),
                    "target_rating": r.get("target_rating"),
                    "target_buzz": r.get("target_buzz"),
                    "target_revenue_million": r.get("target_revenue_million"),
                    "note": r.get("note") or "supabase",
                }
                for r in rows
                if r.get("program_name")
            ]
        )
        return {"pulled": len(rows), "backend": "supabase"}
    except Exception as exc:  # noqa: BLE001
        return {"pulled": 0, "backend": "local", "warning": str(exc)}


def _buzz_row_for_supabase(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "program_name": row.get("program_name"),
        "category": row.get("category"),
        "naver_index": row.get("naver_index"),
        "gooddata_index": row.get("gooddata_index"),
        "article_count": row.get("article_count"),
        "community_score": row.get("community_score"),
        "note": row.get("note") or "admin",
    }


def push_program_buzz_inputs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """화제성 구성 지표를 Supabase에 upsert."""
    local_db.init_schema()
    if not rows:
        return {"uploaded": 0, "backend": "none"}

    payload = [_buzz_row_for_supabase(r) for r in rows if r.get("program_name")]
    if not payload:
        return {"uploaded": 0, "backend": "none"}

    if not supabase_reachable():
        ok, msg = check_supabase_dns()
        return {
            "uploaded": 0,
            "backend": "local",
            "warning": None if ok else msg,
        }

    try:
        client = get_supabase_client()
        client.table("program_buzz_inputs").upsert(
            payload,
            on_conflict="program_name",
        ).execute()
        return {"uploaded": len(payload), "backend": "supabase"}
    except Exception as exc:  # noqa: BLE001
        return {"uploaded": 0, "backend": "local", "warning": str(exc)}


def pull_program_buzz_inputs_into_local() -> dict[str, Any]:
    """Supabase 화제성 지표를 로컬 DB에 동기화."""
    local_db.init_schema()
    if not supabase_reachable():
        return {"pulled": 0, "backend": "local"}

    try:
        client = get_supabase_client()
        res = (
            client.table("program_buzz_inputs")
            .select(
                "program_name,category,naver_index,gooddata_index,"
                "article_count,community_score,note"
            )
            .execute()
        )
        rows = res.data or []
        if not rows:
            local_rows = local_db.list_buzz_inputs()
            if local_rows:
                pushed = push_program_buzz_inputs(local_rows)
                return {
                    "pulled": 0,
                    "pushed": pushed.get("uploaded", 0),
                    "backend": pushed.get("backend", "supabase"),
                    "warning": pushed.get("warning"),
                }
            return {"pulled": 0, "backend": "supabase"}
        local_db.upsert_buzz_inputs(
            [
                {
                    "program_name": r.get("program_name"),
                    "category": r.get("category"),
                    "naver_index": r.get("naver_index"),
                    "gooddata_index": r.get("gooddata_index"),
                    "article_count": r.get("article_count"),
                    "community_score": r.get("community_score"),
                    "note": r.get("note") or "supabase",
                }
                for r in rows
                if r.get("program_name")
            ]
        )
        return {"pulled": len(rows), "backend": "supabase"}
    except Exception as exc:  # noqa: BLE001
        return {"pulled": 0, "backend": "local", "warning": str(exc)}


def push_program_exclusions(program_names: list[str] | None = None) -> dict[str, Any]:
    """제외 타이틀을 Supabase에 동기화(전체 교체)."""
    local_db.init_schema()
    names = (
        list(program_names)
        if program_names is not None
        else local_db.list_excluded_titles()
    )
    cleaned: list[str] = []
    seen: set[str] = set()
    for name in names:
        s = str(name).replace("\n", " ").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        cleaned.append(s)

    if not supabase_reachable():
        ok, msg = check_supabase_dns()
        return {
            "uploaded": 0,
            "backend": "local",
            "warning": None if ok else msg,
        }

    try:
        client = get_supabase_client()
        # 전체 교체: 원격 삭제 후 현재 목록 upsert
        existing = (
            client.table("program_exclusions").select("program_name").execute().data or []
        )
        for row in existing:
            pname = row.get("program_name")
            if pname:
                client.table("program_exclusions").delete().eq("program_name", pname).execute()
        if cleaned:
            payload = [
                {"program_name": n, "note": "admin"}
                for n in cleaned
            ]
            client.table("program_exclusions").upsert(
                payload,
                on_conflict="program_name",
            ).execute()
        return {"uploaded": len(cleaned), "backend": "supabase"}
    except Exception as exc:  # noqa: BLE001
        return {"uploaded": 0, "backend": "local", "warning": str(exc)}


def pull_program_exclusions_into_local() -> dict[str, Any]:
    """Supabase 제외 타이틀을 로컬 DB에 동기화."""
    local_db.init_schema()
    if not supabase_reachable():
        return {"pulled": 0, "backend": "local"}

    try:
        client = get_supabase_client()
        res = client.table("program_exclusions").select("program_name").execute()
        rows = res.data or []
        names = [
            str(r.get("program_name")).strip()
            for r in rows
            if r.get("program_name")
        ]
        local_names = local_db.list_excluded_titles()
        if names:
            local_db.set_excluded_titles(names)
            return {"pulled": len(names), "backend": "supabase"}
        # 원격이 비어 있고 로컬만 있으면 원격으로 보존(초기화 방지)
        if local_names:
            pushed = push_program_exclusions(local_names)
            return {
                "pulled": 0,
                "pushed": pushed.get("uploaded", 0),
                "backend": pushed.get("backend", "supabase"),
                "warning": pushed.get("warning"),
            }
        return {"pulled": 0, "backend": "supabase"}
    except Exception as exc:  # noqa: BLE001
        return {"pulled": 0, "backend": "local", "warning": str(exc)}


def sync_admin_metrics_from_supabase() -> dict[str, Any]:
    """앱 시작 시 목표·화제성·제외 타이틀을 Supabase에서 일괄 pull.

    개별 테이블 부재/권한 오류는 전체 기동을 막지 않도록 삼킵니다.
    """
    out: dict[str, Any] = {}
    for key, fn in (
        ("targets", pull_program_targets_into_local),
        ("buzz", pull_program_buzz_inputs_into_local),
        ("exclusions", pull_program_exclusions_into_local),
    ):
        try:
            out[key] = fn()
        except Exception as exc:  # noqa: BLE001
            out[key] = {"pulled": 0, "backend": "local", "warning": str(exc)}
    return out


def push_all_local_admin_metrics() -> dict[str, Any]:
    """로컬에 저장된 목표·화제성·제외 타이틀을 Supabase로 일괄 push."""
    local_db.init_schema()
    t_rows = local_db.list_target_ratings()
    b_rows = local_db.list_buzz_inputs()
    return {
        "targets": push_program_targets(t_rows),
        "buzz": push_program_buzz_inputs(b_rows),
        "exclusions": push_program_exclusions(),
    }
