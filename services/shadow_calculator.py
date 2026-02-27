from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull

from models.building import BuildingGeometry
from models.solar import ShadowResult, SolarPosition


class ShadowCalculator:
    """Project building vertices onto ground plane to compute shadow polygon."""

    @staticmethod
    def compute_shadow(
        geometry: BuildingGeometry,
        sun_position: SolarPosition,
        roof_vertices: list[tuple[float, float, float]],
        footprint_vertices: list[tuple[float, float]],
    ) -> ShadowResult | None:
        if not sun_position.is_above_horizon:
            return None

        az_rad = np.radians(sun_position.azimuth)
        el_rad = np.radians(sun_position.elevation)
        tan_el = np.tan(el_rad)

        if tan_el < 0.01:
            return None

        # Limit shadow projection to avoid extreme lengths at low sun angles
        max_shadow_reach = max(geometry.width, geometry.depth, geometry.wall_height) * 5

        # Project each elevated vertex onto the ground plane
        projected: list[tuple[float, float]] = []
        cx_bld = geometry.width / 2
        cy_bld = geometry.depth / 2
        for x, y, z in roof_vertices:
            if z > 0:
                shadow_x = x - z * (np.sin(az_rad) / tan_el)
                shadow_y = y - z * (np.cos(az_rad) / tan_el)
                # Clip to max reach from building center
                dx = shadow_x - cx_bld
                dy = shadow_y - cy_bld
                dist = np.sqrt(dx**2 + dy**2)
                if dist > max_shadow_reach:
                    scale = max_shadow_reach / dist
                    shadow_x = cx_bld + dx * scale
                    shadow_y = cy_bld + dy * scale
                projected.append((float(shadow_x), float(shadow_y)))

        # Combine footprint corners with projected roof vertices
        all_points = list(footprint_vertices) + projected

        if len(all_points) < 3:
            return None

        points_array = np.array(all_points)

        try:
            hull = ConvexHull(points_array)
            hull_vertices = [
                (float(points_array[i, 0]), float(points_array[i, 1]))
                for i in hull.vertices
            ]
        except Exception:
            hull_vertices = all_points
            hull = None

        # Shadow length: max distance from building center to any projected point
        cx = geometry.width / 2
        cy = geometry.depth / 2
        max_dist = 0.0
        farthest_point = (cx, cy)
        for px, py in projected:
            dist = np.sqrt((px - cx) ** 2 + (py - cy) ** 2)
            if dist > max_dist:
                max_dist = dist
                farthest_point = (px, py)

        shadow_length = float(max_dist)

        # Shadow area via ConvexHull
        shadow_area = float(hull.volume) if hull else 0.0  # 2D hull: volume = area

        # Shadow bearing: direction from building center to farthest shadow point
        dx = farthest_point[0] - cx
        dy = farthest_point[1] - cy
        bearing = float(np.degrees(np.arctan2(dx, dy))) % 360

        return ShadowResult(
            shadow_vertices=hull_vertices,
            shadow_length=round(shadow_length, 1),
            shadow_area=round(shadow_area, 1),
            shadow_bearing=round(bearing, 1),
            sun_position=sun_position,
        )
