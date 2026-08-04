"""로컬 SQLite 저장소 — Supabase 불가 시 스키마·업로드·조회 폴백.

관리자가 SQL Editor를 수동 실행할 필요 없이, 앱 시작/업로드 시 테이블을 자동 생성합니다.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "local" / "ena_plus.db"

BATCH_HINT = 500

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS nielsen_channel_rankings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_date TEXT NOT NULL,
  sheet_name TEXT NOT NULL,
  segment TEXT NOT NULL,
  rank INTEGER NOT NULL,
  channel_name TEXT NOT NULL,
  rating REAL,
  share REAL,
  reach REAL,
  watch_time TEXT,
  source_file TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ncr_date ON nielsen_channel_rankings(report_date);

CREATE TABLE IF NOT EXISTS nielsen_competition_ratings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_date TEXT NOT NULL,
  sheet_name TEXT NOT NULL,
  channel_name TEXT NOT NULL,
  start_time TEXT,
  end_time TEXT,
  program_name TEXT,
  is_daily_total INTEGER NOT NULL DEFAULT 0,
  target TEXT NOT NULL,
  rating REAL,
  share REAL,
  source_file TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ncomp_date ON nielsen_competition_ratings(report_date);

CREATE TABLE IF NOT EXISTS nielsen_target_details (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_date TEXT NOT NULL,
  sheet_name TEXT NOT NULL,
  channel_name TEXT NOT NULL,
  start_time TEXT,
  end_time TEXT,
  program_name TEXT,
  is_daily_total INTEGER NOT NULL DEFAULT 0,
  target TEXT NOT NULL,
  rating REAL,
  share REAL,
  reach REAL,
  watch_time TEXT,
  watch_time_ratio REAL,
  source_file TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ntd_date ON nielsen_target_details(report_date);

CREATE TABLE IF NOT EXISTS revenue_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_date TEXT NOT NULL,
  program_name TEXT NOT NULL,
  channel TEXT,
  category TEXT,
  revenue_million REAL,
  note TEXT,
  source_file TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rev_date ON revenue_records(report_date);

CREATE TABLE IF NOT EXISTS original_programs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_date TEXT NOT NULL,
  category TEXT NOT NULL,
  program_name TEXT NOT NULL,
  episodes INTEGER,
  rating_target_p2049 REAL,
  rating_household REAL,
  capex_million REAL,
  channel TEXT,
  note TEXT,
  source_file TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_op_date ON original_programs(report_date);

CREATE TABLE IF NOT EXISTS program_target_ratings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  program_name TEXT NOT NULL UNIQUE,
  category TEXT,
  target_rating REAL,
  note TEXT,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS program_exclusions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  program_name TEXT NOT NULL UNIQUE,
  note TEXT,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fundex_buzz_rankings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_week TEXT,
  rank INTEGER,
  program_name TEXT NOT NULL,
  program_name_en TEXT,
  category TEXT,
  channel TEXT,
  release_date TEXT,
  buzz_share REAL,
  source TEXT DEFAULT 'fundex',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def db_path() -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def connect() -> sqlite3.Connection:
    path = db_path()
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema() -> Path:
    """테이블 자동 생성. SQL Editor 수동 실행 대체."""
    path = db_path()
    with connect() as conn:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
    return path


def _serialize_value(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return v


def replace_and_upload_local(
    table: str,
    report_date: str,
    rows: list[dict[str, Any]],
    date_column: str = "report_date",
) -> int:
    init_schema()
    if not rows:
        return 0
    with connect() as conn:
        conn.execute(f"DELETE FROM {table} WHERE {date_column} = ?", (report_date,))
        cols = list(rows[0].keys())
        # drop auto id if present
        cols = [c for c in cols if c != "id"]
        placeholders = ",".join("?" for _ in cols)
        col_sql = ",".join(cols)
        sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})"
        payload = [tuple(_serialize_value(r.get(c)) for c in cols) for r in rows]
        conn.executemany(sql, payload)
        conn.commit()
    return len(rows)


def fetch_all_local(table: str, filters: dict[str, Any] | None = None) -> list[dict]:
    init_schema()
    clauses: list[str] = []
    params: list[Any] = []
    if filters:
        for col, val in filters.items():
            if val is None:
                continue
            if isinstance(val, (list, tuple, set)):
                qs = ",".join("?" for _ in val)
                clauses.append(f"{col} IN ({qs})")
                params.extend(list(val))
            else:
                clauses.append(f"{col} = ?")
                params.append(val)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        cur = conn.execute(f"SELECT * FROM {table}{where}", params)
        return [dict(row) for row in cur.fetchall()]


def fetch_df(table: str, filters: dict[str, Any] | None = None) -> pd.DataFrame:
    rows = fetch_all_local(table, filters)
    return pd.DataFrame(rows)


def upsert_target_ratings(rows: list[dict[str, Any]]) -> int:
    init_schema()
    if not rows:
        return 0
    with connect() as conn:
        for r in rows:
            conn.execute(
                """
                INSERT INTO program_target_ratings (program_name, category, target_rating, note, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(program_name) DO UPDATE SET
                  category=excluded.category,
                  target_rating=excluded.target_rating,
                  note=excluded.note,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (
                    r.get("program_name"),
                    r.get("category"),
                    r.get("target_rating"),
                    r.get("note"),
                ),
            )
        conn.commit()
    return len(rows)


def load_target_ratings_map() -> dict[str, float]:
    init_schema()
    with connect() as conn:
        cur = conn.execute(
            "SELECT program_name, target_rating FROM program_target_ratings WHERE target_rating IS NOT NULL"
        )
        out: dict[str, float] = {}
        for row in cur.fetchall():
            out[str(row["program_name"])] = float(row["target_rating"])
        return out


def list_target_ratings() -> list[dict[str, Any]]:
    init_schema()
    with connect() as conn:
        cur = conn.execute(
            """
            SELECT program_name, category, target_rating, note, updated_at
            FROM program_target_ratings
            ORDER BY updated_at DESC, program_name
            """
        )
        return [dict(row) for row in cur.fetchall()]


def match_target_rating(program_name: str, targets: dict[str, float] | None = None) -> float | None:
    """프로그램명 느슨 매칭으로 목표 시청률 조회."""
    targets = targets if targets is not None else load_target_ratings_map()
    if not program_name or not targets:
        return None
    name = str(program_name).strip()
    if name in targets:
        return targets[name]
    norm = name.replace(" ", "").upper().replace("나는SOLO", "나는솔로")
    for k, v in targets.items():
        kk = str(k).replace(" ", "").upper().replace("나는SOLO", "나는솔로")
        if norm == kk or norm in kk or kk in norm:
            return float(v)
    return None


def _norm_title(name: str) -> str:
    return str(name).replace(" ", "").upper().replace("나는SOLO", "나는솔로")


def list_excluded_titles() -> list[str]:
    init_schema()
    with connect() as conn:
        cur = conn.execute(
            "SELECT program_name FROM program_exclusions ORDER BY program_name"
        )
        return [str(row["program_name"]) for row in cur.fetchall()]


def set_excluded_titles(program_names: list[str]) -> int:
    """제외 타이틀 목록을 교체 저장."""
    init_schema()
    cleaned: list[str] = []
    seen: set[str] = set()
    for name in program_names:
        s = str(name).replace("\n", " ").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        cleaned.append(s)
    with connect() as conn:
        conn.execute("DELETE FROM program_exclusions")
        for name in cleaned:
            conn.execute(
                """
                INSERT INTO program_exclusions (program_name, note, updated_at)
                VALUES (?, 'admin', CURRENT_TIMESTAMP)
                """,
                (name,),
            )
        conn.commit()
    return len(cleaned)


def is_title_excluded(program_name: str, excluded: list[str] | None = None) -> bool:
    """프로그램명 느슨 매칭으로 제외 여부 확인."""
    excluded = excluded if excluded is not None else list_excluded_titles()
    if not program_name or not excluded:
        return False
    name = str(program_name).strip()
    if name in excluded:
        return True
    norm = _norm_title(name)
    for k in excluded:
        kk = _norm_title(k)
        if norm == kk or norm in kk or kk in norm:
            return True
    return False


def list_uploaded_program_titles() -> list[dict[str, str]]:
    """업로드된 프로그램 타이틀 목록 (관리자 목표 입력용)."""
    init_schema()
    found: dict[str, str] = {}

    def add(name: Any, category: Any = None) -> None:
        if name is None or (isinstance(name, float) and pd.isna(name)):
            return
        s = str(name).replace("\n", " ").strip()
        if not s or s.lower() in {"nan", "none", "계", "합계", "소계"}:
            return
        if s not in found:
            found[s] = str(category).strip() if category and str(category) not in {"None", "nan"} else ""

    # 오리지널 CSV
    csv_path = Path(__file__).resolve().parent / "processed" / "programs_summary.csv"
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            for _, r in df.iterrows():
                add(r.get("program_name"), r.get("category"))
        except Exception:  # noqa: BLE001
            pass

    with connect() as conn:
        for table, name_col, cat_col in (
            ("original_programs", "program_name", "category"),
            ("revenue_records", "program_name", "category"),
            ("nielsen_competition_ratings", "program_name", None),
        ):
            try:
                if cat_col:
                    cur = conn.execute(
                        f"SELECT DISTINCT {name_col}, {cat_col} FROM {table} WHERE {name_col} IS NOT NULL"
                    )
                    for row in cur.fetchall():
                        add(row[0], row[1])
                else:
                    cur = conn.execute(
                        f"""
                        SELECT DISTINCT {name_col} FROM {table}
                        WHERE {name_col} IS NOT NULL
                          AND channel_name IN ('ENA', 'ENA PLAY')
                        """
                    )
                    for row in cur.fetchall():
                        add(row[0], "예능")
            except Exception:  # noqa: BLE001
                continue

    return [{"program_name": k, "category": v} for k, v in sorted(found.items(), key=lambda x: x[0])]


def backend_label() -> str:
    return f"로컬 SQLite ({db_path().name})"
