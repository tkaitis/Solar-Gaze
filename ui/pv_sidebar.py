"""PV feasibility sidebar inputs."""

from __future__ import annotations

import streamlit as st

from models.pv import FinancialParams, PanelSpec, RoofPVConfig, SystemLosses


def render_pv_sidebar():
    """Render PV-specific sidebar controls (called when app_mode == pv)."""
    _render_roof_orientation()
    st.divider()
    _render_panel_specs()
    st.divider()
    _render_system_losses()
    st.divider()
    _render_financial_params()


def _render_roof_orientation():
    st.subheader("Roof & Orientation")

    st.session_state.pv_auto_tilt = st.checkbox(
        "Auto tilt (= latitude)",
        value=st.session_state.get("pv_auto_tilt", True),
        key="input_pv_auto_tilt",
    )

    if not st.session_state.pv_auto_tilt:
        st.session_state.pv_tilt_deg = st.number_input(
            "Tilt (degrees)",
            min_value=0.0, max_value=90.0,
            value=st.session_state.get("pv_tilt_deg", 30.0),
            step=1.0, key="input_pv_tilt",
        )

    st.session_state.pv_auto_azimuth = st.checkbox(
        "Auto azimuth (equator-facing)",
        value=st.session_state.get("pv_auto_azimuth", True),
        key="input_pv_auto_azimuth",
    )

    if not st.session_state.pv_auto_azimuth:
        st.session_state.pv_azimuth_deg = st.number_input(
            "Azimuth (degrees, 180=South)",
            min_value=0.0, max_value=359.0,
            value=st.session_state.get("pv_azimuth_deg", 180.0),
            step=5.0, key="input_pv_azimuth",
        )

    st.session_state.pv_usable_roof_pct = st.number_input(
        "Usable roof area (%)",
        min_value=10.0, max_value=100.0,
        value=st.session_state.get("pv_usable_roof_pct", 70.0),
        step=5.0, key="input_pv_usable_roof",
    )


def _render_panel_specs():
    st.subheader("Panel Specifications")

    st.session_state.pv_rated_power = st.number_input(
        "Rated power (W)",
        min_value=100.0, max_value=800.0,
        value=st.session_state.get("pv_rated_power", 400.0),
        step=10.0, key="input_pv_rated_power",
    )

    st.session_state.pv_efficiency = st.number_input(
        "Efficiency (%)",
        min_value=10.0, max_value=30.0,
        value=st.session_state.get("pv_efficiency", 21.0),
        step=0.5, key="input_pv_efficiency",
    )

    with st.expander("Advanced panel settings"):
        st.session_state.pv_temp_coeff = st.number_input(
            "Temp coefficient (%/C)",
            min_value=-1.0, max_value=0.0,
            value=st.session_state.get("pv_temp_coeff", -0.35),
            step=0.05, format="%.2f", key="input_pv_temp_coeff",
        )
        st.session_state.pv_noct = st.number_input(
            "NOCT (C)",
            min_value=35.0, max_value=55.0,
            value=st.session_state.get("pv_noct", 45.0),
            step=1.0, key="input_pv_noct",
        )
        st.session_state.pv_panel_area = st.number_input(
            "Panel area (m2)",
            min_value=0.5, max_value=4.0,
            value=st.session_state.get("pv_panel_area", 1.92),
            step=0.01, format="%.2f", key="input_pv_panel_area",
        )


def _render_system_losses():
    st.subheader("System Losses")

    with st.expander("Adjust loss factors", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.pv_soiling = st.number_input(
                "Soiling (%)", min_value=0.0, max_value=50.0,
                value=st.session_state.get("pv_soiling", 2.0),
                step=0.5, key="input_pv_soiling",
            )
            st.session_state.pv_mismatch = st.number_input(
                "Mismatch (%)", min_value=0.0, max_value=50.0,
                value=st.session_state.get("pv_mismatch", 2.0),
                step=0.5, key="input_pv_mismatch",
            )
            st.session_state.pv_wiring_dc = st.number_input(
                "DC Wiring (%)", min_value=0.0, max_value=50.0,
                value=st.session_state.get("pv_wiring_dc", 2.0),
                step=0.5, key="input_pv_wiring_dc",
            )
            st.session_state.pv_inverter_eff = st.number_input(
                "Inverter eff. (%)", min_value=80.0, max_value=100.0,
                value=st.session_state.get("pv_inverter_eff", 96.0),
                step=0.5, key="input_pv_inverter_eff",
            )
        with c2:
            st.session_state.pv_shading = st.number_input(
                "Shading (%)", min_value=0.0, max_value=50.0,
                value=st.session_state.get("pv_shading", 3.0),
                step=0.5, key="input_pv_shading",
            )
            st.session_state.pv_wiring_ac = st.number_input(
                "AC Wiring (%)", min_value=0.0, max_value=50.0,
                value=st.session_state.get("pv_wiring_ac", 1.0),
                step=0.5, key="input_pv_wiring_ac",
            )
            st.session_state.pv_availability = st.number_input(
                "Availability (%)", min_value=80.0, max_value=100.0,
                value=st.session_state.get("pv_availability", 99.0),
                step=0.5, key="input_pv_availability",
            )

    # Show total derate factor
    losses = get_system_losses()
    st.caption(f"Total derate factor: **{losses.total_derate_factor:.1%}**")


def _render_financial_params():
    st.subheader("Financial Parameters")

    st.session_state.pv_electricity_rate = st.number_input(
        "Electricity rate ($/kWh)",
        min_value=0.0, max_value=1.0,
        value=st.session_state.get("pv_electricity_rate", 0.15),
        step=0.01, format="%.2f", key="input_pv_elec_rate",
    )

    st.session_state.pv_cost_per_watt = st.number_input(
        "System cost ($/W installed)",
        min_value=0.5, max_value=10.0,
        value=st.session_state.get("pv_cost_per_watt", 2.80),
        step=0.10, format="%.2f", key="input_pv_cost_per_watt",
    )

    st.session_state.pv_incentive_pct = st.number_input(
        "Incentive / tax credit (%)",
        min_value=0.0, max_value=100.0,
        value=st.session_state.get("pv_incentive_pct", 30.0),
        step=1.0, key="input_pv_incentive",
    )

    with st.expander("Advanced financial settings"):
        st.session_state.pv_escalation = st.number_input(
            "Price escalation (%/yr)",
            min_value=0.0, max_value=20.0,
            value=st.session_state.get("pv_escalation", 2.5),
            step=0.5, key="input_pv_escalation",
        )
        st.session_state.pv_degradation = st.number_input(
            "Panel degradation (%/yr)",
            min_value=0.0, max_value=5.0,
            value=st.session_state.get("pv_degradation", 0.5),
            step=0.1, format="%.1f", key="input_pv_degradation",
        )
        st.session_state.pv_discount_rate = st.number_input(
            "Discount rate (%)",
            min_value=0.0, max_value=30.0,
            value=st.session_state.get("pv_discount_rate", 5.0),
            step=0.5, key="input_pv_discount_rate",
        )
        st.session_state.pv_analysis_period = st.number_input(
            "Analysis period (years)",
            min_value=1, max_value=40,
            value=st.session_state.get("pv_analysis_period", 25),
            step=1, key="input_pv_analysis_period",
        )
        st.session_state.pv_om_cost = st.number_input(
            "O&M cost ($/kW/yr)",
            min_value=0.0, max_value=200.0,
            value=st.session_state.get("pv_om_cost", 20.0),
            step=5.0, key="input_pv_om_cost",
        )


# --- Getter functions ---

def get_roof_pv_config() -> RoofPVConfig:
    return RoofPVConfig(
        tilt_deg=st.session_state.get("pv_tilt_deg", 30.0),
        azimuth_deg=st.session_state.get("pv_azimuth_deg", 180.0),
        usable_roof_pct=st.session_state.get("pv_usable_roof_pct", 70.0),
        auto_tilt=st.session_state.get("pv_auto_tilt", True),
        auto_azimuth=st.session_state.get("pv_auto_azimuth", True),
    )


def get_panel_spec() -> PanelSpec:
    return PanelSpec(
        rated_power_w=st.session_state.get("pv_rated_power", 400.0),
        efficiency_pct=st.session_state.get("pv_efficiency", 21.0),
        temp_coeff_pmax=st.session_state.get("pv_temp_coeff", -0.35),
        noct_c=st.session_state.get("pv_noct", 45.0),
        panel_area_m2=st.session_state.get("pv_panel_area", 1.92),
    )


def get_system_losses() -> SystemLosses:
    return SystemLosses(
        soiling=st.session_state.get("pv_soiling", 2.0),
        shading=st.session_state.get("pv_shading", 3.0),
        mismatch=st.session_state.get("pv_mismatch", 2.0),
        wiring_dc=st.session_state.get("pv_wiring_dc", 2.0),
        wiring_ac=st.session_state.get("pv_wiring_ac", 1.0),
        inverter_eff=st.session_state.get("pv_inverter_eff", 96.0),
        availability=st.session_state.get("pv_availability", 99.0),
    )


def get_financial_params() -> FinancialParams:
    return FinancialParams(
        electricity_rate=st.session_state.get("pv_electricity_rate", 0.15),
        escalation=st.session_state.get("pv_escalation", 2.5),
        cost_per_watt=st.session_state.get("pv_cost_per_watt", 2.80),
        incentive_pct=st.session_state.get("pv_incentive_pct", 30.0),
        degradation=st.session_state.get("pv_degradation", 0.5),
        discount_rate=st.session_state.get("pv_discount_rate", 5.0),
        analysis_period=st.session_state.get("pv_analysis_period", 25),
        om_cost=st.session_state.get("pv_om_cost", 20.0),
    )
