"""Shared color theme — used by both the live dashboard (app.py) and PDF reports (reports.py)."""

SERIES = {"primary": "#20493A", "amber": "#C97A2B", "teal": "#2B7A78", "rose": "#B5495B", "slate": "#5B6472"}
STATUS = {"good": "#1F7A4D", "warning": "#B4791B", "critical": "#B5495B"}
INK = "#1C1C1A"
INK_MUTED = "#6B6A66"
BORDER = "#E4E2DC"
SURFACE = "#FFFFFF"


def ordinal(n) -> str:
    n = int(round(n))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
