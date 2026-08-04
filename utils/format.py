"""숫자·금액 포맷 유틸."""

RATING_DECIMALS = 3


def round_rating(value: float | int | None) -> float | None:
    """시청률을 소수 3자리로 반올림. None/NaN은 None."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return round(f, RATING_DECIMALS)


def format_rating(value: float | int | None, *, suffix: str = "%") -> str:
    """시청률 표시용 (소수 3자리)."""
    r = round_rating(value)
    if r is None:
        return "-"
    return f"{r:.{RATING_DECIMALS}f}{suffix}"


def format_revenue_won(revenue_million: float | int) -> str:
    """백만 원 단위 데이터를 억 원 단위 문자열로 변환."""
    eok = float(revenue_million) / 100.0
    if abs(eok) >= 10:
        return f"{eok:.1f}억원"
    return f"{eok:.2f}억원"
