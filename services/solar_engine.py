from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pvlib
import streamlit as st

from models.solar import LocationConfig, SolarPosition, SunPath


class SolarEngine:
    """Deterministic solar position calculations using pvlib (NREL SPA)."""

    @staticmethod
    @st.cache_data(ttl=3600)
    def compute_position(
        location: LocationConfig, dt: datetime
    ) -> SolarPosition:
        ts = pd.Timestamp(dt, tz=location.timezone)
        solpos = pvlib.solarposition.get_solarposition(
            ts,
            location.latitude,
            location.longitude,
            method="nrel_numpy",
        )
        return SolarPosition(
            azimuth=float(solpos["azimuth"].iloc[0]),
            elevation=float(solpos["elevation"].iloc[0]),
            zenith=float(solpos["zenith"].iloc[0]),
            timestamp=ts.to_pydatetime(),
        )

    @staticmethod
    @st.cache_data(ttl=3600)
    def compute_sun_path(
        location: LocationConfig,
        target_date: date,
        interval_minutes: int = 5,
    ) -> SunPath:
        tz = location.timezone
        start = pd.Timestamp(
            datetime.combine(target_date, datetime.min.time()), tz=tz
        )
        end = start + pd.Timedelta(hours=23, minutes=59)
        times = pd.date_range(start, end, freq=f"{interval_minutes}min")

        solpos = pvlib.solarposition.get_solarposition(
            times,
            location.latitude,
            location.longitude,
            method="nrel_numpy",
        )

        positions: list[SolarPosition] = []
        for i in range(len(solpos)):
            positions.append(
                SolarPosition(
                    azimuth=float(solpos["azimuth"].iloc[i]),
                    elevation=float(solpos["elevation"].iloc[i]),
                    zenith=float(solpos["zenith"].iloc[i]),
                    timestamp=times[i].to_pydatetime(),
                )
            )

        # Find sunrise, sunset, solar noon
        above = [(p.timestamp, p.elevation) for p in positions if p.elevation > 0]
        sunrise = None
        sunset = None
        solar_noon = None
        day_length = 0.0

        if above:
            sunrise = above[0][0]
            sunset = above[-1][0]
            solar_noon_pos = max(above, key=lambda x: x[1])
            solar_noon = solar_noon_pos[0]
            day_length = (sunset - sunrise).total_seconds() / 3600.0

        return SunPath(
            positions=positions,
            sunrise=sunrise,
            sunset=sunset,
            solar_noon=solar_noon,
            day_length_hours=round(day_length, 2),
            date=target_date,
        )

    @staticmethod
    def sun_path_3d_coords(
        sun_path: SunPath, radius: float = 40.0
    ) -> tuple[list[float], list[float], list[float]]:
        """Convert sun path to 3D coordinates for visualization.
        Returns (xs, ys, zs) in X=East, Y=North, Z=Up."""
        xs, ys, zs = [], [], []
        for pos in sun_path.above_horizon:
            az_rad = np.radians(pos.azimuth)
            el_rad = np.radians(pos.elevation)
            x = radius * np.sin(az_rad) * np.cos(el_rad)
            y = radius * np.cos(az_rad) * np.cos(el_rad)
            z = radius * np.sin(el_rad)
            xs.append(float(x))
            ys.append(float(y))
            zs.append(float(z))
        return xs, ys, zs

    @staticmethod
    def sun_sphere_coords(
        position: SolarPosition, radius: float = 40.0
    ) -> tuple[float, float, float]:
        """Get 3D coordinates for the current sun position."""
        az_rad = np.radians(position.azimuth)
        el_rad = np.radians(position.elevation)
        x = radius * np.sin(az_rad) * np.cos(el_rad)
        y = radius * np.cos(az_rad) * np.cos(el_rad)
        z = radius * np.sin(el_rad)
        return float(x), float(y), float(z)
