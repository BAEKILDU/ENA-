"""오리지널 콘텐츠 관리 엑셀 → CSV 분류 + Supabase 업로드."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROCESSED = Path(__file__).resolve().parent / "processed"
SKIP_EXACT = {
    "계",
    "검증",
    "합계",
    "소계",
    "총계",
    "average",
    "all",
    "nan",
    "none",
    "콘텐츠",
    "타이틀",
    "구분",
    "total",
    "현재",
    "담당 pd",
    "no.",
}


def _clean_title(v: Any) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (datetime, date)):
        return None
    if isinstance(v, (int, float)):
        return None
    s = re.sub(r"\s+", " ", str(v).replace("\n", " ")).strip()
    if not s or s.lower() in SKIP_EXACT:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return None
    if s.startswith("촌장") or s in {"촌장 외", "주1) 본방 GRP 기준"}:
        return None
    # 합계 행만 제외 (나솔사계 등은 유지)
    if re.fullmatch(r"(예능|드라마)?\s*(계|합계|소계|총계)", s):
        return None
    if re.fullmatch(r"[\d,.]+", s):
        return None
    # 슬롯 괄호 제거: "나는 솔로 (수요일 22:30~)" → "나는 솔로"
    base = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    return base or s


def _parse_slot(raw_title: str) -> tuple[str | None, str | None, str | None]:
    """타이틀 문자열에서 (slot, day, time) 추출."""
    m = re.search(r"\(([^)]*)\)\s*$", str(raw_title or ""))
    if not m:
        return None, None, None
    inner = m.group(1)
    day = None
    for d in ("월", "화", "수", "목", "금", "토", "일"):
        if d in inner:
            day = d
            break
    tm = re.search(r"(\d{1,2}:\d{2})", inner)
    time = tm.group(1) if tm else None
    slot = f"{day} {time}" if day and time else inner.split("/")[0].strip()
    return slot, day, time


def _num(v: Any) -> float | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _rating(v: Any) -> float | None:
    """시청률은 소수 3자리로 통일."""
    n = _num(v)
    return round(n, 3) if n is not None else None


def _money(v: Any) -> float | None:
    """매출/CAPEX는 소수 1자리로 통일."""
    n = _num(v)
    return round(n, 1) if n is not None else None


def _date_iso(v: Any) -> str | None:
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        parsed = pd.to_datetime(v, errors="coerce")
        if pd.notna(parsed):
            return parsed.date().isoformat()
    except Exception:  # noqa: BLE001
        pass
    return None


def _norm_key(name: str) -> str:
    s = name.replace(" ", "").upper()
    s = s.replace("나는SOLO", "나는솔로").replace("나.솔.사.계", "나솔사계")
    s = s.replace("그대애게", "그대에게")
    return s


def detect_workbook_kind(path: Path, original_name: str | None = None) -> str:
    """original_content | nielsen | revenue_simple"""
    name = (original_name or path.name).lower()
    if "닐슨" in name or "nielsen" in name or "채널시청률" in name:
        return "nielsen"
    try:
        sheets = set(pd.ExcelFile(path).sheet_names)
    except Exception:  # noqa: BLE001
        return "revenue_simple"
    if "● summary" in sheets or any("오리지널" in s for s in sheets) or any("CAPEX" in s for s in sheets):
        return "original_content"
    if any("경쟁채널시청률" in s for s in sheets) and any("타깃상세" in s for s in sheets):
        return "nielsen"
    return "revenue_simple"


def extract_report_date(path: Path) -> str:
    try:
        raw = pd.read_excel(path, sheet_name="● summary", header=None)
        for r in range(min(6, len(raw))):
            for v in raw.iloc[r].tolist():
                d = _date_iso(v)
                if d and d.startswith("202"):
                    return d
    except Exception:  # noqa: BLE001
        pass
    md = re.search(r"~(\d{2})(\d{2})", path.stem)
    if md:
        return date(2026, int(md.group(1)), int(md.group(2))).isoformat()
    return date.today().isoformat()


def _extract_summary(path: Path, report_date: str) -> list[dict]:
    raw = pd.read_excel(path, sheet_name="● summary", header=None)
    rows: list[dict] = []
    category: str | None = None
    for r in range(len(raw)):
        vals = raw.iloc[r].tolist()
        cat = str(vals[1]).strip() if len(vals) > 1 and pd.notna(vals[1]) else ""
        if cat in {"드라마", "예능"}:
            category = cat
        title = _clean_title(vals[2]) if len(vals) > 2 else None
        if not title or not category:
            continue
        capex = _money(vals[6]) if len(vals) > 6 else None
        rating = _rating(vals[4]) if len(vals) > 4 else None
        if capex is None and rating is None:
            continue
        rows.append(
            {
                "report_date": report_date,
                "category": category,
                "program_name": title.replace("그대애게", "그대에게"),
                "episodes": int(_num(vals[3]) or 0) or None,
                "rating_target_p2049": rating,
                "rating_household": _rating(vals[5]) if len(vals) > 5 else None,
                "capex_million": capex,
                "channel": "ENA",
                "note": _clean_title(vals[7]) if len(vals) > 7 else None,
                "slot": None,
                "day": None,
                "time": None,
                "source_file": path.name,
                "data_area": "variety" if category == "예능" else "drama",
            }
        )
    return rows


def _extract_drama_compare(path: Path, report_date: str) -> list[dict]:
    sheet = "◎ '26년 오리지널 드라마 타이틀 별 비교"
    if sheet not in pd.ExcelFile(path).sheet_names:
        return []
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    rows: list[dict] = []
    for r in range(len(raw)):
        vals = raw.iloc[r].tolist()
        # No. 열이 숫자인 데이터 행만
        no = _num(vals[1]) if len(vals) > 1 else None
        if no is None:
            continue
        title = _clean_title(vals[3]) if len(vals) > 3 else None
        if not title:
            continue
        episodes = int(_num(vals[4]) or 0) or None
        rating = _rating(vals[6]) if len(vals) > 6 else None
        capex = _money(vals[11]) if len(vals) > 11 else None
        if not episodes and not rating and not capex:
            continue
        rows.append(
            {
                "report_date": report_date,
                "category": "드라마",
                "program_name": title.replace("그대애게", "그대에게"),
                "pd": _clean_title(vals[2]) if len(vals) > 2 else None,
                "episodes": episodes,
                "rating_target_p2049": rating,
                "grp": _rating(vals[7]) if len(vals) > 7 else None,
                "rank": int(_num(vals[10]) or 0) or None if len(vals) > 10 else None,
                "capex_million": capex,
                "channel": "ENA",
                "source_file": path.name,
                "data_area": "drama",
            }
        )
    return rows


def _extract_variety_compare(path: Path, report_date: str) -> list[dict]:
    sheet = "◎ '26년 오리지널 예능 타이틀 별 비교"
    if sheet not in pd.ExcelFile(path).sheet_names:
        return []
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    rows: list[dict] = []
    for r in range(len(raw)):
        vals = raw.iloc[r].tolist()
        no = _num(vals[1]) if len(vals) > 1 else None
        if no is None:
            continue
        title = _clean_title(vals[4]) if len(vals) > 4 else None
        if not title:
            continue
        episodes = int(_num(vals[5]) or 0) or None
        rating = _rating(vals[7]) if len(vals) > 7 else None
        if not episodes and not rating:
            continue
        rows.append(
            {
                "report_date": report_date,
                "category": "예능",
                "program_name": title,
                "pd": _clean_title(vals[2]) if len(vals) > 2 else None,
                "episodes": episodes,
                "rating_target_p2049": rating,
                "grp": _rating(vals[8]) if len(vals) > 8 else None,
                "rank": int(_num(vals[11]) or 0) or None if len(vals) > 11 else None,
                "capex_million": None,
                "channel": "ENA",
                "source_file": path.name,
                "data_area": "variety",
            }
        )
    return rows


def _extract_variety_slots(path: Path) -> dict[str, dict]:
    sheet = "◎ '26년 오리지널 예능"
    if sheet not in pd.ExcelFile(path).sheet_names:
        return {}
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    out: dict[str, dict] = {}
    for r in range(len(raw)):
        vals = raw.iloc[r].tolist()
        raw_title = vals[3] if len(vals) > 3 else None
        title = _clean_title(raw_title)
        if not title:
            continue
        slot, day, time = _parse_slot(str(raw_title))
        if not slot and not day:
            continue
        out[_norm_key(title)] = {
            "program_name": title,
            "slot": slot,
            "day": day,
            "time": time,
            "raw_title": str(raw_title),
        }
    return out


def _extract_capex_monthly(path: Path, report_date: str) -> pd.DataFrame:
    sheet = "◎ '26년 월별 CAPEX 집행 현황"
    if sheet not in pd.ExcelFile(path).sheet_names:
        return pd.DataFrame()
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    rows: list[dict] = []
    category = "예능"
    for r in range(len(raw)):
        vals = raw.iloc[r].tolist()
        label1 = str(vals[1]).strip() if len(vals) > 1 and pd.notna(vals[1]) else ""
        if "NO." in label1:
            if rows:
                category = "드라마"
            continue
        title = _clean_title(vals[2]) if len(vals) > 2 else None
        if not title:
            continue
        total = _money(vals[3]) if len(vals) > 3 else None
        base = {
            "report_date": report_date,
            "category": category,
            "program_name": title.replace("그대애게", "그대에게").replace("짐싸라비움", "짐쌀라비움"),
            "capex_total_million": total,
            "source_file": path.name,
            "data_area": "admin_revenue",
        }
        for i, month in enumerate(range(1, 13)):
            col = 4 + i
            if col >= len(vals):
                break
            amount = _money(vals[col])
            if amount is None:
                continue
            rows.append({**base, "month": month, "capex_million": amount})
    return pd.DataFrame(rows)


def _extract_targets(path: Path, report_date: str) -> pd.DataFrame:
    sheet = "25년 예능 목표 시청률"
    if sheet not in pd.ExcelFile(path).sheet_names:
        return pd.DataFrame()
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    rows: list[dict] = []
    for r in range(len(raw)):
        vals = raw.iloc[r].tolist()
        title = _clean_title(vals[1]) if len(vals) > 1 else None
        if not title:
            continue
        # 정규화
        title = (
            title.replace("나는SOLO", "나는 솔로")
            .replace("나.솔.사.계", "나솔사계")
            .replace("지구마블3", "지구마블3")
        )
        avg = _rating(vals[3]) if len(vals) > 3 else None
        if avg is None:
            continue
        rows.append(
            {
                "report_date": report_date,
                "program_name": title,
                "target_episodes": int(_num(vals[2]) or 0) or None,
                "target_rating": avg,
                "target_grp": _rating(vals[4]) if len(vals) > 4 else None,
                "category": "예능",
                "source_file": path.name,
                "data_area": "variety",
            }
        )
    return pd.DataFrame(rows)


def _extract_drama_episodes(path: Path, report_date: str) -> pd.DataFrame:
    sheet = "◎ '26년 오리지널 드라마"
    if sheet not in pd.ExcelFile(path).sheet_names:
        return pd.DataFrame()
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    rows: list[dict] = []
    current_title: str | None = None
    dates_row: list[Any] = []

    def emit(metric: str, vals: list[Any]) -> None:
        if not current_title:
            return
        for i, v in enumerate(vals[4:]):
            value = _rating(v) if metric in {"target", "household"} else _num(v)
            if value is None:
                continue
            rows.append(
                {
                    "report_date": report_date,
                    "category": "드라마",
                    "program_name": current_title,
                    "episode": i + 1,
                    "broadcast_date": _date_iso(dates_row[i]) if i < len(dates_row) else None,
                    "metric": metric,
                    "value": value,
                    "source_file": path.name,
                    "data_area": "drama",
                }
            )

    for r in range(len(raw)):
        vals = list(raw.iloc[r].tolist())
        c1 = vals[1] if len(vals) > 1 else None
        c2 = vals[2] if len(vals) > 2 else None
        title_cell = _clean_title(c1)
        metric_label = str(c2).strip() if pd.notna(c2) else ""

        if (
            title_cell
            and metric_label not in {"타깃", "전국가구", "타이틀", "예산/목표"}
            and not any(k in title_cell for k in ("현황", "단위", "시청률"))
            and _num(c2) is None
        ):
            current_title = title_cell.replace("그대애게", "그대에게")
            dates_row = vals[4:] if any(_date_iso(v) for v in vals[4:20]) else []
            continue
        if current_title is None:
            continue
        if any(_date_iso(v) for v in vals[4:20]) and metric_label not in {"타깃", "전국가구"}:
            dates_row = vals[4:]
            continue
        if metric_label == "타깃":
            emit("target", vals)
        elif metric_label == "전국가구":
            emit("household", vals)
        elif _num(c2) is not None:
            emit("capex", vals)
    return pd.DataFrame(rows)


def _merge_programs(
    summary: list[dict],
    drama_cmp: list[dict],
    variety_cmp: list[dict],
    slots: dict[str, dict],
    targets: pd.DataFrame,
    capex_df: pd.DataFrame,
) -> pd.DataFrame:
    by_key: dict[str, dict] = {}

    def upsert(row: dict) -> None:
        name = str(row.get("program_name") or "").strip()
        if not name:
            return
        key = _norm_key(name)
        cur = by_key.get(key)
        if cur is None:
            by_key[key] = {**row}
            return
        for k, v in row.items():
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            if cur.get(k) is None or cur.get(k) == "" or cur.get(k) == 0:
                cur[k] = v
            elif k in {"rating_target_p2049", "capex_million", "episodes"} and cur.get(k) in (None, 0):
                cur[k] = v

    for row in summary + drama_cmp + variety_cmp:
        upsert(row)

    # CAPEX total 보강
    if not capex_df.empty:
        totals = (
            capex_df.groupby(["program_name", "category"], as_index=False)["capex_total_million"]
            .first()
        )
        for _, r in totals.iterrows():
            upsert(
                {
                    "program_name": r["program_name"],
                    "category": r["category"],
                    "capex_million": r["capex_total_million"],
                    "channel": "ENA",
                    "report_date": summary[0]["report_date"] if summary else None,
                    "data_area": "variety" if r["category"] == "예능" else "drama",
                    "source_file": r.get("source_file"),
                }
            )

    # 슬롯 보강
    for key, slot_info in slots.items():
        if key in by_key:
            by_key[key]["slot"] = slot_info.get("slot")
            by_key[key]["day"] = slot_info.get("day")
            by_key[key]["time"] = slot_info.get("time")
        else:
            upsert(
                {
                    "program_name": slot_info["program_name"],
                    "category": "예능",
                    "slot": slot_info.get("slot"),
                    "day": slot_info.get("day"),
                    "time": slot_info.get("time"),
                    "channel": "ENA",
                    "data_area": "variety",
                }
            )

    # 목표 시청률 — 없는 타이틀은 기획/목표 행으로 추가
    if not targets.empty:
        for _, r in targets.iterrows():
            key = _norm_key(str(r["program_name"]))
            if key in by_key:
                by_key[key]["target_rating"] = r.get("target_rating")
                if not by_key[key].get("episodes") and r.get("target_episodes"):
                    by_key[key]["episodes"] = r.get("target_episodes")
            else:
                upsert(
                    {
                        "report_date": r.get("report_date"),
                        "category": "예능",
                        "program_name": r["program_name"],
                        "episodes": r.get("target_episodes"),
                        "rating_target_p2049": None,
                        "target_rating": r.get("target_rating"),
                        "capex_million": None,
                        "channel": "ENA",
                        "note": "목표 편성",
                        "data_area": "variety",
                        "source_file": r.get("source_file"),
                    }
                )

    df = pd.DataFrame(list(by_key.values()))
    if df.empty:
        return df
    df["revenue_million"] = df["capex_million"]
    return df


def extract_all(path: str | Path) -> dict[str, pd.DataFrame]:
    path = Path(path)
    report_date = extract_report_date(path)
    summary = _extract_summary(path, report_date)
    drama_cmp = _extract_drama_compare(path, report_date)
    variety_cmp = _extract_variety_compare(path, report_date)
    slots = _extract_variety_slots(path)
    capex = _extract_capex_monthly(path, report_date)
    targets = _extract_targets(path, report_date)
    episodes = _extract_drama_episodes(path, report_date)
    programs = _merge_programs(summary, drama_cmp, variety_cmp, slots, targets, capex)

    revenue = pd.DataFrame()
    if not programs.empty:
        rev = programs.dropna(subset=["capex_million"]).copy()
        if not rev.empty:
            revenue = pd.DataFrame(
                {
                    "report_date": rev["report_date"],
                    "program_name": rev["program_name"],
                    "channel": rev.get("channel", "ENA"),
                    "category": rev["category"],
                    "revenue_million": rev["capex_million"],
                    "note": rev.get("note"),
                    "source_file": rev.get("source_file", path.name),
                }
            )

    return {
        "programs_summary": programs,
        "revenue_records": revenue,
        "capex_monthly": capex,
        "drama_title_compare": pd.DataFrame(drama_cmp),
        "variety_title_compare": pd.DataFrame(variety_cmp),
        "episode_ratings_drama": episodes,
        "target_ratings": targets,
    }


def write_processed_csvs(frames: dict[str, pd.DataFrame]) -> dict[str, Path]:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, df in frames.items():
        out = PROCESSED / f"{name}.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
        written[name] = out
    return written


def _rows_clean(df: pd.DataFrame) -> list[dict]:
    rows = []
    for r in df.to_dict(orient="records"):
        rows.append({k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in r.items()})
    return rows


def upload_frames(frames: dict[str, pd.DataFrame], *, dry_run: bool = False) -> dict[str, Any]:
    from data.supabase_upload import upload_table

    revenue = frames.get("revenue_records", pd.DataFrame())
    programs = frames.get("programs_summary", pd.DataFrame())
    result: dict[str, Any] = {
        "revenue_records": 0,
        "original_programs": 0,
        "errors": [],
        "backend": None,
    }
    if dry_run:
        result["revenue_records"] = len(revenue)
        result["original_programs"] = len(programs)
        return result

    backends: set[str] = set()

    if not revenue.empty:
        by_date: dict[str, list[dict]] = {}
        for row in _rows_clean(revenue):
            by_date.setdefault(str(row["report_date"]), []).append(row)
        total = 0
        for d, group in by_date.items():
            up = upload_table("revenue_records", d, group)
            total += int(up["uploaded"])
            backends.add(up.get("backend") or "none")
            if up.get("warning"):
                result["errors"].append(str(up["warning"]))
        result["revenue_records"] = total

    if not programs.empty:
        cols = [
            "report_date",
            "category",
            "program_name",
            "episodes",
            "rating_target_p2049",
            "rating_household",
            "capex_million",
            "channel",
            "note",
            "source_file",
        ]
        slim_df = programs.copy()
        for c in cols:
            if c not in slim_df.columns:
                slim_df[c] = None
        slim_df = slim_df[cols]
        by_date = {}
        for row in _rows_clean(slim_df):
            if not row.get("report_date") or not row.get("program_name"):
                continue
            by_date.setdefault(str(row["report_date"]), []).append(row)
        total = 0
        for d, group in by_date.items():
            up = upload_table("original_programs", d, group)
            total += int(up["uploaded"])
            backends.add(up.get("backend") or "none")
            if up.get("warning"):
                result["errors"].append(str(up["warning"]))
        result["original_programs"] = total

    result["backend"] = ",".join(sorted(backends)) if backends else "none"
    return result


def apply_original_workbook(
    path: str | Path,
    *,
    dry_run: bool = False,
    original_name: str | None = None,
) -> dict[str, Any]:
    """분류 CSV 저장 + Supabase 업로드. Streamlit 관리자/CLI 공용."""
    path = Path(path)
    frames = extract_all(path)
    # source_file을 원본 파일명으로
    if original_name:
        for df in frames.values():
            if not df.empty and "source_file" in df.columns:
                df["source_file"] = original_name

    written = write_processed_csvs(frames)
    upload = upload_frames(frames, dry_run=dry_run)
    programs = frames["programs_summary"]
    drama_n = int((programs["category"] == "드라마").sum()) if not programs.empty else 0
    variety_n = int((programs["category"] == "예능").sum()) if not programs.empty else 0
    report_date = (
        str(programs["report_date"].iloc[0])
        if not programs.empty and "report_date" in programs.columns
        else extract_report_date(path)
    )
    return {
        "kind": "original_content",
        "report_date": report_date,
        "source_file": original_name or path.name,
        "counts": {
            "programs_total": len(programs),
            "drama": drama_n,
            "variety": variety_n,
            "revenue_rows": len(frames.get("revenue_records", [])),
            "capex_monthly": len(frames.get("capex_monthly", [])),
            "drama_episodes": len(frames.get("episode_ratings_drama", [])),
            "targets": len(frames.get("target_ratings", [])),
        },
        "csv_files": {k: str(v.name) for k, v in written.items()},
        "uploaded": upload,
        "sample_programs": programs.head(8).to_dict(orient="records") if not programs.empty else [],
        "dry_run": dry_run,
    }
