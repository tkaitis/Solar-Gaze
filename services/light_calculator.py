"""Compute interior sun light patches projected through windows onto the floor."""

from __future__ import annotations

import numpy as np

from models.building import BuildingGeometry, WindowConfig, WallGlazing
from models.solar import LightPatchResult, SolarPosition


class LightCalculator:
    """Project sunlight through windows onto the building's interior floor."""

    # Unrotated wall definitions: (outward_normal, wall_origin, wall_u, wall_v)
    # wall_origin is bottom-left corner when facing the wall from outside.
    # wall_u is horizontal direction along the wall, wall_v is vertical (up).
    # These are defined for a building with corners at (0,0) to (w,d), height h.

    @staticmethod
    def compute_light_patches(
        geometry: BuildingGeometry,
        sun_position: SolarPosition,
        window_config: WindowConfig,
    ) -> list[LightPatchResult]:
        if not sun_position.is_above_horizon:
            return []

        el_rad = np.radians(sun_position.elevation)
        tan_el = np.tan(el_rad)
        if tan_el < 0.01:
            return []

        w = geometry.width
        d = geometry.depth
        h = geometry.wall_height
        az_rad = np.radians(sun_position.azimuth)
        orient_rad = np.radians(geometry.orientation)

        # Building center for rotation
        cx, cy = w / 2, d / 2

        # Wall definitions in unrotated building space:
        # (name, outward_normal_2d, origin_3d, u_vec_3d, v_vec_3d, wall_width, wall_height)
        walls = [
            ("south", (0, -1), (0, 0, 0), (1, 0, 0), (0, 0, 1), w, h),
            ("north", (0, 1), (w, d, 0), (-1, 0, 0), (0, 0, 1), w, h),
            ("east", (1, 0), (w, 0, 0), (0, 1, 0), (0, 0, 1), d, h),
            ("west", (-1, 0), (0, d, 0), (0, -1, 0), (0, 0, 1), d, h),
        ]

        glazings = {
            "south": window_config.south,
            "north": window_config.north,
            "east": window_config.east,
            "west": window_config.west,
        }

        results = []
        for name, normal_2d, origin, u_vec, v_vec, wall_w, wall_h in walls:
            glazing = glazings[name]
            if glazing.glazing_type == "none":
                continue

            # Rotate outward normal by building orientation
            rn = _rotate_2d(normal_2d[0], normal_2d[1], orient_rad)
            # Inward normal
            inward = (-rn[0], -rn[1])

            # Sun horizontal direction (direction sun shines toward = negative of sun_direction_vector horizontal)
            # sun_direction_vector points FROM sun TO ground, so horizontal component is the shadow direction.
            # We want the direction light travels horizontally: same as sun_direction_vector xy.
            sun_dx = -np.sin(az_rad) * np.cos(el_rad)
            sun_dy = -np.cos(az_rad) * np.cos(el_rad)

            # Dot product of sun horizontal direction with inward normal
            # If positive, sun shines into this wall
            dot = sun_dx * inward[0] + sun_dy * inward[1]
            if dot <= 0:
                continue

            # Compute window aperture corners in 3D (unrotated)
            corners = _window_corners_3d(
                glazing, origin, u_vec, v_vec, wall_w, wall_h
            )

            # Apply building rotation to corners
            rotated_corners = [
                _rotate_point_3d(p, cx, cy, orient_rad) for p in corners
            ]

            # Project each window corner onto z=0 floor
            projected = []
            for wx, wy, wz in rotated_corners:
                if wz <= 0:
                    continue
                floor_x = wx - wz * np.sin(az_rad) / tan_el
                floor_y = wy - wz * np.cos(az_rad) / tan_el
                projected.append((float(floor_x), float(floor_y)))

            if len(projected) < 3:
                continue

            # Clip to building footprint (rotated)
            footprint = _rotated_footprint(w, d, cx, cy, orient_rad)
            clipped = _sutherland_hodgman_clip(projected, footprint)

            if len(clipped) < 3:
                continue

            area = _polygon_area(clipped)
            if area < 0.01:
                continue

            results.append(LightPatchResult(
                wall_name=name,
                patch_vertices=clipped,
                patch_area=round(area, 2),
                window_corners_3d=rotated_corners,
            ))

        return results


def _rotate_2d(x: float, y: float, theta: float) -> tuple[float, float]:
    """Rotate a 2D vector clockwise by theta radians."""
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    return (float(x * cos_t + y * sin_t), float(-x * sin_t + y * cos_t))


def _rotate_point_3d(
    point: tuple[float, float, float],
    cx: float, cy: float,
    theta: float,
) -> tuple[float, float, float]:
    """Rotate a 3D point around (cx, cy) in the XY plane by theta (clockwise)."""
    x, y, z = point
    dx, dy = x - cx, y - cy
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    rx = cx + dx * cos_t + dy * sin_t
    ry = cy - dx * sin_t + dy * cos_t
    return (float(rx), float(ry), float(z))


def _window_corners_3d(
    glazing: WallGlazing,
    origin: tuple[float, float, float],
    u_vec: tuple[float, float, float],
    v_vec: tuple[float, float, float],
    wall_w: float,
    wall_h: float,
) -> list[tuple[float, float, float]]:
    """Compute 4 corners of window aperture in unrotated 3D space.

    Returns corners in order: bottom-left, bottom-right, top-right, top-left.
    """
    ox, oy, oz = origin
    ux, uy, uz = u_vec
    vx, vy, vz = v_vec

    if glazing.glazing_type == "glass_wall":
        # Full wall opening (small margin)
        u_start, u_end = 0.02, 0.98
        v_start, v_end = 0.02, 0.98
    else:
        # Window: centered horizontally, positioned by sill height
        wf = glazing.window_width_frac
        hf = glazing.window_height_frac
        sf = glazing.sill_height_frac
        # Clamp so window doesn't exceed wall
        hf = min(hf, 1.0 - sf)
        u_start = (1 - wf) / 2
        u_end = u_start + wf
        v_start = sf
        v_end = sf + hf

    def _pt(u_frac: float, v_frac: float) -> tuple[float, float, float]:
        return (
            float(ox + ux * wall_w * u_frac + vx * wall_h * v_frac),
            float(oy + uy * wall_w * u_frac + vy * wall_h * v_frac),
            float(oz + uz * wall_w * u_frac + vz * wall_h * v_frac),
        )

    return [
        _pt(u_start, v_start),  # bottom-left
        _pt(u_end, v_start),    # bottom-right
        _pt(u_end, v_end),      # top-right
        _pt(u_start, v_end),    # top-left
    ]


def _rotated_footprint(
    w: float, d: float, cx: float, cy: float, theta: float
) -> list[tuple[float, float]]:
    """Get the 4 corners of the building footprint, rotated."""
    corners = [(0, 0), (w, 0), (w, d), (0, d)]
    rotated = []
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    for x, y in corners:
        dx, dy = x - cx, y - cy
        rx = cx + dx * cos_t + dy * sin_t
        ry = cy - dx * sin_t + dy * cos_t
        rotated.append((float(rx), float(ry)))
    return rotated


def _sutherland_hodgman_clip(
    subject: list[tuple[float, float]],
    clip_polygon: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Clip a polygon by a convex clipping polygon using Sutherland-Hodgman."""
    output = list(subject)

    for i in range(len(clip_polygon)):
        if len(output) == 0:
            return []

        edge_start = clip_polygon[i]
        edge_end = clip_polygon[(i + 1) % len(clip_polygon)]

        input_list = output
        output = []

        for j in range(len(input_list)):
            current = input_list[j]
            prev = input_list[j - 1]

            curr_inside = _is_inside(current, edge_start, edge_end)
            prev_inside = _is_inside(prev, edge_start, edge_end)

            if curr_inside:
                if not prev_inside:
                    output.append(_line_intersect(prev, current, edge_start, edge_end))
                output.append(current)
            elif prev_inside:
                output.append(_line_intersect(prev, current, edge_start, edge_end))

    return output


def _is_inside(
    point: tuple[float, float],
    edge_start: tuple[float, float],
    edge_end: tuple[float, float],
) -> bool:
    """Test if a point is on the inside (left) of a directed edge."""
    return (
        (edge_end[0] - edge_start[0]) * (point[1] - edge_start[1])
        - (edge_end[1] - edge_start[1]) * (point[0] - edge_start[0])
    ) >= 0


def _line_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> tuple[float, float]:
    """Intersection of line p1-p2 with line p3-p4."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-12:
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return (float(x1 + t * (x2 - x1)), float(y1 + t * (y2 - y1)))


def _polygon_area(vertices: list[tuple[float, float]]) -> float:
    """Compute area of a simple polygon using the shoelace formula."""
    n = len(vertices)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0
