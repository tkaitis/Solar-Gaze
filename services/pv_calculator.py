"""PV feasibility calculator using pvlib for irradiance and energy modeling."""

from __future__ import annotations

import calendar
import math
from datetime import datetime

import numpy as np
import pandas as pd
import pvlib
import streamlit as st

from models.building import BuildingGeometry
from models.pv import (
    AnnualPVResult,
    FinancialParams,
    FinancialResult,
    MonthlyPVResult,
    PanelSpec,
    PVFeasibilityResult,
    RoofPVConfig,
    SystemLosses,
)
from models.solar import LocationConfig


class PVCalculator:

    @staticmethod
    @st.cache_data(ttl=3600)
    def compute_feasibility(
        lat: float,
        lon: float,
        tz: str,
        width: float,
        depth: float,
        roof_pitch: float,
        roof_type: str,
        tilt_deg: float,
        azimuth_deg: float,
        usable_roof_pct: float,
        auto_tilt: bool,
        auto_azimuth: bool,
        rated_power_w: float,
        efficiency_pct: float,
        temp_coeff_pmax: float,
        noct_c: float,
        panel_area_m2: float,
        soiling: float,
        shading: float,
        mismatch: float,
        wiring_dc: float,
        wiring_ac: float,
        inverter_eff: float,
        availability: float,
        electricity_rate: float,
        escalation: float,
        cost_per_watt: float,
        incentive_pct: float,
        degradation: float,
        discount_rate: float,
        analysis_period: int,
        om_cost: float,
    ) -> PVFeasibilityResult:
        """Main entry point — all args are hashable primitives for st.cache_data."""

        # Reconstruct model objects from primitives
        location = LocationConfig(latitude=lat, longitude=lon, timezone=tz)
        roof_config = RoofPVConfig(
            tilt_deg=tilt_deg, azimuth_deg=azimuth_deg,
            usable_roof_pct=usable_roof_pct,
            auto_tilt=auto_tilt, auto_azimuth=auto_azimuth,
        )
        panel = PanelSpec(
            rated_power_w=rated_power_w, efficiency_pct=efficiency_pct,
            temp_coeff_pmax=temp_coeff_pmax, noct_c=noct_c,
            panel_area_m2=panel_area_m2,
        )
        losses = SystemLosses(
            soiling=soiling, shading=shading, mismatch=mismatch,
            wiring_dc=wiring_dc, wiring_ac=wiring_ac,
            inverter_eff=inverter_eff, availability=availability,
        )
        financial = FinancialParams(
            electricity_rate=electricity_rate, escalation=escalation,
            cost_per_watt=cost_per_watt, incentive_pct=incentive_pct,
            degradation=degradation, discount_rate=discount_rate,
            analysis_period=analysis_period, om_cost=om_cost,
        )

        # 1. Resolve orientation
        tilt, azimuth = PVCalculator._resolve_orientation(location, roof_config)

        # 2. System sizing
        num_panels, capacity_kw, total_area = PVCalculator._size_system(
            width, depth, roof_pitch, roof_type,
            usable_roof_pct, panel,
        )

        # 3. Monthly simulation
        monthly, hourly_poa, hourly_dc = PVCalculator._simulate_monthly(
            location, tilt, azimuth, capacity_kw, panel, losses,
        )

        # 4. Aggregate annual results
        annual_ghi = sum(m.ghi_kwh_m2 for m in monthly)
        annual_poa = sum(m.poa_kwh_m2 for m in monthly)
        annual_dc = sum(m.dc_energy_kwh for m in monthly)
        annual_ac = sum(m.ac_energy_kwh for m in monthly)
        specific_yield = annual_ac / capacity_kw if capacity_kw > 0 else 0
        capacity_factor = (annual_ac / (capacity_kw * 8760) * 100) if capacity_kw > 0 else 0

        energy = AnnualPVResult(
            system_capacity_kw=round(capacity_kw, 2),
            num_panels=num_panels,
            total_panel_area_m2=round(total_area, 1),
            annual_ghi_kwh_m2=round(annual_ghi, 1),
            annual_poa_kwh_m2=round(annual_poa, 1),
            annual_dc_kwh=round(annual_dc, 0),
            annual_ac_kwh=round(annual_ac, 0),
            specific_yield_kwh_kwp=round(specific_yield, 0),
            capacity_factor_pct=round(capacity_factor, 1),
            monthly=monthly,
            hourly_poa_matrix=hourly_poa,
            hourly_dc_matrix=hourly_dc,
        )

        # 5. Financial model
        fin = PVCalculator._compute_financials(capacity_kw, annual_ac, financial)

        return PVFeasibilityResult(energy=energy, financial=fin)

    @staticmethod
    def _resolve_orientation(
        location: LocationConfig, config: RoofPVConfig,
    ) -> tuple[float, float]:
        tilt = abs(location.latitude) if config.auto_tilt else config.tilt_deg
        if config.auto_azimuth:
            azimuth = 180.0 if location.latitude >= 0 else 0.0
        else:
            azimuth = config.azimuth_deg
        return tilt, azimuth

    @staticmethod
    def _size_system(
        width: float,
        depth: float,
        roof_pitch: float,
        roof_type: str,
        usable_roof_pct: float,
        panel: PanelSpec,
    ) -> tuple[int, float, float]:
        """Returns (num_panels, capacity_kw, total_panel_area)."""
        footprint = width * depth
        # Adjust for roof slope — actual roof area is larger than footprint
        pitch_rad = math.radians(roof_pitch) if roof_type != "flat" else 0
        slope_factor = 1 / math.cos(pitch_rad) if pitch_rad < math.radians(80) else 1.0
        roof_area = footprint * slope_factor
        usable_area = roof_area * (usable_roof_pct / 100)
        num_panels = max(1, int(usable_area / panel.panel_area_m2))
        capacity_kw = num_panels * panel.rated_power_w / 1000
        total_area = num_panels * panel.panel_area_m2
        return num_panels, capacity_kw, total_area

    @staticmethod
    def _simulate_monthly(
        location: LocationConfig,
        tilt: float,
        azimuth: float,
        capacity_kw: float,
        panel: PanelSpec,
        losses: SystemLosses,
    ) -> tuple[list[MonthlyPVResult], list[list[float]], list[list[float]]]:
        """Simulate 12 representative days (15th of each month).

        Returns (monthly_results, hourly_poa_matrix[12][24], hourly_dc_matrix[12][24]).
        """
        site = pvlib.location.Location(
            location.latitude, location.longitude, tz=location.timezone,
        )
        pdc0 = capacity_kw * 1000  # system DC nameplate in watts
        gamma_pdc = panel.temp_coeff_pmax / 100  # convert %/C to fraction/C

        monthly_results = []
        hourly_poa_matrix = []
        hourly_dc_matrix = []

        for month in range(1, 13):
            days_in = calendar.monthrange(2024, month)[1]
            rep_date = datetime(2024, month, 15)

            # Hourly timestamps for the representative day
            times = pd.date_range(
                start=rep_date, periods=24, freq="h",
                tz=location.timezone,
            )

            # Clear-sky irradiance
            cs = site.get_clearsky(times, model="ineichen")
            ghi = cs["ghi"]
            dni = cs["dni"]
            dhi = cs["dhi"]

            # Solar position for POA calculation
            solpos = site.get_solarposition(times)

            # Plane-of-array irradiance (Perez transposition model)
            poa = pvlib.irradiance.get_total_irradiance(
                surface_tilt=tilt,
                surface_azimuth=azimuth,
                solar_zenith=solpos["apparent_zenith"],
                solar_azimuth=solpos["azimuth"],
                dni=dni,
                ghi=ghi,
                dhi=dhi,
                model="perez",
                dni_extra=pvlib.irradiance.get_extra_radiation(times),
            )
            poa_global = poa["poa_global"].fillna(0).clip(lower=0)

            # Cell temperature (SAPM model)
            temp_air = 20.0  # assume 20C ambient for clear-sky estimate
            wind_speed = 1.0  # assume 1 m/s
            cell_temp = pvlib.temperature.sapm_cell(
                poa_global, temp_air, wind_speed,
                a=-3.56, b=-0.075, deltaT=3,
            )

            # DC power output (PVWatts model)
            dc_power = pvlib.pvsystem.pvwatts_dc(
                poa_global, cell_temp, pdc0, gamma_pdc,
            ).clip(lower=0)

            # AC power = DC * system derate factor
            ac_power = dc_power * losses.total_derate_factor

            # Daily totals (Wh -> kWh)
            daily_ghi_kwh_m2 = float(ghi.sum()) / 1000
            daily_poa_kwh_m2 = float(poa_global.sum()) / 1000
            daily_dc_kwh = float(dc_power.sum()) / 1000
            daily_ac_kwh = float(ac_power.sum()) / 1000

            # Scale to monthly
            monthly_ghi = daily_ghi_kwh_m2 * days_in
            monthly_poa = daily_poa_kwh_m2 * days_in
            monthly_dc = daily_dc_kwh * days_in
            monthly_ac = daily_ac_kwh * days_in
            avg_cell = float(cell_temp[poa_global > 0].mean()) if (poa_global > 0).any() else temp_air
            peak_sun = daily_poa_kwh_m2  # peak sun hours = kWh/m2/day

            monthly_results.append(MonthlyPVResult(
                month=month,
                ghi_kwh_m2=round(monthly_ghi, 2),
                poa_kwh_m2=round(monthly_poa, 2),
                dc_energy_kwh=round(monthly_dc, 1),
                ac_energy_kwh=round(monthly_ac, 1),
                avg_cell_temp=round(avg_cell, 1),
                peak_sun_hours=round(peak_sun, 2),
            ))

            # Store hourly arrays for heatmap (W -> kW)
            hourly_poa_row = [round(float(v) / 1000, 3) for v in poa_global.values]
            hourly_dc_row = [round(float(v) / 1000, 3) for v in dc_power.values]
            # Pad/trim to exactly 24 entries
            hourly_poa_row = (hourly_poa_row + [0] * 24)[:24]
            hourly_dc_row = (hourly_dc_row + [0] * 24)[:24]
            hourly_poa_matrix.append(hourly_poa_row)
            hourly_dc_matrix.append(hourly_dc_row)

        return monthly_results, hourly_poa_matrix, hourly_dc_matrix

    @staticmethod
    def _compute_financials(
        capacity_kw: float,
        annual_ac_kwh: float,
        fp: FinancialParams,
    ) -> FinancialResult:
        gross_cost = capacity_kw * 1000 * fp.cost_per_watt
        net_cost = gross_cost * (1 - fp.incentive_pct / 100)

        # Year-by-year cash flow
        cumulative = [-net_cost]
        annual_savings = []
        total_energy_lifetime = 0.0
        total_cost_lifetime = net_cost

        for year in range(1, fp.analysis_period + 1):
            deg_factor = (1 - fp.degradation / 100) ** year
            energy_year = annual_ac_kwh * deg_factor
            rate_year = fp.electricity_rate * (1 + fp.escalation / 100) ** year
            savings = energy_year * rate_year
            om = capacity_kw * fp.om_cost
            net_savings = savings - om
            annual_savings.append(round(net_savings, 2))
            cumulative.append(round(cumulative[-1] + net_savings, 2))
            total_energy_lifetime += energy_year

        # Payback year (linear interpolation)
        payback = fp.analysis_period + 1  # default: doesn't pay back
        for i in range(1, len(cumulative)):
            if cumulative[i] >= 0 and cumulative[i - 1] < 0:
                frac = -cumulative[i - 1] / (cumulative[i] - cumulative[i - 1])
                payback = (i - 1) + frac
                break

        # NPV
        npv = -net_cost
        for year in range(1, fp.analysis_period + 1):
            npv += annual_savings[year - 1] / (1 + fp.discount_rate / 100) ** year
        npv = round(npv, 2)

        # LCOE
        discounted_energy = sum(
            (annual_ac_kwh * (1 - fp.degradation / 100) ** y)
            / (1 + fp.discount_rate / 100) ** y
            for y in range(1, fp.analysis_period + 1)
        )
        om_npv = sum(
            (capacity_kw * fp.om_cost) / (1 + fp.discount_rate / 100) ** y
            for y in range(1, fp.analysis_period + 1)
        )
        lcoe = (net_cost + om_npv) / discounted_energy if discounted_energy > 0 else 0

        # IRR via scipy brentq
        irr = PVCalculator._compute_irr(net_cost, annual_savings)

        return FinancialResult(
            gross_cost=round(gross_cost, 2),
            net_cost=round(net_cost, 2),
            payback_years=round(payback, 1),
            npv=npv,
            irr=round(irr * 100, 1) if irr is not None else None,
            lcoe=round(lcoe, 4),
            annual_savings_year1=annual_savings[0] if annual_savings else 0,
            cumulative_cash_flow=cumulative,
            annual_savings_by_year=annual_savings,
        )

    @staticmethod
    def _compute_irr(net_cost: float, annual_savings: list[float]) -> float | None:
        """Compute IRR using scipy brentq."""
        from scipy.optimize import brentq

        cash_flows = [-net_cost] + annual_savings

        def npv_at_rate(r: float) -> float:
            return sum(cf / (1 + r) ** t for t, cf in enumerate(cash_flows))

        try:
            return brentq(npv_at_rate, -0.5, 5.0, xtol=1e-6)
        except (ValueError, RuntimeError):
            return None
