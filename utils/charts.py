"""공통 막대 그래프 유틸 — 다크 네온 UI."""

from __future__ import annotations

import re

import plotly.graph_objects as go

from utils.theme import CHART_LAYOUT, COLORS

BAR_RADIUS = 8
RATING_DECIMALS = 3
REVENUE_DECIMALS = 1
OTHER_DECIMALS = 0
DEFAULT_DECIMALS = RATING_DECIMALS


def _title_layout(title: str) -> dict:
    # text=None 이면 Plotly.js가 차트 제목에 "undefined"를 렌더링함
    return dict(text=title or "", font=dict(color="#ffffff", size=16))


def _top_margin(title: str) -> int:
    return 60 if title else 24


def _as_number_list(values: list) -> list[float]:
    return [float(v) for v in values]


def _is_revenue_label(*parts: str) -> bool:
    blob = " ".join(str(p) for p in parts)
    return any(k in blob for k in ("매출", "CAPEX", "부가", "억", "제작비", "revenue"))


def _is_rating_label(*parts: str) -> bool:
    blob = " ".join(str(p) for p in parts).lower()
    # 달성률은 시청률 수치가 아님
    if "달성" in blob:
        return False
    return any(
        k in blob
        for k in ("시청률", "rating", "점유율", "share", "grp")
    )


def _decimals_for(*parts: str) -> int:
    if _is_revenue_label(*parts):
        return REVENUE_DECIMALS
    if _is_rating_label(*parts):
        return RATING_DECIMALS
    return OTHER_DECIMALS


def _fmt_num(value: float, decimals: int, suffix: str = "") -> str:
    if decimals <= 0:
        return f"{int(round(float(value)))}{suffix}"
    return f"{float(value):.{decimals}f}{suffix}"


def _suffix_from_template(text_template: str) -> str:
    return "%" if str(text_template or "").endswith("%") else ""


def _decimals_from_template(text_template: str, fallback: int = DEFAULT_DECIMALS) -> int:
    m = re.search(r"\.(\d+)f", str(text_template or ""))
    if m:
        return int(m.group(1))
    return fallback


def apply_chart_style(fig: go.Figure) -> go.Figure:
    fig.update_layout(**CHART_LAYOUT)
    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.06)",
        linecolor="rgba(255,255,255,0.12)",
        tickfont=dict(color="#cbd5e1"),
        title_font=dict(color="#e2e8f0"),
    )
    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.06)",
        linecolor="rgba(255,255,255,0.12)",
        tickfont=dict(color="#cbd5e1"),
        title_font=dict(color="#e2e8f0"),
    )
    return fig


def _gradient_bar_colors(count: int, highlight: set[int] | None = None) -> list[str]:
    highlight = highlight or set()
    colors = []
    for i in range(count):
        if i in highlight:
            colors.append(COLORS["magenta"])
        elif i % 2 == 0:
            colors.append(COLORS["cyan"])
        else:
            colors.append(COLORS["purple"])
    return colors


def bar_chart(
    x: list,
    y: list,
    title: str,
    y_title: str = "",
    text_template: str = "%{y:.3f}",
    highlight_indices: set[int] | None = None,
    height: int = 380,
) -> go.Figure:
    y_vals = _as_number_list(y)
    colors = _gradient_bar_colors(len(x), highlight_indices)
    suffix = _suffix_from_template(text_template)
    decimals = _decimals_for(title, y_title)
    labels = [_fmt_num(v, decimals, suffix) for v in y_vals]
    fig = go.Figure(
        go.Bar(
            x=[str(v) for v in x],
            y=y_vals,
            marker=dict(
                color=colors,
                line=dict(width=0),
            ),
            text=labels,
            textposition="outside",
            textfont=dict(color="#e2e8f0", size=12),
            hovertemplate="%{x}: %{text}<extra></extra>",
        )
    )
    fig.update_layout(
        title=_title_layout(title),
        yaxis_title=y_title or "",
        height=height,
        showlegend=False,
        bargap=0.28,
        margin=dict(l=20, r=20, t=_top_margin(title), b=20),
    )
    fig.update_traces(marker_cornerradius=BAR_RADIUS)
    return apply_chart_style(fig)


def grouped_bar_chart(
    categories: list[str],
    series: dict[str, list],
    title: str,
    y_title: str = "",
    height: int = 400,
) -> go.Figure:
    palette = [COLORS["cyan"], COLORS["magenta"], COLORS["purple"], COLORS["blue"]]
    fig = go.Figure()
    cats = [str(c) for c in categories]
    for i, (name, values) in enumerate(series.items()):
        vals = _as_number_list(values)
        labels = [
            _fmt_num(v, _decimals_for(title, y_title, name, cat))
            for cat, v in zip(cats, vals)
        ]
        fig.add_trace(
            go.Bar(
                name=str(name),
                x=cats,
                y=vals,
                marker=dict(color=palette[i % len(palette)], line=dict(width=0)),
                text=labels,
                textposition="outside",
                textfont=dict(color="#e2e8f0", size=11),
                hovertemplate="%{x}<br>%{fullData.name}: %{text}<extra></extra>",
            )
        )
    fig.update_layout(
        title=_title_layout(title),
        yaxis_title=y_title or "",
        height=height,
        barmode="group",
        bargap=0.18,
        bargroupgap=0.08,
        legend=dict(font=dict(color="#e2e8f0"), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=20, r=20, t=_top_margin(title), b=20),
    )
    fig.update_traces(marker_cornerradius=BAR_RADIUS)
    return apply_chart_style(fig)


def horizontal_bar_chart(
    labels: list[str],
    values: list,
    title: str,
    x_title: str = "",
    text_suffix: str = "",
    height: int = 380,
) -> go.Figure:
    vals = _as_number_list(values)
    colors = _gradient_bar_colors(len(labels))
    decimals = _decimals_for(title, x_title)
    fig = go.Figure(
        go.Bar(
            y=[str(v) for v in labels],
            x=vals,
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[_fmt_num(v, decimals, text_suffix) for v in vals],
            textposition="outside",
            textfont=dict(color="#e2e8f0", size=12),
            hovertemplate="%{y}: %{text}<extra></extra>",
        )
    )
    fig.update_layout(
        title=_title_layout(title),
        xaxis_title=x_title or "",
        height=height,
        showlegend=False,
        bargap=0.22,
        margin=dict(l=20, r=20, t=_top_margin(title), b=20),
    )
    fig.update_traces(marker_cornerradius=BAR_RADIUS)
    return apply_chart_style(fig)
