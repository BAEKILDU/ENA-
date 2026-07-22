"""Supabase 업로드 공통 유틸."""

from __future__ import annotations

import os
from typing import Any, Iterable

from supabase import Client, create_client

from utils.config import get_supabase_anon_key, get_supabase_url

BATCH_SIZE = 500


def get_supabase_client() -> Client:
    url = get_supabase_url()
    key = get_supabase_anon_key()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_ANON_KEY 가 .env 에 없습니다.")
    return create_client(url, key)


def chunked(rows: list[dict], size: int = BATCH_SIZE) -> Iterable[list[dict]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def replace_and_upload(
    client: Client,
    table: str,
    report_date: str,
    rows: list[dict[str, Any]],
    date_column: str = "report_date",
) -> int:
    """동일 일자 데이터 삭제 후 insert. 업로드 행 수 반환."""
    if not rows:
        return 0
    client.table(table).delete().eq(date_column, report_date).execute()
    uploaded = 0
    for batch in chunked(rows):
        client.table(table).insert(batch).execute()
        uploaded += len(batch)
    return uploaded
