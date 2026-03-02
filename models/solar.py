from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class LocationConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "America/Los_Angeles"
    name: str = ""


class SolarPosition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    azimuth: float = Field(description="Degrees from north, clockwise")
    elevation: float = Field(description="Degrees above horizon")
    zenith: float = Field(description="Degrees from vertical")
    timestamp: Any  # datetime, but accept cached/deserialized variants

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
    model_config = ConfigDict(arbitrary_types_allowed=True)
    positions: list[SolarPosition]
    sunrise: Any = None
    sunset: Any = None
    solar_noon: Any = None
    day_length_hours: float = 0.0
    date: Any  # date, but accept cached/deserialized variants

    @property
    def above_horizon(self) -> list[SolarPosition]:
        return [p for p in self.positions if p.is_above_horizon]


class LightPatchResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    """Sun light patch projected onto the interior floor through a window."""
    wall_name: str = Field(description="Which wall: south, north, east, west")
    patch_vertices: list = Field(
        description="2D polygon vertices (x, y) on the interior floor"
    )
    patch_area: float = Field(description="Light patch area in m²")
    window_corners_3d: list = Field(
        description="4 corners of the window aperture in 3D for rendering"
    )


class ShadowResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    shadow_vertices: list = Field(
        description="2D polygon vertices (x, y) on ground plane"
    )
    shadow_length: float = Field(description="Maximum shadow extent in meters")
    shadow_area: float = Field(description="Shadow polygon area in m²")
    shadow_bearing: float = Field(
        description="Direction shadow points, degrees from north"
    )
    sun_position: Any  # SolarPosition, accept cached/deserialized variants
