"""PV feasibility results dashboard — KPI cards, charts, table, CSV export."""

from __future__ import annotations

import calendar
import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from models.pv import PVFeasibilityResult
from ui.analysis_panel import _build_dashboard


MONTH_LABELS = [calendar.month_abbr[m] for m in range(1, 13)]


def render_pv_dashboard(result: PVFeasibilityResult):
    """Render the full PV feasibility dashboard."""
    e = result.energy
    f = result.financial

    # --- KPI Cards ---
    _render_kpi_cards(e, f)

    st.markdown("")  # spacer

    # --- Monthly Energy Bar Chart ---
    _render_monthly_chart(e)

    # --- Two-column: Heatmap + Cash Flow ---
    col1, col2 = st.columns(2)
    with col1:
        _render_hourly_heatmap(e)
    with col2:
        _render_cash_flow_chart(f)

    # --- Monthly Breakdown Table + CSV ---
    _render_monthly_table(e)


def _render_kpi_cards(e, f):
    sizing_items = [
        ("System Size", f"{e.system_capacity_kw:.1f} kW"),
        ("Panels", f"{e.num_panels}"),
        ("Panel Area", f"{e.total_panel_area_m2:.0f} m&sup2;"),
    ]

    energy_items = [
        ("Annual Energy", f"{e.annual_ac_kwh:,.0f} kWh"),
        ("Specific Yield", f"{e.specific_yield_kwh_kwp:,.0f} kWh/kWp"),
        ("Capacity Factor", f"{e.capacity_factor_pct:.1f}%"),
    ]

    payback_str = f"{f.payback_years:.1f} yrs" if f.payback_years <= 40 else "> 40 yrs"
    irr_str = f"{f.irr:.1f}%" if f.irr is not None else "N/A"
    financial_items = [
        ("Net Cost", f"${f.net_cost:,.0f}"),
        ("Payback", payback_str),
        ("NPV", f"${f.npv:,.0f}"),
        ("LCOE", f"${f.lcoe:.3f}/kWh"),
        ("IRR", irr_str),
    ]

    html = _build_dashboard(
        ("System Sizing", "#0ea5e9", sizing_items),
        ("Energy Production", "#10b981", energy_items),
        ("Financial Analysis", "#f59e0b", financial_items),
    )
    st.markdown(html, unsafe_allow_html=True)


def _render_monthly_chart(e):
    ac_values = [m.ac_energy_kwh for m in e.monthly]
    poa_values = [m.poa_kwh_m2 for m in e.monthly]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=MONTH_LABELS, y=ac_values,
        name="AC Energy (kWh)",
        marker_color="#0ea5e9",
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=MONTH_LABELS, y=poa_values,
        name="POA Irradiance (kWh/m2)",
        mode="lines+markers",
        marker=dict(color="#f59e0b", size=7),
        line=dict(color="#f59e0b", width=2),
        yaxis="y2",
    ))
    fig.update_layout(
        title="Monthly Energy Production",
        yaxis=dict(title="AC Energy (kWh)", side="left"),
        yaxis2=dict(title="POA Irradiance (kWh/m2)", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=50, r=50, t=50, b=30),
        height=350,
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True, key="pv_monthly_chart")


def _render_hourly_heatmap(e):
    # 12 months x 24 hours matrix of POA irradiance (kW/m2)
    z = e.hourly_poa_matrix
    hours = list(range(24))

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=hours,
        y=MONTH_LABELS,
        colorscale="YlOrRd",
        colorbar=dict(title="kW/m2"),
        hoverongaps=False,
    ))
    fig.update_layout(
        title="Hourly POA Irradiance Pattern",
        xaxis=dict(title="Hour of Day", dtick=3),
        yaxis=dict(title=""),
        margin=dict(l=50, r=20, t=50, b=30),
        height=350,
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True, key="pv_heatmap")


def _render_cash_flow_chart(f):
    years = list(range(len(f.cumulative_cash_flow)))
    cf = f.cumulative_cash_flow

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=cf,
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(14, 165, 89, 0.15)",
        line=dict(color="#10b981", width=2.5),
        name="Cumulative Cash Flow",
    ))

    # Zero line
    fig.add_hline(y=0, line_dash="dash", line_color="#94a3b8", line_width=1)

    # Payback marker
    if f.payback_years <= len(years):
        payback_idx = min(int(round(f.payback_years)), len(cf) - 1)
        fig.add_trace(go.Scatter(
            x=[f.payback_years], y=[0],
            mode="markers",
            marker=dict(symbol="star", size=14, color="#f59e0b", line=dict(width=1, color="#d97706")),
            name=f"Payback ({f.payback_years:.1f} yr)",
            showlegend=True,
        ))

    fig.update_layout(
        title="Cumulative Cash Flow",
        xaxis=dict(title="Year"),
        yaxis=dict(title="Cumulative ($)", tickformat="$,.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=60, r=20, t=50, b=30),
        height=350,
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True, key="pv_cashflow")


def _render_monthly_table(e):
    rows = []
    for m in e.monthly:
        rows.append({
            "Month": calendar.month_abbr[m.month],
            "GHI (kWh/m2)": m.ghi_kwh_m2,
            "POA (kWh/m2)": m.poa_kwh_m2,
            "DC (kWh)": m.dc_energy_kwh,
            "AC (kWh)": m.ac_energy_kwh,
            "Cell Temp (C)": m.avg_cell_temp,
            "Peak Sun (hrs)": m.peak_sun_hours,
        })

    # Total row
    rows.append({
        "Month": "TOTAL",
        "GHI (kWh/m2)": round(sum(m.ghi_kwh_m2 for m in e.monthly), 1),
        "POA (kWh/m2)": round(sum(m.poa_kwh_m2 for m in e.monthly), 1),
        "DC (kWh)": round(sum(m.dc_energy_kwh for m in e.monthly), 0),
        "AC (kWh)": round(sum(m.ac_energy_kwh for m in e.monthly), 0),
        "Cell Temp (C)": round(sum(m.avg_cell_temp for m in e.monthly) / 12, 1),
        "Peak Sun (hrs)": round(sum(m.peak_sun_hours for m in e.monthly) / 12, 2),
    })

    df = pd.DataFrame(rows)
    st.subheader("Monthly Breakdown")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # CSV download
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(
        "Download CSV",
        data=csv_buf.getvalue(),
        file_name="pv_monthly_results.csv",
        mime="text/csv",
        key="pv_csv_download",
    )
