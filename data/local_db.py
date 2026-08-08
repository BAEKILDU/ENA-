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
  target_buzz REAL,
  target_revenue_million REAL,
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

CREATE TABLE IF NOT EXISTS program_buzz_inputs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  program_name TEXT NOT NULL UNIQUE,
  category TEXT,
  naver_index REAL,
  gooddata_index REAL,
  article_count REAL,
  community_score REAL,
  note TEXT,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def db_path() -> Path:
    """배포 환경(Streamlit Cloud)에서도 쓰기 가능한 DB 경로를 반환."""
    preferred = DB_PATH
    try:
        preferred.parent.mkdir(parents=True, exist_ok=True)
        probe = preferred.parent / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError:
        import tempfile

        fallback = Path(tempfile.gettempdir()) / "ena_plus" / "ena_plus.db"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return fallback


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
        _migrate_target_columns(conn)
        conn.commit()
    return path


def _migrate_target_columns(conn: sqlite3.Connection) -> None:
    """기존 DB에 목표 화제성·매출 컬럼 추가."""
    try:
        cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(program_target_ratings)")}
    except Exception:  # noqa: BLE001
        return
    if "target_buzz" not in cols:
        conn.execute("ALTER TABLE program_target_ratings ADD COLUMN target_buzz REAL")
    if "target_revenue_million" not in cols:
        conn.execute(
            "ALTER TABLE program_target_ratings ADD COLUMN target_revenue_million REAL"
        )


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
                INSERT INTO program_target_ratings (
                  program_name, category, target_rating, target_buzz,
                  target_revenue_million, note, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(program_name) DO UPDATE SET
                  category=excluded.category,
                  target_rating=excluded.target_rating,
                  target_buzz=excluded.target_buzz,
                  target_revenue_million=excluded.target_revenue_million,
                  note=excluded.note,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (
                    r.get("program_name"),
                    r.get("category"),
                    r.get("target_rating"),
                    r.get("target_buzz"),
                    r.get("target_revenue_million"),
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


def load_admin_targets_map() -> dict[str, dict[str, float]]:
    """프로그램명 → 목표 시청률/화제성/매출 맵."""
    init_schema()
    with connect() as conn:
        cur = conn.execute(
            """
            SELECT program_name, target_rating, target_buzz, target_revenue_million
            FROM program_target_ratings
            """
        )
        out: dict[str, dict[str, float]] = {}
        for row in cur.fetchall():
            entry: dict[str, float] = {}
            if row["target_rating"] is not None:
                entry["target_rating"] = float(row["target_rating"])
            if row["target_buzz"] is not None:
                entry["target_buzz"] = float(row["target_buzz"])
            if row["target_revenue_million"] is not None:
                entry["target_revenue_million"] = float(row["target_revenue_million"])
            if entry:
                out[str(row["program_name"])] = entry
        return out


def list_target_ratings() -> list[dict[str, Any]]:
    init_schema()
    with connect() as conn:
        cur = conn.execute(
            """
            SELECT program_name, category, target_rating, target_buzz,
                   target_revenue_million, note, updated_at
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


def match_admin_targets(
    program_name: str,
    targets: dict[str, dict[str, float]] | None = None,
) -> dict[str, float] | None:
    """프로그램명 느슨 매칭으로 관리자 목표(시청률·화제성·매출) 조회."""
    targets = targets if targets is not None else load_admin_targets_map()
    if not program_name or not targets:
        return None
    name = str(program_name).strip()
    if name in targets:
        return targets[name]
    norm = _norm_title(name)
    for k, v in targets.items():
        kk = _norm_title(k)
        if norm == kk or norm in kk or kk in norm:
            return v
    return None


def upsert_buzz_inputs(rows: list[dict[str, Any]]) -> int:
    init_schema()
    if not rows:
        return 0
    with connect() as conn:
        for r in rows:
            conn.execute(
                """
                INSERT INTO program_buzz_inputs (
                  program_name, category, naver_index, gooddata_index,
                  article_count, community_score, note, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(program_name) DO UPDATE SET
                  category=excluded.category,
                  naver_index=excluded.naver_index,
                  gooddata_index=excluded.gooddata_index,
                  article_count=excluded.article_count,
                  community_score=excluded.community_score,
                  note=excluded.note,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (
                    r.get("program_name"),
                    r.get("category"),
                    r.get("naver_index"),
                    r.get("gooddata_index"),
                    r.get("article_count"),
                    r.get("community_score"),
                    r.get("note"),
                ),
            )
        conn.commit()
    return len(rows)


def list_buzz_inputs() -> list[dict[str, Any]]:
    init_schema()
    with connect() as conn:
        cur = conn.execute(
            """
            SELECT program_name, category, naver_index, gooddata_index,
                   article_count, community_score, note, updated_at
            FROM program_buzz_inputs
            ORDER BY updated_at DESC, program_name
            """
        )
        return [dict(row) for row in cur.fetchall()]


def load_buzz_inputs_map() -> dict[str, dict[str, Any]]:
    """프로그램명 → 화제성 구성 지표."""
    out: dict[str, dict[str, Any]] = {}
    for row in list_buzz_inputs():
        name = str(row.get("program_name") or "").strip()
        if not name:
            continue
        out[name] = {
            "naver_index": row.get("naver_index"),
            "gooddata_index": row.get("gooddata_index"),
            "article_count": row.get("article_count"),
            "community_score": row.get("community_score"),
            "category": row.get("category"),
        }
    return out


def lookup_fundex_buzz_share(program_name: str) -> float | None:
    """로컬 fundex_buzz_rankings 에서 화제성 점유율 조회."""
    init_schema()
    name = str(program_name or "").strip()
    if not name:
        return None
    with connect() as conn:
        cur = conn.execute(
            """
            SELECT program_name, buzz_share FROM fundex_buzz_rankings
            WHERE buzz_share IS NOT NULL
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()
    if not rows:
        return None
    norm = _norm_title(name)
    for row in rows:
        kk = _norm_title(str(row["program_name"]))
        if norm == kk or norm in kk or kk in norm:
            try:
                return float(row["buzz_share"])
            except (TypeError, ValueError):
                return None
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
