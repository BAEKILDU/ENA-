"""닐슨 채널시청률 Excel 파싱 · Supabase 업로드."""

from __future__ import annotations

import re
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import pandas as pd

from data.supabase_upload import upload_table

RANKING_SHEETS = {"유료방송가입가구", "개인"}
COMPETITION_SUFFIX = "경쟁채널시청률"
TARGET_SUFFIX = "타깃상세"


# ── helpers ───────────────────────────────────────────────────────────────────

def _clean_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str):
        s = value.strip()
        return s or None
    return str(value).strip() or None


def _to_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", "")
    if not s or s.lower() in {"nan", "none", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_time_str(value: Any) -> str | None:
    """시청시간/방송시간을 text(HH:MM:SS)로. 25시 초과·문자열 모두 허용."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")
    if isinstance(value, datetime):
        return value.strftime("%H:%M:%S")
    if isinstance(value, str):
        s = value.strip()
        return s or None
    # Excel serial time as fraction of day
    if isinstance(value, (int, float)):
        total = int(round(float(value) * 24 * 3600))
        h, rem = divmod(total, 3600)
        m, sec = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return str(value)


def _parse_report_date(df: pd.DataFrame, filename: str) -> date:
    """시트 메타 또는 파일명에서 분석일 추출."""
    # 시트 상단 여러 셀 스캔
    for i in range(min(12, len(df))):
        for j in range(min(10, df.shape[1])):
            cell = _clean_str(df.iat[i, j])
            if not cell:
                continue
            m = re.search(r"(\d{4})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})", cell)
            if m:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            m = re.search(r"(\d{4})(\d{2})(\d{2})", cell)
            if m:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                    return date(y, mo, d)

    stem = Path(filename).stem
    # YYMMDD / YYYYMMDD (파일명 어디에든)
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", stem)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(?<!\d)(\d{2})(\d{2})(\d{2})(?!\d)", stem)
    if m:
        yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mm <= 12 and 1 <= dd <= 31:
            return date(2000 + yy, mm, dd)

    raise ValueError(f"분석일을 찾을 수 없습니다: {filename}")


def _segment_label(raw: Any) -> str | None:
    s = _clean_str(raw)
    if not s:
        return None
    return s.lstrip("-").strip()


def _is_channel_header_row(row: pd.Series) -> bool:
    """경쟁/타깃 시트에서 채널명 헤더 행 판별."""
    v0 = row.iloc[0]
    if not isinstance(v0, str):
        return False
    s = v0.strip()
    if not s:
        return False
    # 시간/메타/컬럼명/날짜 제외
    if re.match(r"^\d{1,2}:\d{2}", s):
        return False
    if re.match(r"^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}", s):
        return False
    if s in {"시작시간", "끝시간", "프로그램명", "하루전체"}:
        return False
    if s.startswith(("닐슨", "■", "-", "분석")):
        return False
    if "시청률" in s or "제공" in s or "요일" in s:
        return False
    # 채널명만 있는 행: 값 개수가 적고 모두 문자열
    non_null = [x for x in row.tolist() if pd.notna(x)]
    if not non_null:
        return False
    return all(isinstance(x, str) for x in non_null) and len(non_null) <= 25


# ── parsers ───────────────────────────────────────────────────────────────────

def parse_ranking_sheet(
    df: pd.DataFrame,
    sheet_name: str,
    report_date: date,
    source_file: str,
) -> list[dict]:
    """4개 세그먼트가 가로로 나란히 있는 순위 시트."""
    header_row = 7
    data_start = 9
    block_starts = [0, 7, 14, 21]
    segments = [_segment_label(df.iat[header_row, start + 1]) for start in block_starts]

    rows: list[dict] = []
    for start, segment in zip(block_starts, segments):
        if not segment:
            continue
        for i in range(data_start, len(df)):
            rank_val = df.iat[i, start]
            channel = _clean_str(df.iat[i, start + 1])
            if channel is None:
                continue
            rank = _to_float(rank_val)
            if rank is None:
                continue
            rows.append(
                {
                    "report_date": report_date.isoformat(),
                    "sheet_name": sheet_name,
                    "segment": segment,
                    "rank": int(rank),
                    "channel_name": channel,
                    "rating": _to_float(df.iat[i, start + 2]),
                    "share": _to_float(df.iat[i, start + 3]),
                    "reach": _to_float(df.iat[i, start + 4]),
                    "watch_time": _to_time_str(df.iat[i, start + 5]),
                    "source_file": source_file,
                }
            )
    return rows


def parse_competition_sheet(
    df: pd.DataFrame,
    sheet_name: str,
    report_date: date,
    source_file: str,
) -> list[dict]:
    """좌·우 채널 블록이 세로로 반복되는 경쟁채널 시청률 시트."""
    # 타깃 라벨은 첫 데이터 블록의 row 5 기준 (시트마다 동일 패턴)
    left_targets = [
        _clean_str(df.iat[5, 3]),
        _clean_str(df.iat[5, 4]),
        _clean_str(df.iat[5, 5]),
    ]
    right_targets = [
        _clean_str(df.iat[5, 13]),
        _clean_str(df.iat[5, 14]),
        _clean_str(df.iat[5, 15]),
    ]

    rows: list[dict] = []
    i = 0
    while i < len(df):
        row = df.iloc[i]
        if not _is_channel_header_row(row):
            i += 1
            continue

        left_channel = _clean_str(row.iloc[0])
        right_channel = _clean_str(row.iloc[10]) if len(row) > 10 else None

        # 다음 행이 컬럼 헤더(시작시간), 그 다음이 타깃 헤더
        i += 1
        if i >= len(df):
            break
        # skip metric header row if present
        if _clean_str(df.iat[i, 0]) == "시작시간":
            i += 1
        if i < len(df) and _clean_str(df.iat[i, 3]) in left_targets:
            i += 1

        while i < len(df):
            if _is_channel_header_row(df.iloc[i]):
                break

            left_start = _to_time_str(df.iat[i, 0])
            left_program = _clean_str(df.iat[i, 2])
            is_daily = left_start is None and left_program is None and _clean_str(df.iat[i, 0]) == "하루전체"
            if _clean_str(df.iat[i, 0]) == "하루전체":
                is_daily = True
                left_program = "하루전체"

            if left_channel and (left_program or left_start or is_daily):
                for t_idx, target in enumerate(left_targets):
                    if not target:
                        continue
                    rows.append(
                        {
                            "report_date": report_date.isoformat(),
                            "sheet_name": sheet_name,
                            "channel_name": left_channel,
                            "start_time": None if is_daily else left_start,
                            "end_time": None if is_daily else _to_time_str(df.iat[i, 1]),
                            "program_name": left_program,
                            "is_daily_total": is_daily,
                            "target": target,
                            "rating": _to_float(df.iat[i, 3 + t_idx]),
                            "share": _to_float(df.iat[i, 6 + t_idx]),
                            "source_file": source_file,
                        }
                    )

            right_start = _to_time_str(df.iat[i, 10]) if df.shape[1] > 10 else None
            right_program = _clean_str(df.iat[i, 12]) if df.shape[1] > 12 else None
            right_daily = _clean_str(df.iat[i, 10]) == "하루전체"
            if right_daily:
                right_program = "하루전체"

            if right_channel and (right_program or right_start or right_daily):
                for t_idx, target in enumerate(right_targets):
                    if not target:
                        continue
                    rows.append(
                        {
                            "report_date": report_date.isoformat(),
                            "sheet_name": sheet_name,
                            "channel_name": right_channel,
                            "start_time": None if right_daily else right_start,
                            "end_time": None if right_daily else _to_time_str(df.iat[i, 11]),
                            "program_name": right_program,
                            "is_daily_total": right_daily,
                            "target": target,
                            "rating": _to_float(df.iat[i, 13 + t_idx]),
                            "share": _to_float(df.iat[i, 16 + t_idx]),
                            "source_file": source_file,
                        }
                    )

            i += 1

    return rows


def parse_target_detail_sheet(
    df: pd.DataFrame,
    sheet_name: str,
    report_date: date,
    source_file: str,
) -> list[dict]:
    """채널별 타깃 상세 — 타깃을 long format으로 펼침."""
    rows: list[dict] = []
    i = 0
    while i < len(df):
        row = df.iloc[i]
        if not _is_channel_header_row(row):
            i += 1
            continue

        channel_name = _clean_str(row.iloc[0])
        # 타깃 라벨: col 3부터 5열 간격 (중간 merged 라벨 제외)
        targets: list[tuple[int, str]] = []
        for col in range(3, df.shape[1], 5):
            label = _clean_str(row.iloc[col])
            if label:
                targets.append((col, label))

        i += 1
        # skip column header row (시작시간/시청률/...)
        if i < len(df) and _clean_str(df.iat[i, 0]) == "시작시간":
            i += 1

        while i < len(df):
            if _is_channel_header_row(df.iloc[i]):
                break

            start_raw = _clean_str(df.iat[i, 0])
            if not start_raw:
                i += 1
                continue

            is_daily = start_raw == "하루전체"
            program = "하루전체" if is_daily else _clean_str(df.iat[i, 2])
            start_time = None if is_daily else _to_time_str(df.iat[i, 0])
            end_time = None if is_daily else _to_time_str(df.iat[i, 1])

            for col, target in targets:
                # 일부 타깃 라벨이 잘못 밀린 열(예: '남 60대+')은 메트릭 시작이 아닐 수 있음
                # 시청률 열이 숫자/문자숫자인지만 검사
                rating = _to_float(df.iat[i, col] if col < df.shape[1] else None)
                share = _to_float(df.iat[i, col + 1] if col + 1 < df.shape[1] else None)
                reach = _to_float(df.iat[i, col + 2] if col + 2 < df.shape[1] else None)
                watch_time = _to_time_str(df.iat[i, col + 3] if col + 3 < df.shape[1] else None)
                watch_ratio = _to_float(df.iat[i, col + 4] if col + 4 < df.shape[1] else None)

                # 타깃 헤더 오검출(중간 라벨) 스킵: 메트릭이 전부 None이면 제외
                if all(v is None for v in (rating, share, reach, watch_time, watch_ratio)):
                    continue

                rows.append(
                    {
                        "report_date": report_date.isoformat(),
                        "sheet_name": sheet_name,
                        "channel_name": channel_name,
                        "start_time": start_time,
                        "end_time": end_time,
                        "program_name": program,
                        "is_daily_total": is_daily,
                        "target": target,
                        "rating": rating,
                        "share": share,
                        "reach": reach,
                        "watch_time": watch_time,
                        "watch_time_ratio": watch_ratio,
                        "source_file": source_file,
                    }
                )
            i += 1

    return rows


def parse_workbook(
    path: Path,
    *,
    original_name: str | None = None,
) -> tuple[str, dict[str, list[dict]]]:
    xl = pd.ExcelFile(path)
    source_file = original_name or path.name
    report_date: date | None = None
    date_error: Exception | None = None

    rankings: list[dict] = []
    competitions: list[dict] = []
    targets: list[dict] = []

    try:
        for sheet_name in xl.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet_name, header=None)
            if report_date is None:
                try:
                    report_date = _parse_report_date(df, source_file)
                except ValueError as exc:
                    date_error = exc

            if report_date is None:
                continue

            if sheet_name in RANKING_SHEETS:
                rankings.extend(parse_ranking_sheet(df, sheet_name, report_date, source_file))
            elif sheet_name.endswith(COMPETITION_SUFFIX):
                competitions.extend(
                    parse_competition_sheet(df, sheet_name, report_date, source_file)
                )
            elif sheet_name.endswith(TARGET_SUFFIX):
                targets.extend(
                    parse_target_detail_sheet(df, sheet_name, report_date, source_file)
                )
    finally:
        xl.close()

    if report_date is None:
        raise ValueError(
            str(date_error) if date_error else f"분석일을 찾을 수 없습니다: {source_file}"
        )

    return report_date.isoformat(), {
        "nielsen_channel_rankings": rankings,
        "nielsen_competition_ratings": competitions,
        "nielsen_target_details": targets,
    }


def upload_nielsen_file(
    path: str | Path,
    *,
    dry_run: bool = False,
    original_name: str | None = None,
) -> dict[str, Any]:
    """엑셀 파싱 후 Supabase 업로드. 요약 dict 반환."""
    path = Path(path)
    display_name = original_name or path.name
    report_date, tables = parse_workbook(path, original_name=display_name)
    summary: dict[str, Any] = {
        "report_date": report_date,
        "source_file": display_name,
        "tables": {name: len(rows) for name, rows in tables.items()},
        "uploaded": {},
    }
    if dry_run:
        return summary

    backends: set[str] = set()
    warnings: list[str] = []
    for table, rows in tables.items():
        result = upload_table(table, report_date, rows)
        summary["uploaded"][table] = result["uploaded"]
        backends.add(result.get("backend") or "none")
        if result.get("warning"):
            warnings.append(str(result["warning"]))
    summary["backend"] = ",".join(sorted(backends))
    if warnings:
        summary["warnings"] = warnings
    return summary
