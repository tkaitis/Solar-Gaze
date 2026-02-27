from __future__ import annotations

from datetime import date, datetime
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field


class LocationConfig(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "America/Los_Angeles"
    name: str = ""


class SolarPosition(BaseModel):
    azimuth: float = Field(description="Degrees from north, clockwise")
    elevation: float = Field(description="Degrees above horizon")
    zenith: float = Field(description="Degrees from vertical")
    timestamp: datetime

    @property
    def is_above_horizon(self) -> bool:
        return self.elevation > 0

    def sun_direction_vector(self) -> tuple[float, float, float]:
        """Unit vector FROM sun TO ground (for shadow projection).
        Coordinate system: X=East, Y=North, Z=Up."""
        az_rad = np.radians(self.azimuth)
        el_rad = np.radians(self.elevation)
        # Sun direction in X=East, Y=North
        dx = -np.sin(az_rad) * np.cos(el_rad)
        dy = -np.cos(az_rad) * np.cos(el_rad)
        dz = -np.sin(el_rad)
        return (float(dx), float(dy), float(dz))


class SunPath(BaseModel):
    positions: list[SolarPosition]
    sunrise: datetime | None = None
    sunset: datetime | None = None
    solar_noon: datetime | None = None
    day_length_hours: float = 0.0
    date: date

    @property
    def above_horizon(self) -> list[SolarPosition]:
        return [p for p in self.positions if p.is_above_horizon]


class ShadowResult(BaseModel):
    shadow_vertices: list[tuple[float, float]] = Field(
        description="2D polygon vertices (x, y) on ground plane"
    )
    shadow_length: float = Field(description="Maximum shadow extent in meters")
    shadow_area: float = Field(description="Shadow polygon area in m²")
    shadow_bearing: float = Field(
        description="Direction shadow points, degrees from north"
    )
    sun_position: SolarPosition
