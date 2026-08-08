"""숫자·금액 포맷 유틸.

규칙:
- 시청률 관련: 소수 3자리
- 매출 관련: 소수 1자리
- 그 외: 소수 없음(정수)
"""

RATING_DECIMALS = 3
REVENUE_DECIMALS = 1
OTHER_DECIMALS = 0

# 하위 호환
DECIMALS = RATING_DECIMALS


def _to_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def round_rating(value: float | int | None) -> float | None:
    """시청률을 소수 3자리로 반올림."""
    f = _to_float(value)
    return None if f is None else round(f, RATING_DECIMALS)


def round_revenue(value: float | int | None) -> float | None:
    """매출(백만 원 등)을 소수 1자리로 반올림."""
    f = _to_float(value)
    return None if f is None else round(f, REVENUE_DECIMALS)


def round_other(value: float | int | None) -> int | None:
    """시청률·매출 외 수치는 정수로 반올림."""
    f = _to_float(value)
    return None if f is None else int(round(f, OTHER_DECIMALS))


def format_rating(value: float | int | None, *, suffix: str = "%") -> str:
    """시청률 표시용 (소수 3자리)."""
    r = round_rating(value)
    if r is None:
        return "-"
    return f"{r:.{RATING_DECIMALS}f}{suffix}"


def format_revenue_won(revenue_million: float | int | None) -> str:
    """백만 원 단위 데이터를 억 원 단위 문자열로 변환 (소수 1자리)."""
    f = _to_float(revenue_million)
    if f is None:
        return "-"
    eok = f / 100.0
    return f"{eok:.{REVENUE_DECIMALS}f}억원"


def format_other(value: float | int | None, *, suffix: str = "") -> str:
    """시청률·매출 외 숫자 표시 (정수)."""
    n = round_other(value)
    if n is None:
        return "-"
    return f"{n}{suffix}"


def format_pct(value: float | int | None) -> str:
    """달성률 등 일반 비율 표시 (정수 %)."""
    return format_other(value, suffix="%")
