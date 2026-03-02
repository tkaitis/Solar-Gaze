"""Pydantic models for PV feasibility analysis."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PanelSpec(BaseModel):
    rated_power_w: float = Field(400.0, gt=0, description="Panel rated power in watts (STC)")
    efficiency_pct: float = Field(21.0, gt=0, le=100, description="Panel efficiency %")
    temp_coeff_pmax: float = Field(-0.35, le=0, description="Temperature coefficient of Pmax (%/C)")
    noct_c: float = Field(45.0, gt=0, description="Nominal Operating Cell Temperature (C)")
    panel_area_m2: float = Field(1.92, gt=0, description="Single panel area in m2")


class RoofPVConfig(BaseModel):
    tilt_deg: float = Field(30.0, ge=0, le=90, description="Array tilt in degrees")
    azimuth_deg: float = Field(180.0, ge=0, lt=360, description="Array azimuth (180=south)")
    usable_roof_pct: float = Field(70.0, gt=0, le=100, description="Usable roof area %")
    auto_tilt: bool = Field(True, description="Auto-set tilt to abs(latitude)")
    auto_azimuth: bool = Field(True, description="Auto-set azimuth (180 NH, 0 SH)")


class SystemLosses(BaseModel):
    soiling: float = Field(2.0, ge=0, le=50, description="Soiling loss %")
    shading: float = Field(3.0, ge=0, le=50, description="Shading loss %")
    mismatch: float = Field(2.0, ge=0, le=50, description="Module mismatch loss %")
    wiring_dc: float = Field(2.0, ge=0, le=50, description="DC wiring loss %")
    wiring_ac: float = Field(1.0, ge=0, le=50, description="AC wiring loss %")
    inverter_eff: float = Field(96.0, gt=0, le=100, description="Inverter efficiency %")
    availability: float = Field(99.0, gt=0, le=100, description="System availability %")

    @property
    def total_derate_factor(self) -> float:
        """Overall AC derate factor (0 to 1)."""
        factor = 1.0
        for loss in [self.soiling, self.shading, self.mismatch, self.wiring_dc, self.wiring_ac]:
            factor *= (1 - loss / 100)
        factor *= self.inverter_eff / 100
        factor *= self.availability / 100
        return factor


class FinancialParams(BaseModel):
    electricity_rate: float = Field(0.15, ge=0, description="Electricity rate $/kWh")
    escalation: float = Field(2.5, ge=0, le=20, description="Annual electricity price escalation %")
    cost_per_watt: float = Field(2.80, ge=0, description="Installed cost per watt $")
    incentive_pct: float = Field(30.0, ge=0, le=100, description="Federal/state incentive %")
    degradation: float = Field(0.5, ge=0, le=5, description="Annual panel degradation %")
    discount_rate: float = Field(5.0, ge=0, le=30, description="Discount rate for NPV %")
    analysis_period: int = Field(25, ge=1, le=40, description="Analysis period in years")
    om_cost: float = Field(20.0, ge=0, description="Annual O&M cost per kW $")


class MonthlyPVResult(BaseModel):
    month: int
    ghi_kwh_m2: float
    poa_kwh_m2: float
    dc_energy_kwh: float
    ac_energy_kwh: float
    avg_cell_temp: float
    peak_sun_hours: float


class AnnualPVResult(BaseModel):
    system_capacity_kw: float
    num_panels: int
    total_panel_area_m2: float
    annual_ghi_kwh_m2: float
    annual_poa_kwh_m2: float
    annual_dc_kwh: float
    annual_ac_kwh: float
    specific_yield_kwh_kwp: float
    capacity_factor_pct: float
    monthly: list[MonthlyPVResult]
    hourly_poa_matrix: list[list[float]]  # 12 months x 24 hours
    hourly_dc_matrix: list[list[float]]   # 12 months x 24 hours


class FinancialResult(BaseModel):
    gross_cost: float
    net_cost: float
    payback_years: float
    npv: float
    irr: float | None
    lcoe: float
    annual_savings_year1: float
    cumulative_cash_flow: list[float]  # length = analysis_period + 1
    annual_savings_by_year: list[float]


class PVFeasibilityResult(BaseModel):
    energy: AnnualPVResult
    financial: FinancialResult
