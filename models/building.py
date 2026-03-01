from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RoofType = Literal[
    "flat", "gable", "hip", "shed", "mansard",
    "gambrel", "butterfly", "sawtooth", "dutch_gable",
]
Confidence = Literal["low", "medium", "high"]
GlazingType = Literal["none", "window", "glass_wall"]


class WallGlazing(BaseModel):
    """Glazing configuration for a single wall."""
    glazing_type: GlazingType = "none"
    window_width_frac: float = Field(0.5, ge=0.1, le=1.0, description="Window width as fraction of wall width")
    window_height_frac: float = Field(0.5, ge=0.1, le=1.0, description="Window height as fraction of wall height")
    sill_height_frac: float = Field(0.15, ge=0.0, le=0.9, description="Sill height as fraction of wall height")


class WindowConfig(BaseModel):
    """Glazing configuration for all four walls."""
    south: WallGlazing = Field(default_factory=WallGlazing)
    north: WallGlazing = Field(default_factory=WallGlazing)
    east: WallGlazing = Field(default_factory=WallGlazing)
    west: WallGlazing = Field(default_factory=WallGlazing)

    def has_any_glazing(self) -> bool:
        return any(
            w.glazing_type != "none"
            for w in [self.south, self.north, self.east, self.west]
        )


class NearbyStructure(BaseModel):
    type: Literal["tree", "fence", "wall", "shed", "garage", "other"] = "tree"
    description: str = ""
    relative_position: str = ""
    estimated_height: float = 3.0


class BuildingGeometry(BaseModel):
    width: float = Field(10.0, gt=0, description="East-west dimension in meters")
    depth: float = Field(8.0, gt=0, description="North-south dimension in meters")
    wall_height: float = Field(6.0, gt=0, description="Wall height in meters")
    roof_type: RoofType = "gable"
    roof_pitch: float = Field(
        30.0, ge=0, le=80, description="Roof pitch in degrees"
    )
    ridge_height: float = Field(
        0.0, ge=0, description="Extra height from roof peak above wall"
    )
    orientation: float = Field(
        0.0,
        ge=0,
        lt=360,
        description="Building rotation in degrees clockwise from north",
    )

    @property
    def total_height(self) -> float:
        if self.roof_type == "flat":
            return self.wall_height
        return self.wall_height + self.ridge_height

    def compute_ridge_height(self) -> float:
        """Compute ridge height from roof pitch and building width."""
        import numpy as np

        if self.roof_type == "flat":
            return 0.0
        if self.roof_type == "shed":
            return self.depth * np.tan(np.radians(self.roof_pitch))
        if self.roof_type == "butterfly":
            # Inverted V — valley depth below eaves
            return (self.width / 2) * np.tan(np.radians(self.roof_pitch))
        if self.roof_type == "gambrel":
            # Barn-style — steep lower + shallow upper
            lower = (self.width / 2) * 0.35 * np.tan(np.radians(min(self.roof_pitch + 20, 75)))
            upper = (self.width / 2) * 0.15 * np.tan(np.radians(self.roof_pitch))
            return lower + upper
        if self.roof_type == "sawtooth":
            return self.depth * 0.4 * np.tan(np.radians(self.roof_pitch))
        # gable, hip, mansard, dutch_gable: ridge rises over half the width
        return (self.width / 2) * np.tan(np.radians(self.roof_pitch))


class BuildingAnalysis(BaseModel):
    geometry: BuildingGeometry = Field(default_factory=BuildingGeometry)
    building_type: str = "residential"
    stories: int = Field(1, ge=1, le=100)
    materials: list[str] = Field(default_factory=list)
    confidence: Confidence = "medium"
    notes: str = ""
    nearby_structures: list[NearbyStructure] = Field(default_factory=list)
