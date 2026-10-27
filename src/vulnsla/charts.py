"""Small inline-SVG charts. Colors are CSS variables so the page's light/dark theme applies.

Every mark carries a <title>, which browsers show as a hover tooltip, and every chart has a
matching data table on the page, so no number is available only as a shape.
"""

from __future__ import annotations

import math
from html import escape

W, H = 520, 240  # close to the rendered card width, so 13px text stays about 13px on screen
PAD_L, PAD_R, PAD_T, PAD_B = 44, 16, 16, 34


def nice_max(value: float) -> float:
    """Round up to 1, 2 or 5 times a power of ten so gridlines land on round numbers."""
    if value <= 0:
        return 1
    exp = 10 ** math.floor(math.log10(value))
    for step in (1, 2, 5, 10):
        if value <= step * exp:
            return step * exp
    return 10 * exp


def _fmt(v: float, pct: bool) -> str:
    return f"{v:.0f}%" if pct else f"{v:g}"


def _frame(top: float, ticks: int = 4, pct: bool = False) -> list[str]:
    parts = []
    plot_h = H - PAD_T - PAD_B
    for i in range(ticks + 1):
        v = top * i / ticks
        y = PAD_T + plot_h - plot_h * i / ticks
        cls = "axis" if i == 0 else "grid"
        parts.append(f'<line class="{cls}" x1="{PAD_L}" x2="{W - PAD_R}" y1="{y:.1f}" y2="{y:.1f}"/>')
        parts.append(f'<text class="tick" x="{PAD_L - 6}" y="{y + 4:.1f}" text-anchor="end">{_fmt(v, pct)}</text>')
    return parts


def _svg(label: str, parts: list[str]) -> str:
    return (
        f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(label)}" '
        f'preserveAspectRatio="xMidYMid meet">{"".join(parts)}</svg>'
    )


def _x_labels(labels: list[str], xs: list[float]) -> list[str]:
    every = 1 if len(labels) <= 8 else 2
    out = []
    for i, (lab, x) in enumerate(zip(labels, xs, strict=True)):
        if i % every == 0 or i == len(labels) - 1:
            out.append(f'<text class="tick" x="{x:.1f}" y="{H - PAD_B + 18}" text-anchor="middle">{escape(lab)}</text>')
    return out


def line_chart(
    labels: list[str],
    values: list[float | None],
    label: str,
    pct: bool = False,
    target: float | None = None,
    target_label: str = "",
) -> str:
    known = [v for v in values if v is not None]
    top = 100 if pct else nice_max(max(known + [target or 0], default=1))
    plot_w, plot_h = W - PAD_L - PAD_R, H - PAD_T - PAD_B
    step = plot_w / max(len(labels) - 1, 1)
    xs = [PAD_L + i * step for i in range(len(labels))]

    def y(v: float) -> float:
        return PAD_T + plot_h - plot_h * v / top

    parts = _frame(top, pct=pct)
    if target is not None:
        ty = y(target)
        parts.append(f'<line class="target" x1="{PAD_L}" x2="{W - PAD_R}" y1="{ty:.1f}" y2="{ty:.1f}"/>')
        parts.append(
            f'<text class="tick" x="{W - PAD_R}" y="{ty - 6:.1f}" text-anchor="end">{escape(target_label)}</text>'
        )
    points = [(x, y(v), lab, v) for x, lab, v in zip(xs, labels, values, strict=True) if v is not None]
    if points:
        path = " ".join(f"{'M' if i == 0 else 'L'}{px:.1f},{py:.1f}" for i, (px, py, _, _) in enumerate(points))
        parts.append(f'<path class="line" d="{path}"/>')
    for px, py, lab, v in points:
        tip = f"{lab}: {_fmt(v, pct)}"
        parts.append(f'<g class="pt"><title>{escape(tip)}</title>')
        parts.append(f'<rect class="hit" x="{px - step / 2:.1f}" y="{PAD_T}" width="{step:.1f}" height="{plot_h}"/>')
        parts.append(f'<circle class="dot" cx="{px:.1f}" cy="{py:.1f}" r="4"/></g>')
    if points:  # label the latest value directly, below the point if the target label sits above it
        px, py, _, v = points[-1]
        near_target = target is not None and abs(py - y(target)) < 28
        ly = py + 22 if near_target else py - 10
        parts.append(f'<text class="value" x="{px - 8:.1f}" y="{ly:.1f}" text-anchor="end">{_fmt(v, pct)}</text>')
    parts += _x_labels(labels, xs)
    return _svg(label, parts)


def grouped_bars(labels: list[str], series: list[tuple[str, list[int], str]], label: str) -> str:
    """series: (name, values, css class that sets the fill)."""
    top = nice_max(max((v for _, vals, _ in series for v in vals), default=1))
    plot_w, plot_h = W - PAD_L - PAD_R, H - PAD_T - PAD_B
    group_w = plot_w / len(labels)
    bar_w = min(28.0 if len(series) == 1 else 14.0, (group_w - 8) / len(series) - 2)
    parts = _frame(top)
    xs = []
    for i, lab in enumerate(labels):
        center = PAD_L + group_w * (i + 0.5)
        xs.append(center)
        first = center - (bar_w * len(series) + 2 * (len(series) - 1)) / 2
        for j, (name, vals, cls) in enumerate(series):
            v = vals[i]
            h = plot_h * v / top
            x = first + j * (bar_w + 2)
            y0 = PAD_T + plot_h
            r = min(4.0, bar_w / 2, h)
            # Rounded data end only; the baseline end stays square.
            d = (
                f"M{x:.1f},{y0:.1f} V{y0 - h + r:.1f} Q{x:.1f},{y0 - h:.1f} {x + r:.1f},{y0 - h:.1f} "
                f"H{x + bar_w - r:.1f} Q{x + bar_w:.1f},{y0 - h:.1f} {x + bar_w:.1f},{y0 - h + r:.1f} V{y0:.1f} Z"
            )
            parts.append(f'<path class="{cls}" d="{d}"><title>{escape(f"{lab} · {name}: {v}")}</title></path>')
    parts += _x_labels(labels, xs)
    return _svg(label, parts)


def target_bars(rows: list[tuple[str, float | None, float]], label: str, unit: str = "days") -> str:
    """Horizontal bars (actual) with a tick for the target, one row per category."""
    top = nice_max(max([v or 0 for _, v, _ in rows] + [t for _, _, t in rows]))
    left, right, row_h = 90, 70, 44
    height = row_h * len(rows) + 30
    plot_w = W - left - right
    parts = []
    for i in range(5):
        x = left + plot_w * i / 4
        parts.append(f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="6" y2="{height - 24}"/>')
        parts.append(f'<text class="tick" x="{x:.1f}" y="{height - 6}" text-anchor="middle">{top * i / 4:g}</text>')
    for i, (name, value, target) in enumerate(rows):
        y = 10 + i * row_h
        parts.append(f'<text class="cat" x="{left - 10}" y="{y + 19}" text-anchor="end">{escape(name)}</text>')
        tx = left + plot_w * target / top
        if value is not None:
            w = max(plot_w * value / top, 2)
            over = value > target
            cls = "bar-over" if over else "bar"
            tip = f"{name}: {value:g} {unit} (target {target:g})"
            parts.append(
                f'<rect class="{cls}" x="{left}" y="{y + 6}" width="{w:.1f}" height="18" rx="4">'
                f"<title>{escape(tip)}</title></rect>"
            )
            # Over-target is stated in words too, never by color alone.
            note = " · over" if over else ""
            # Start the label past both the bar end and the target tick so neither overlaps it.
            lx = max(left + w, tx) + 8
            parts.append(f'<text class="value" x="{lx:.1f}" y="{y + 20}">{value:g}{note}</text>')
        parts.append(f'<line class="target-tick" x1="{tx:.1f}" x2="{tx:.1f}" y1="{y + 1}" y2="{y + 29}"/>')
    return (
        f'<svg class="chart" viewBox="0 0 {W} {height}" role="img" aria-label="{escape(label)}">{"".join(parts)}</svg>'
    )
