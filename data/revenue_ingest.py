"""매출 Excel 파싱 · Supabase 업로드."""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from data.supabase_upload import upload_table

# 헤더 별칭 → 표준 컬럼
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "report_date": ("report_date", "일자", "날짜", "기준일", "방송일", "date"),
    "program_name": (
        "program_name",
        "프로그램명",
        "프로그램",
        "타이틀",
        "콘텐츠",
        "title",
        "프로그램 명",
    ),
    "channel": ("channel", "채널", "방송채널"),
    "category": ("category", "구분", "카테고리", "매출구분", "유형"),
    "revenue_million": (
        "revenue_million",
        "매출(백만)",
        "매출백만",
        "매출액",
        "부가매출",
        "매출(억)",
        "매출억",
        "capex",
        "CAPEX",
        "제작비",
        "총제작비",
        "총 제작비",
        "예산",
        "수익",
        "금액",
        "매출",
    ),
    "note": ("note", "비고", "메모", "설명"),
}

SKIP_PROGRAMS = {"계", "검증", "합계", "소계", "총계", "nan", "none", "true", "false"}


def build_revenue_template_bytes() -> bytes:
    """업로드용 샘플 xlsx 바이트."""
    sample = pd.DataFrame(
        [
            {
                "일자": "2026-07-21",
                "프로그램명": "그대에게드림",
                "채널": "ENA",
                "구분": "광고",
                "매출(백만)": 120.5,
                "비고": "샘플",
            },
            {
                "일자": "2026-07-21",
                "프로그램명": "ENA 캠핑클럽",
                "채널": "ENA",
                "구분": "MD",
                "매출(백만)": 45.0,
                "비고": "",
            },
        ]
    )
    buf = io.BytesIO()
    sample.to_excel(buf, index=False, sheet_name="매출")
    return buf.getvalue()


def _normalize_header(value: Any) -> str:
    s = str(value or "").strip().lower()
    s = re.sub(r"\s+", "", s)
    s = s.replace("\n", "")
    return s


def _alias_keys() -> dict[str, set[str]]:
    return {
        std: {_normalize_header(a) for a in aliases}
        for std, aliases in COLUMN_ALIASES.items()
    }


def _match_header(norm: str, keys: set[str]) -> bool:
    if not norm or norm.startswith("unnamed") or norm.startswith("col_"):
        return False
    if norm in keys:
        return True
    # 부분일치: 짧은 키(금액/매출)는 오탐 방지를 위해 정확히 포함하되 시청률 등은 제외
    if "시청률" in norm or "목표대비" in norm or "전주" in norm:
        return False
    for k in sorted(keys, key=len, reverse=True):
        if len(k) < 2:
            continue
        if k in norm:
            return True
    return False


def _is_capex_sheet(sheet_name: str) -> bool:
    s = sheet_name.lower()
    return any(k in s for k in ("capex", "집행", "summary", "요약", "제작비", "매출"))


def _score_header_row(
    values: list[Any],
    *,
    sheet_name: str = "",
) -> tuple[int, dict[str, int]]:
    """행이 헤더일 가능성 점수와 표준컬럼→열인덱스 매핑."""
    aliases = _alias_keys()
    mapping: dict[str, int] = {}
    norms = [_normalize_header(v) for v in values]

    # CAPEX 시트에서는 '합계'도 매출 컬럼으로 허용
    revenue_keys = set(aliases["revenue_million"])
    if _is_capex_sheet(sheet_name):
        revenue_keys.add(_normalize_header("합계"))

    for col_idx, norm in enumerate(norms):
        if not norm:
            continue
        for std, keys in aliases.items():
            if std in mapping:
                continue
            use_keys = revenue_keys if std == "revenue_million" else keys
            if _match_header(norm, use_keys):
                mapping[std] = col_idx
                break

    score = len(mapping)
    if "program_name" in mapping:
        score += 3
    if "revenue_million" in mapping:
        score += 5
    # 재무 시트 가점
    if _is_capex_sheet(sheet_name):
        score += 2
    # 시청률 헤더만 있는 행 감점
    if any("시청률" in n for n in norms):
        score -= 4
    return score, mapping


def _map_columns(columns: list[Any], sheet_name: str = "") -> dict[str, str]:
    """원본 컬럼명 → 표준 키."""
    score, idx_map = _score_header_row(list(columns), sheet_name=sheet_name)
    if "program_name" not in idx_map or "revenue_million" not in idx_map:
        return {}
    mapping: dict[str, str] = {}
    for std, idx in idx_map.items():
        if 0 <= idx < len(columns):
            mapping[std] = columns[idx]
    return mapping


def _find_sheet_report_date(raw: pd.DataFrame, header_row: int) -> str | None:
    scan = raw.iloc[max(0, header_row - 5) : header_row + 1]
    for _, row in scan.iterrows():
        for v in row.tolist():
            if isinstance(v, datetime):
                return v.date().isoformat()
            if isinstance(v, date):
                return v.isoformat()
            d = _to_date_str(v)
            if d:
                return d
    return None


def _read_revenue_frame(path: Path) -> tuple[pd.DataFrame, dict[str, str], str | None]:
    """제목/공백 행을 건너뛰고 헤더 행을 자동 탐지. report_date 힌트 포함."""
    xl = pd.ExcelFile(path)
    try:
        first_sheet = xl.sheet_names[0]
        df0 = pd.read_excel(path, sheet_name=first_sheet)
        mapping0 = _map_columns(list(df0.columns), sheet_name=first_sheet)
        if mapping0:
            return df0, mapping0, None

        best: tuple[int, int, dict[str, int], pd.DataFrame, str] | None = None

        for sheet in xl.sheet_names:
            raw = pd.read_excel(path, sheet_name=sheet, header=None)
            if raw.empty:
                continue
            scan_limit = min(len(raw), 60)
            for r in range(scan_limit):
                values = raw.iloc[r].tolist()
                score, idx_map = _score_header_row(values, sheet_name=sheet)
                if "program_name" not in idx_map or "revenue_million" not in idx_map:
                    continue
                if best is None or score > best[0]:
                    best = (score, r, idx_map, raw, sheet)
    finally:
        xl.close()

    if best is None:
        raw = pd.read_excel(path, sheet_name=0, header=None)
        preview = []
        for r in range(min(12, len(raw))):
            cells = [str(v).replace("\n", " ") for v in raw.iloc[r].tolist()[:8] if pd.notna(v)]
            if cells:
                preview.append(f"row{r}:{cells}")
        raise ValueError(
            "필수 컬럼을 찾지 못했습니다. "
            "프로그램명/타이틀/콘텐츠 + 매출(또는 CAPEX/제작비) 컬럼이 필요합니다. "
            f"미리보기: {' | '.join(preview) if preview else list(df0.columns)}"
        )

    _, header_row, idx_map, raw, sheet_name = best
    hint_date = _find_sheet_report_date(raw, header_row)

    headers = []
    for i, v in enumerate(raw.iloc[header_row].tolist()):
        name = str(v).strip().replace("\n", " ") if pd.notna(v) else ""
        headers.append(name if name else f"col_{i}")

    seen: dict[str, int] = {}
    uniq_headers = []
    for h in headers:
        if h in seen:
            seen[h] += 1
            uniq_headers.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            uniq_headers.append(h)

    body = raw.iloc[header_row + 1 :].copy()
    body.columns = uniq_headers
    body = body.dropna(how="all").reset_index(drop=True)

    mapping = {std: uniq_headers[idx] for std, idx in idx_map.items() if idx < len(uniq_headers)}
    body.attrs["sheet_name"] = sheet_name
    return body, mapping, hint_date


def _to_date_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    s = str(value).strip()
    if not s:
        return None
    m = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    if re.fullmatch(r"\d{8}", s[:8] or ""):
        return date(int(s[0:4]), int(s[4:6]), int(s[6:8])).isoformat()
    try:
        parsed = pd.to_datetime(s, errors="coerce")
        if pd.notna(parsed):
            return parsed.date().isoformat()
    except Exception:  # noqa: BLE001
        pass
    return None


def _to_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", "").replace("백만", "").replace("원", "")
    if not s or s in {"-", "–", "—"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _clean_program(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return None
    s = str(value).replace("\n", " ").strip()
    if not s or s.lower() in SKIP_PROGRAMS:
        return None
    s = re.sub(r"\s+", " ", s)
    # 합계/소계 행, 숫자만 있는 셀 제외
    if re.search(r"(^|\s)(계|합계|소계|총계)$", s):
        return None
    if re.fullmatch(r"[\d,.]+", s):
        return None
    return s


def parse_revenue_excel(path: str | Path) -> tuple[str, list[dict]]:
    """매출/CAPEX 엑셀 파싱. (대표 report_date, rows)."""
    path = Path(path)
    df, mapping, hint_date = _read_revenue_frame(path)
    if df.empty:
        raise ValueError("매출 시트가 비어 있습니다.")

    if "program_name" not in mapping or "revenue_million" not in mapping:
        raise ValueError(
            "필수 컬럼을 찾지 못했습니다. "
            "프로그램명(또는 타이틀/콘텐츠)과 매출(또는 CAPEX/제작비) 컬럼이 필요합니다. "
            f"현재 컬럼: {list(df.columns)}"
        )

    # 파일명 날짜
    file_date = None
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", path.stem)
    if m:
        file_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    else:
        m = re.search(r"(?<!\d)(\d{2})(\d{2})(\d{2})(?!\d)", path.stem)
        if m:
            yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= mm <= 12 and 1 <= dd <= 31:
                file_date = date(2000 + yy, mm, dd).isoformat()

    rows: list[dict] = []
    dates: list[str] = []
    last_category: str | None = None

    for _, raw in df.iterrows():
        program = _clean_program(raw[mapping["program_name"]])
        if not program:
            # 구분만 있는 행은 카테고리 갱신
            if "category" in mapping and pd.notna(raw[mapping["category"]]):
                cat = str(raw[mapping["category"]]).strip()
                if cat and cat.lower() not in SKIP_PROGRAMS:
                    last_category = cat
            continue

        revenue = _to_float(raw[mapping["revenue_million"]])
        if revenue is None:
            continue

        category = None
        if "category" in mapping and pd.notna(raw[mapping["category"]]):
            category = str(raw[mapping["category"]]).strip() or None
            if category:
                last_category = category
        if not category:
            category = last_category

        report_date = None
        if "report_date" in mapping:
            report_date = _to_date_str(raw[mapping["report_date"]])
        if not report_date:
            report_date = hint_date or file_date or date.today().isoformat()

        dates.append(report_date)
        rows.append(
            {
                "report_date": report_date,
                "program_name": program,
                "channel": (
                    str(raw[mapping["channel"]]).replace("\n", " ").strip()
                    if "channel" in mapping and pd.notna(raw[mapping["channel"]])
                    else "ENA"
                ),
                "category": category,
                "revenue_million": revenue,
                "note": (
                    str(raw[mapping["note"]]).replace("\n", " ").strip()
                    if "note" in mapping and pd.notna(raw[mapping["note"]])
                    else None
                ),
                "source_file": path.name,
            }
        )

    if not rows:
        raise ValueError("업로드할 매출 행이 없습니다.")

    primary = max(set(dates), key=dates.count)
    return primary, rows


def upload_revenue_file(path: str | Path, *, dry_run: bool = False) -> dict[str, Any]:
    path = Path(path)
    report_date, rows = parse_revenue_excel(path)
    summary: dict[str, Any] = {
        "report_date": report_date,
        "source_file": path.name,
        "tables": {"revenue_records": len(rows)},
        "uploaded": {},
        "sample": rows[:3],
    }
    if dry_run:
        return summary

    backends: set[str] = set()
    warnings: list[str] = []
    total = 0
    by_date: dict[str, list[dict]] = {}
    for row in rows:
        by_date.setdefault(row["report_date"], []).append(row)
    for d, group in by_date.items():
        result = upload_table("revenue_records", d, group)
        total += int(result["uploaded"])
        backends.add(result.get("backend") or "none")
        if result.get("warning"):
            warnings.append(str(result["warning"]))
    summary["uploaded"]["revenue_records"] = total
    summary["backend"] = ",".join(sorted(backends))
    if warnings:
        summary["warnings"] = warnings
    return summary
