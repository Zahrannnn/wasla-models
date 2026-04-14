"""
Chart data contract — structured payloads for interactive frontend rendering.

Tools that produce chart-worthy data include a ``_charts`` list in their
return dict.  The API route handler extracts these from ToolMessages and
returns them in ``ChatResponse.charts`` alongside the text response.

The frontend renders each ``ChartBlock`` as an interactive chart (Chart.js,
Recharts, etc.) inline in the chat conversation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChartDataset(BaseModel):
    """One data series in a chart (one line, one set of bars, or one set of slices)."""

    label: str = Field(description="Legend label for this series")
    data: list[float | int] = Field(description="Numeric values, one per label on the axis")


class ChartBlock(BaseModel):
    """One interactive chart block for the frontend to render.

    When a tool returns ``_charts``, the route handler strips them from
    the tool result and attaches them to ``ChatResponse.charts``.

    Chart types:
        bar      — vertical bar chart (comparisons, monthly trends)
        line     — line chart (time-series trends)
        pie      — pie chart (proportional breakdown)
        doughnut — doughnut chart (proportional breakdown, hollow center)
    """

    id: str = Field(
        description=(
            "Stable identifier for this chart. Frontend can use it as a "
            "React key and for test selectors. Examples: 'expense_monthly', "
            "'offers_by_status', 'employee_tasks'."
        )
    )
    chart_type: str = Field(
        description="Rendering type: 'bar', 'line', 'pie', or 'doughnut'."
    )
    title: str = Field(
        description="Human-readable chart title shown above the chart."
    )
    labels: list[str] = Field(
        default_factory=list,
        description="Category or X-axis labels (one per data point).",
    )
    datasets: list[ChartDataset] = Field(
        default_factory=list,
        description="One or more data series to plot.",
    )
