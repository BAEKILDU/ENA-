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
