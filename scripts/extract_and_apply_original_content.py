"""
오리지널 콘텐츠 관리 엑셀 → 영역별 CSV 추출 + Supabase/앱 적용.

분류:
  1) programs_summary.csv     → 홈/예능 카탈로그·CAPEX(매출)
  2) revenue_records.csv      → revenue_records 업로드
  3) capex_monthly.csv        → 월별 CAPEX 집행
  4) drama_title_compare.csv  → 드라마 타이틀 비교
  5) variety_title_compare.csv→ 예능 타이틀 비교
  6) episode_ratings.csv      → 회차별 시청률(드라마+예능)
  7) target_ratings.csv       → 목표 시청률

사용:
  python scripts/extract_and_apply_original_content.py
  python scripts/extract_and_apply_original_content.py --dry-run
  python scripts/extract_and_apply_original_content.py --file "경로.xlsx"
"""

from __future__ import annotations

import argparse
import re
import sys
import warnings
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

OUT_DIR = ROOT / "data" / "processed"
SKIP_TITLES = {"계", "검증", "합계", "소계", "총계", "average", "all", "nan", "none"}


def find_default_file() -> Path | None:
    for pattern in ("*0802*.xlsx", "*오리지널*콘텐츠*관리*.xlsx"):
        cands = sorted(
            (p for p in ROOT.glob(pattern) if not p.name.startswith("~$")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if cands:
            return cands[0]
    return None


def _clean(v: Any) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return None
    s = re.sub(r"\s+", " ", str(v).replace("\n", " ")).strip()
    if not s or s.lower() in SKIP_TITLES:
        return None
    if re.search(r"(^|\s)(계|합계|소계|총계)$", s):
        return None
    if re.fullmatch(r"[\d,.]+", s):
        return None
    return s


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


def extract_report_date(path: Path, xl: pd.ExcelFile) -> str:
    raw = pd.read_excel(path, sheet_name="● summary", header=None)
    for r in range(min(6, len(raw))):
        for v in raw.iloc[r].tolist():
            d = _date_iso(v)
            if d and d.startswith("202"):
                return d
    m = re.search(r"(20)?(\d{2})(\d{2})", path.stem)
    if m:
        yy = int(m.group(2))
        mm = int(m.group(3)[:2]) if len(m.group(3)) >= 2 else 1
        # filename pattern 0802 → month/day
        md = re.search(r"~(\d{2})(\d{2})", path.stem)
        if md:
            return date(2000 + yy if yy < 100 else yy, int(md.group(1)), int(md.group(2))).isoformat()
    return date.today().isoformat()


def extract_programs_summary(path: Path, report_date: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="● summary", header=None)
    rows: list[dict] = []
    category: str | None = None
    for r in range(len(raw)):
        vals = raw.iloc[r].tolist()
        # col1=구분, col2=타이틀, col3=편수, col4=타깃시청률, col5=가구, col6=CAPEX, col7=비고
        cat = _clean(vals[1]) if len(vals) > 1 else None
        if cat in {"드라마", "예능"}:
            category = cat
        title = _clean(vals[2]) if len(vals) > 2 else None
        if not title or not category:
            continue
        episodes = _num(vals[3]) if len(vals) > 3 else None
        target_rating = _num(vals[4]) if len(vals) > 4 else None
        household_rating = _num(vals[5]) if len(vals) > 5 else None
        capex = _num(vals[6]) if len(vals) > 6 else None
        note = _clean(vals[7]) if len(vals) > 7 else None
        if capex is None and target_rating is None:
            continue
        rows.append(
            {
                "report_date": report_date,
                "category": category,
                "program_name": title,
                "episodes": int(episodes) if episodes is not None else None,
                "rating_target_p2049": target_rating,
                "rating_household": household_rating,
                "capex_million": capex,
                "revenue_million": capex,  # 프로젝트 매출 필드와 동일 단위(백만)
                "channel": "ENA",
                "note": note,
                "source_file": path.name,
                "data_area": "variety" if category == "예능" else "drama",
            }
        )
    return pd.DataFrame(rows)


def extract_capex_monthly(path: Path, report_date: str) -> pd.DataFrame:
    sheet = "◎ '26년 월별 CAPEX 집행 현황"
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    rows: list[dict] = []
    months = list(range(1, 13))
    category = "예능"
    for r in range(len(raw)):
        vals = raw.iloc[r].tolist()
        label = str(vals[2]).strip() if len(vals) > 2 and pd.notna(vals[2]) else ""
        if "NO." in str(vals[1]) if len(vals) > 1 and pd.notna(vals[1]) else "":
            # 두 번째 블록(드라마) 헤더
            if rows:
                category = "드라마"
            continue
        if "계" in label or not label or label.replace(".", "", 1).isdigit():
            continue
        title = _clean(vals[2])
        if not title:
            continue
        total = _num(vals[3]) if len(vals) > 3 else None
        base = {
            "report_date": report_date,
            "category": category,
            "program_name": title,
            "capex_total_million": total,
            "source_file": path.name,
            "data_area": "admin_revenue",
        }
        for i, month in enumerate(months):
            col = 4 + i
            if col >= len(vals):
                break
            amount = _num(vals[col])
            if amount is None:
                continue
            rows.append({**base, "month": month, "capex_million": amount})
    return pd.DataFrame(rows)


def extract_title_compare(path: Path, report_date: str, *, drama: bool) -> pd.DataFrame:
    sheet = (
        "◎ '26년 오리지널 드라마 타이틀 별 비교"
        if drama
        else "◎ '26년 오리지널 예능 타이틀 별 비교"
    )
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    rows: list[dict] = []
    # drama: No, PD, title, episodes..., rating avg, ..., production cost
    # variety: producer group, title, episodes, avg rating, rank, grp, cost...
    for r in range(len(raw)):
        vals = raw.iloc[r].tolist()
        if drama:
            title = _clean(vals[3]) if len(vals) > 3 else None
            if not title:
                continue
            rows.append(
                {
                    "report_date": report_date,
                    "category": "드라마",
                    "program_name": title,
                    "pd": _clean(vals[2]) if len(vals) > 2 else None,
                    "episodes": int(_num(vals[4]) or 0) or None,
                    "rating_avg_p2049": _num(vals[6]) if len(vals) > 6 else None,
                    "grp": _num(vals[7]) if len(vals) > 7 else None,
                    "rank": int(_num(vals[10]) or 0) or None if len(vals) > 10 else None,
                    "capex_million": _num(vals[11]) if len(vals) > 11 else None,
                    "source_file": path.name,
                    "data_area": "drama",
                }
            )
        else:
            # find title-like cell
            title = None
            group = _clean(vals[1]) if len(vals) > 1 else None
            for idx in (2, 3):
                if len(vals) > idx:
                    t = _clean(vals[idx])
                    if t and "소계" not in t and "합계" not in t:
                        # strip (제작사)
                        title = re.sub(r"\([^)]*\)", "", t).strip() or t
                        break
            if not title:
                continue
            # heuristic columns from earlier dump
            rows.append(
                {
                    "report_date": report_date,
                    "category": "예능",
                    "producer_group": group,
                    "program_name": title,
                    "episodes": int(_num(vals[3]) or 0) or None if len(vals) > 3 else None,
                    "rating_avg_p2049": _num(vals[5]) if len(vals) > 5 else None,
                    "rank": int(_num(vals[6]) or 0) or None if len(vals) > 6 else None,
                    "grp": _num(vals[7]) if len(vals) > 7 else None,
                    "capex_million": _num(vals[9]) if len(vals) > 9 else None,
                    "source_file": path.name,
                    "data_area": "variety",
                }
            )
    return pd.DataFrame(rows)


def extract_episode_ratings_drama(path: Path, report_date: str) -> pd.DataFrame:
    sheet = "◎ '26년 오리지널 드라마"
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    rows: list[dict] = []
    current_title: str | None = None
    dates_row: list[Any] = []

    def _emit(metric: str, vals: list[Any]) -> None:
        if not current_title:
            return
        for i, v in enumerate(vals[4:]):
            value = _num(v)
            if value is None:
                continue
            ep_date = _date_iso(dates_row[i]) if i < len(dates_row) else None
            # 회차번호가 날짜 행에 없고 에피소드 순번으로 저장
            rows.append(
                {
                    "report_date": report_date,
                    "category": "드라마",
                    "program_name": current_title,
                    "episode": i + 1,
                    "broadcast_date": ep_date,
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
        title_cell = _clean(c1)
        metric_label = str(c2).strip() if pd.notna(c2) else ""

        # 타이틀 행: col1에 제목, col2는 비어 있거나 숫자가 아님
        if (
            title_cell
            and metric_label not in {"타깃", "전국가구", "타이틀", "예산/목표"}
            and not any(k in title_cell for k in ("현황", "단위", "시청률"))
            and _num(c2) is None
        ):
            current_title = title_cell
            # 같은 행에 방송일이 있으면 사용
            if any(_date_iso(v) for v in vals[4:20]):
                dates_row = vals[4:]
            else:
                dates_row = []
            continue

        if current_title is None:
            continue

        # 방송일 행
        if any(_date_iso(v) for v in vals[4:20]) and metric_label not in {"타깃", "전국가구"}:
            dates_row = vals[4:]
            continue

        if metric_label == "타깃":
            _emit("target", vals)
        elif metric_label == "전국가구":
            _emit("household", vals)
        elif _num(c2) is not None and metric_label not in {"타깃", "전국가구"}:
            _emit("capex", vals)

    return pd.DataFrame(rows)


def extract_target_ratings(path: Path, report_date: str) -> pd.DataFrame:
    sheet = "25년 예능 목표 시청률"
    if sheet not in pd.ExcelFile(path).sheet_names:
        return pd.DataFrame()
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    rows: list[dict] = []
    for r in range(len(raw)):
        vals = raw.iloc[r].tolist()
        title = _clean(vals[1]) if len(vals) > 1 else None
        if not title:
            continue
        episodes = _num(vals[2]) if len(vals) > 2 else None
        avg = _num(vals[3]) if len(vals) > 3 else None
        grp = _num(vals[4]) if len(vals) > 4 else None
        if avg is None:
            continue
        rows.append(
            {
                "report_date": report_date,
                "program_name": title,
                "target_episodes": int(episodes) if episodes else None,
                "target_rating": avg,
                "target_grp": grp,
                "source_file": path.name,
                "data_area": "variety",
            }
        )
    return pd.DataFrame(rows)


def to_revenue_records(programs: pd.DataFrame) -> pd.DataFrame:
    if programs.empty:
        return pd.DataFrame()
    df = programs.copy()
    out = pd.DataFrame(
        {
            "report_date": df["report_date"],
            "program_name": df["program_name"],
            "channel": df.get("channel", "ENA"),
            "category": df["category"],
            "revenue_million": df["capex_million"],
            "note": df.get("note"),
            "source_file": df["source_file"],
        }
    )
    return out.dropna(subset=["program_name", "revenue_million"])


def write_csvs(frames: dict[str, pd.DataFrame]) -> dict[str, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, df in frames.items():
        path = OUT_DIR / f"{name}.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")
        written[name] = path
        print(f"  CSV {name}: {len(df)} rows → {path.name}")
    return written


def upload_revenue(df: pd.DataFrame, *, dry_run: bool) -> int:
    if df.empty:
        return 0
    rows = df.to_dict(orient="records")
    # clean NaN → None
    clean_rows = []
    for r in rows:
        clean_rows.append({k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in r.items()})
    if dry_run:
        print(f"  [--dry-run] revenue_records {len(clean_rows)} rows")
        return len(clean_rows)

    from data.supabase_upload import get_supabase_client, replace_and_upload

    client = get_supabase_client()
    by_date: dict[str, list[dict]] = {}
    for row in clean_rows:
        by_date.setdefault(str(row["report_date"]), []).append(row)
    total = 0
    for d, group in by_date.items():
        total += replace_and_upload(client, "revenue_records", d, group)
    print(f"  uploaded revenue_records: {total}")
    return total


def upload_original_programs(df: pd.DataFrame, *, dry_run: bool) -> int:
    """optional table original_programs — skip if table missing."""
    if df.empty:
        return 0
    rows = []
    for r in df.to_dict(orient="records"):
        rows.append({k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in r.items()})
    if dry_run:
        print(f"  [--dry-run] original_programs {len(rows)} rows")
        return len(rows)
    try:
        from data.supabase_upload import get_supabase_client, replace_and_upload

        client = get_supabase_client()
        # try insert; if table missing, ignore
        by_date: dict[str, list[dict]] = {}
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
        for row in rows:
            slim = {k: row.get(k) for k in cols}
            by_date.setdefault(str(slim["report_date"]), []).append(slim)
        total = 0
        for d, group in by_date.items():
            total += replace_and_upload(client, "original_programs", d, group)
        print(f"  uploaded original_programs: {total}")
        return total
    except Exception as exc:  # noqa: BLE001
        print(f"  [skip] original_programs 업로드 생략: {exc}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="오리지널 콘텐츠 엑셀 → CSV + 업로드 적용")
    parser.add_argument("--file", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-upload", action="store_true", help="CSV만 생성")
    args = parser.parse_args()

    path = args.file or find_default_file()
    if path is None or not path.exists():
        print("엑셀 파일을 찾을 수 없습니다. --file 로 지정하세요.", file=sys.stderr)
        return 1

    path = path.resolve()
    print(f"파일: {path.name}")
    xl = pd.ExcelFile(path)
    report_date = extract_report_date(path, xl)
    print(f"기준일: {report_date}")

    programs = extract_programs_summary(path, report_date)
    capex = extract_capex_monthly(path, report_date)
    drama_cmp = extract_title_compare(path, report_date, drama=True)
    variety_cmp = extract_title_compare(path, report_date, drama=False)
    episodes = extract_episode_ratings_drama(path, report_date)
    targets = extract_target_ratings(path, report_date)
    revenue = to_revenue_records(programs)

    frames = {
        "programs_summary": programs,
        "revenue_records": revenue,
        "capex_monthly": capex,
        "drama_title_compare": drama_cmp,
        "variety_title_compare": variety_cmp,
        "episode_ratings_drama": episodes,
        "target_ratings": targets,
    }
    print("CSV 생성:")
    write_csvs(frames)

    # 영역 매핑 요약
    print("\n영역별 적용:")
    print(f"  [예능/홈] programs_summary 예능 {len(programs[programs['category']=='예능']) if not programs.empty else 0}건")
    print(f"  [드라마]  programs_summary 드라마 {len(programs[programs['category']=='드라마']) if not programs.empty else 0}건 · episode {len(episodes)}건")
    print(f"  [매출]    revenue_records {len(revenue)}건 · capex_monthly {len(capex)}건")
    print(f"  [목표]    target_ratings {len(targets)}건")

    if args.skip_upload:
        print("업로드 생략 (--skip-upload)")
        return 0

    print("\nSupabase 업로드:")
    try:
        upload_revenue(revenue, dry_run=args.dry_run)
        upload_original_programs(programs, dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] Supabase 업로드 실패 (CSV는 적용됨): {exc}")
        print("  네트워크/.env 확인 후 다시 실행하거나 관리자 페이지에서 업로드하세요.")
        return 0
    print("완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
