from __future__ import annotations

import numpy as np

from models.building import BuildingGeometry


class GeometryBuilder:
    """Generate 3D mesh vertices and faces for parametric buildings."""

    @staticmethod
    def build_mesh(
        geom: BuildingGeometry,
    ) -> tuple[
        list[float],
        list[float],
        list[float],
        list[list[int]],
        list[tuple[float, float]],
        list[tuple[float, float, float]],
    ]:
        """Build a 3D mesh for the building.

        Returns:
            (x_verts, y_verts, z_verts, faces, footprint_2d, roof_vertices_3d)
            - faces: list of [i, j, k] triangle index triples
            - footprint_2d: ground-level corners
            - roof_vertices_3d: all vertices above ground (for shadow projection)
        """
        w = geom.width
        d = geom.depth
        h = geom.wall_height
        ridge = geom.compute_ridge_height()
        geom.ridge_height = ridge

        if geom.roof_type == "flat":
            result = GeometryBuilder._flat_roof(w, d, h)
        else:
            builders = {
                "gable": GeometryBuilder._gable_roof,
                "shed": GeometryBuilder._shed_roof,
                "hip": GeometryBuilder._hip_roof,
                "mansard": GeometryBuilder._mansard_roof,
                "gambrel": GeometryBuilder._gambrel_roof,
                "butterfly": GeometryBuilder._butterfly_roof,
                "sawtooth": GeometryBuilder._sawtooth_roof,
                "dutch_gable": GeometryBuilder._dutch_gable_roof,
            }
            builder = builders.get(geom.roof_type, GeometryBuilder._gable_roof)
            result = builder(w, d, h, ridge)

        if geom.orientation != 0.0:
            result = GeometryBuilder._apply_rotation(result, geom.orientation, w, d)

        return result

    @staticmethod
    def _apply_rotation(mesh_result, orientation_deg, w, d):
        """Rotate all mesh vertices around the building center by orientation degrees clockwise from North."""
        xs, ys, zs, faces, footprint, roof_verts = mesh_result
        cx, cy = w / 2, d / 2
        theta = np.radians(orientation_deg)
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)

        # Clockwise rotation in X-Y plane (Z unchanged)
        new_xs = [cx + (x - cx) * cos_t + (y - cy) * sin_t for x, y in zip(xs, ys)]
        new_ys = [cy - (x - cx) * sin_t + (y - cy) * cos_t for x, y in zip(xs, ys)]

        new_footprint = [
            (cx + (fx - cx) * cos_t + (fy - cy) * sin_t,
             cy - (fx - cx) * sin_t + (fy - cy) * cos_t)
            for fx, fy in footprint
        ]

        new_roof_verts = [
            (cx + (rx - cx) * cos_t + (ry - cy) * sin_t,
             cy - (rx - cx) * sin_t + (ry - cy) * cos_t,
             rz)
            for rx, ry, rz in roof_verts
        ]

        return new_xs, new_ys, zs, faces, new_footprint, new_roof_verts

    @staticmethod
    def _flat_roof(w, d, h):
        # 8 vertices: bottom 4 + top 4
        verts = [
            (0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0),  # bottom
            (0, 0, h), (w, 0, h), (w, d, h), (0, d, h),  # top
        ]
        faces = [
            # Bottom
            [0, 1, 2], [0, 2, 3],
            # Top
            [4, 5, 6], [4, 6, 7],
            # Front (y=0)
            [0, 1, 5], [0, 5, 4],
            # Back (y=d)
            [2, 3, 7], [2, 7, 6],
            # Left (x=0)
            [0, 3, 7], [0, 7, 4],
            # Right (x=w)
            [1, 2, 6], [1, 6, 5],
        ]
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        footprint = [(0, 0), (w, 0), (w, d), (0, d)]
        roof_verts = [v for v in verts if v[2] > 0]
        return xs, ys, zs, faces, footprint, roof_verts

    @staticmethod
    def _gable_roof(w, d, h, ridge):
        # 10 vertices: bottom 4, wall top 4, ridge 2
        verts = [
            (0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0),           # 0-3 bottom
            (0, 0, h), (w, 0, h), (w, d, h), (0, d, h),           # 4-7 wall top
            (w / 2, 0, h + ridge), (w / 2, d, h + ridge),          # 8-9 ridge
        ]
        faces = [
            # Bottom
            [0, 1, 2], [0, 2, 3],
            # Front wall (y=0)
            [0, 1, 5], [0, 5, 4],
            # Back wall (y=d)
            [2, 3, 7], [2, 7, 6],
            # Left wall (x=0)
            [0, 3, 7], [0, 7, 4],
            # Right wall (x=w)
            [1, 2, 6], [1, 6, 5],
            # Front gable triangle
            [4, 5, 8],
            # Back gable triangle
            [6, 7, 9],
            # Left roof slope
            [4, 8, 9], [4, 9, 7],
            # Right roof slope
            [5, 8, 9], [5, 9, 6],
        ]
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        footprint = [(0, 0), (w, 0), (w, d), (0, d)]
        roof_verts = [v for v in verts if v[2] > 0]
        return xs, ys, zs, faces, footprint, roof_verts

    @staticmethod
    def _shed_roof(w, d, h, ridge):
        # Shed roof: slopes from front (high) to back (low) or similar
        # High side at y=0, low side at y=d
        verts = [
            (0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0),               # 0-3 bottom
            (0, 0, h + ridge), (w, 0, h + ridge),                       # 4-5 high wall
            (w, d, h), (0, d, h),                                        # 6-7 low wall
        ]
        faces = [
            # Bottom
            [0, 1, 2], [0, 2, 3],
            # Front wall (y=0, tall)
            [0, 1, 5], [0, 5, 4],
            # Back wall (y=d, short)
            [2, 3, 7], [2, 7, 6],
            # Left wall
            [0, 3, 7], [0, 7, 4],
            # Right wall
            [1, 2, 6], [1, 6, 5],
            # Roof (sloped plane)
            [4, 5, 6], [4, 6, 7],
        ]
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        footprint = [(0, 0), (w, 0), (w, d), (0, d)]
        roof_verts = [v for v in verts if v[2] > 0]
        return xs, ys, zs, faces, footprint, roof_verts

    @staticmethod
    def _hip_roof(w, d, h, ridge):
        # Hip roof: 4 sloping sides meeting at a ridge line
        inset = min(w, d) / 2
        ridge_len = max(0, d - 2 * inset) if d > w else max(0, w - 2 * inset)

        if d >= w:
            # Ridge runs along Y axis
            verts = [
                (0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0),           # 0-3 bottom
                (0, 0, h), (w, 0, h), (w, d, h), (0, d, h),           # 4-7 wall top
                (w / 2, inset, h + ridge),                               # 8 ridge front
                (w / 2, d - inset, h + ridge),                           # 9 ridge back
            ]
        else:
            verts = [
                (0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0),
                (0, 0, h), (w, 0, h), (w, d, h), (0, d, h),
                (inset, d / 2, h + ridge),
                (w - inset, d / 2, h + ridge),
            ]

        faces = [
            # Bottom
            [0, 1, 2], [0, 2, 3],
            # Front wall
            [0, 1, 5], [0, 5, 4],
            # Back wall
            [2, 3, 7], [2, 7, 6],
            # Left wall
            [0, 3, 7], [0, 7, 4],
            # Right wall
            [1, 2, 6], [1, 6, 5],
            # Front hip
            [4, 5, 8],
            # Back hip
            [6, 7, 9],
            # Left slope
            [4, 8, 9], [4, 9, 7],
            # Right slope
            [5, 8, 9], [5, 9, 6],
        ]
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        footprint = [(0, 0), (w, 0), (w, d), (0, d)]
        roof_verts = [v for v in verts if v[2] > 0]
        return xs, ys, zs, faces, footprint, roof_verts

    @staticmethod
    def _mansard_roof(w, d, h, ridge):
        # Mansard: steep lower slope, shallow upper slope
        inset = w * 0.15
        lower_rise = ridge * 0.7
        upper_rise = ridge * 0.3
        mid_h = h + lower_rise
        top_h = h + ridge

        verts = [
            (0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0),                       # 0-3 bottom
            (0, 0, h), (w, 0, h), (w, d, h), (0, d, h),                       # 4-7 wall top
            (inset, inset, mid_h), (w - inset, inset, mid_h),                   # 8-9 lower break front
            (w - inset, d - inset, mid_h), (inset, d - inset, mid_h),           # 10-11 lower break back
            (inset, inset, top_h), (w - inset, inset, top_h),                   # 12-13 top front
            (w - inset, d - inset, top_h), (inset, d - inset, top_h),           # 14-15 top back
        ]
        faces = [
            # Bottom
            [0, 1, 2], [0, 2, 3],
            # Front wall
            [0, 1, 5], [0, 5, 4],
            # Back wall
            [2, 3, 7], [2, 7, 6],
            # Left wall
            [0, 3, 7], [0, 7, 4],
            # Right wall
            [1, 2, 6], [1, 6, 5],
            # Front lower mansard
            [4, 5, 9], [4, 9, 8],
            # Back lower mansard
            [6, 7, 11], [6, 11, 10],
            # Left lower mansard
            [4, 8, 11], [4, 11, 7],
            # Right lower mansard
            [5, 9, 10], [5, 10, 6],
            # Front upper
            [8, 9, 13], [8, 13, 12],
            # Back upper
            [10, 11, 15], [10, 15, 14],
            # Left upper
            [8, 12, 15], [8, 15, 11],
            # Right upper
            [9, 13, 14], [9, 14, 10],
            # Top flat
            [12, 13, 14], [12, 14, 15],
        ]
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        footprint = [(0, 0), (w, 0), (w, d), (0, d)]
        roof_verts = [v for v in verts if v[2] > 0]
        return xs, ys, zs, faces, footprint, roof_verts

    @staticmethod
    def _gambrel_roof(w, d, h, ridge):
        """Barn-style roof: steep lower slopes, shallow upper slopes on each side."""
        # Lower slope occupies 35% of half-width, upper slope the remaining 15%
        lower_x = w * 0.35
        lower_rise = ridge * 0.65
        mid_h = h + lower_rise
        top_h = h + ridge

        verts = [
            (0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0),                     # 0-3 bottom
            (0, 0, h), (w, 0, h), (w, d, h), (0, d, h),                     # 4-7 wall top
            (lower_x, 0, mid_h), (w - lower_x, 0, mid_h),                    # 8-9 break front
            (w - lower_x, d, mid_h), (lower_x, d, mid_h),                    # 10-11 break back
            (w / 2, 0, top_h), (w / 2, d, top_h),                            # 12-13 ridge
        ]
        faces = [
            # Bottom
            [0, 1, 2], [0, 2, 3],
            # Front wall
            [0, 1, 5], [0, 5, 4],
            # Back wall
            [2, 3, 7], [2, 7, 6],
            # Left wall
            [0, 3, 7], [0, 7, 4],
            # Right wall
            [1, 2, 6], [1, 6, 5],
            # Front gable (lower left, lower right, upper left, upper right, peak)
            [4, 8, 12], [5, 9, 12], [8, 9, 12],
            # Back gable
            [7, 11, 13], [6, 10, 13], [11, 10, 13],
            # Left lower slope
            [4, 8, 11], [4, 11, 7],
            # Right lower slope
            [5, 9, 10], [5, 10, 6],
            # Left upper slope
            [8, 12, 13], [8, 13, 11],
            # Right upper slope
            [9, 12, 13], [9, 13, 10],
        ]
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        footprint = [(0, 0), (w, 0), (w, d), (0, d)]
        roof_verts = [v for v in verts if v[2] > 0]
        return xs, ys, zs, faces, footprint, roof_verts

    @staticmethod
    def _butterfly_roof(w, d, h, ridge):
        """Inverted V-shape: two surfaces slope inward toward a central valley."""
        valley_drop = ridge  # valley is lower than eaves
        eave_h = h + ridge
        valley_h = h

        verts = [
            (0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0),                     # 0-3 bottom
            (0, 0, eave_h), (w, 0, eave_h), (w, d, eave_h), (0, d, eave_h), # 4-7 high eaves
            (w / 2, 0, valley_h), (w / 2, d, valley_h),                       # 8-9 valley line
        ]
        faces = [
            # Bottom
            [0, 1, 2], [0, 2, 3],
            # Front wall
            [0, 1, 5], [0, 5, 4],
            # Back wall
            [2, 3, 7], [2, 7, 6],
            # Left wall (tall)
            [0, 3, 7], [0, 7, 4],
            # Right wall (tall)
            [1, 2, 6], [1, 6, 5],
            # Front V
            [4, 5, 8],
            # Back V
            [6, 7, 9],
            # Left slope (slopes down toward center)
            [4, 8, 9], [4, 9, 7],
            # Right slope (slopes down toward center)
            [5, 8, 9], [5, 9, 6],
        ]
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        footprint = [(0, 0), (w, 0), (w, d), (0, d)]
        roof_verts = [v for v in verts if v[2] > 0]
        return xs, ys, zs, faces, footprint, roof_verts

    @staticmethod
    def _sawtooth_roof(w, d, h, ridge):
        """Industrial sawtooth: repeating asymmetric ridges along depth axis."""
        n_teeth = max(2, round(d / (w * 0.4)))
        tooth_d = d / n_teeth

        all_verts = []
        all_faces = []

        # Base box vertices (0-7)
        base = [
            (0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0),
            (0, 0, h), (w, 0, h), (w, d, h), (0, d, h),
        ]
        all_verts.extend(base)
        all_faces.extend([
            [0, 1, 2], [0, 2, 3],
            [0, 1, 5], [0, 5, 4],
            [2, 3, 7], [2, 7, 6],
            [0, 3, 7], [0, 7, 4],
            [1, 2, 6], [1, 6, 5],
        ])

        # Add sawtooth ridges on top
        for t in range(n_teeth):
            y_start = t * tooth_d
            y_end = y_start + tooth_d
            offset = len(all_verts)

            # 4 vertices per tooth: low-front, high-front (vertical face), high-back, low-back
            tooth_verts = [
                (0, y_start, h),               # 0: low left front
                (w, y_start, h),               # 1: low right front
                (0, y_start, h + ridge),       # 2: high left front
                (w, y_start, h + ridge),       # 3: high right front
                (0, y_end, h),                 # 4: low left back
                (w, y_end, h),                 # 5: low right back
            ]
            all_verts.extend(tooth_verts)

            o = offset
            all_faces.extend([
                # Vertical face (front of tooth)
                [o, o + 1, o + 3], [o, o + 3, o + 2],
                # Sloped surface (from high front to low back)
                [o + 2, o + 3, o + 5], [o + 2, o + 5, o + 4],
                # Left side triangle
                [o, o + 2, o + 4],
                # Right side triangle
                [o + 1, o + 3, o + 5],
            ])

        xs = [v[0] for v in all_verts]
        ys = [v[1] for v in all_verts]
        zs = [v[2] for v in all_verts]
        footprint = [(0, 0), (w, 0), (w, d), (0, d)]
        roof_verts = [v for v in all_verts if v[2] > 0]
        return xs, ys, zs, all_faces, footprint, roof_verts

    @staticmethod
    def _dutch_gable_roof(w, d, h, ridge):
        """Dutch gable: hip roof with small gable (vertical triangle) at each end."""
        inset = min(w, d) * 0.25
        gable_h = ridge * 0.35  # small gable portion at top

        hip_ridge_h = h + ridge - gable_h
        peak_h = h + ridge

        verts = [
            (0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0),                     # 0-3 bottom
            (0, 0, h), (w, 0, h), (w, d, h), (0, d, h),                     # 4-7 wall top
            # Hip section endpoints (lower ridge)
            (w / 2, inset, hip_ridge_h),                                       # 8 front hip
            (w / 2, d - inset, hip_ridge_h),                                   # 9 back hip
            # Gable ridge (top)
            (w / 2, inset, peak_h),                                            # 10 front peak
            (w / 2, d - inset, peak_h),                                        # 11 back peak
        ]
        faces = [
            # Bottom
            [0, 1, 2], [0, 2, 3],
            # Front wall
            [0, 1, 5], [0, 5, 4],
            # Back wall
            [2, 3, 7], [2, 7, 6],
            # Left wall
            [0, 3, 7], [0, 7, 4],
            # Right wall
            [1, 2, 6], [1, 6, 5],
            # Front hip slope
            [4, 5, 8],
            # Back hip slope
            [6, 7, 9],
            # Left lower slope
            [4, 8, 9], [4, 9, 7],
            # Right lower slope
            [5, 8, 9], [5, 9, 6],
            # Front gable triangle (vertical)
            [8, 10, 10],  # degenerate — use proper triangle below
            # Upper gable ridge section
            # Left upper slope
            [8, 10, 11], [8, 11, 9],
            # Right upper slope
            [8, 10, 11], [9, 11, 8],
            # Front gable vertical face
            [8, 10, 10],
            # Back gable vertical face
            [9, 11, 11],
        ]

        # Clean up: use proper small vertical triangles for gable ends
        # Front gable: 3 points at hip level + peak
        faces = [
            # Bottom
            [0, 1, 2], [0, 2, 3],
            # Walls
            [0, 1, 5], [0, 5, 4],
            [2, 3, 7], [2, 7, 6],
            [0, 3, 7], [0, 7, 4],
            [1, 2, 6], [1, 6, 5],
            # Front hip triangle
            [4, 5, 8],
            # Back hip triangle
            [6, 7, 9],
            # Left roof slope (wall to hip ridge)
            [4, 8, 9], [4, 9, 7],
            # Right roof slope
            [5, 8, 9], [5, 9, 6],
            # Left upper gable slope
            [8, 10, 11], [8, 11, 9],
            # Right upper gable slope (same faces, other side is same plane)
        ]

        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        footprint = [(0, 0), (w, 0), (w, d), (0, d)]
        roof_verts = [v for v in verts if v[2] > 0]
        return xs, ys, zs, faces, footprint, roof_verts

    @staticmethod
    def build_nearby_structure(
        struct_type: str, height: float, position: tuple[float, float]
    ) -> tuple[list[float], list[float], list[float], list[list[int]]]:
        """Build simple geometry for nearby structures."""
        px, py = position

        if struct_type == "tree":
            # Cylinder trunk + cone canopy approximated as octagonal prism + pyramid
            r = 1.5
            trunk_h = height * 0.4
            n = 8
            angles = [2 * np.pi * i / n for i in range(n)]

            verts = []
            # Bottom ring
            for a in angles:
                verts.append((px + r * 0.3 * np.cos(a), py + r * 0.3 * np.sin(a), 0))
            # Trunk top ring
            for a in angles:
                verts.append(
                    (px + r * 0.3 * np.cos(a), py + r * 0.3 * np.sin(a), trunk_h)
                )
            # Canopy bottom ring
            for a in angles:
                verts.append(
                    (px + r * np.cos(a), py + r * np.sin(a), trunk_h)
                )
            # Canopy top
            verts.append((px, py, height))

            faces = []
            # Trunk sides
            for i in range(n):
                j = (i + 1) % n
                faces.append([i, j, j + n])
                faces.append([i, j + n, i + n])
            # Canopy sides
            top_idx = 3 * n
            base = 2 * n
            for i in range(n):
                j = (i + 1) % n
                faces.append([base + i, base + j, top_idx])

            xs = [v[0] for v in verts]
            ys = [v[1] for v in verts]
            zs = [v[2] for v in verts]
            return xs, ys, zs, faces

        else:
            # Generic box shape for fences, walls, sheds, etc.
            size = 1.0 if struct_type == "fence" else 2.0
            fence_h = min(height, 2.0) if struct_type == "fence" else height
            verts = [
                (px, py, 0),
                (px + size, py, 0),
                (px + size, py + size, 0),
                (px, py + size, 0),
                (px, py, fence_h),
                (px + size, py, fence_h),
                (px + size, py + size, fence_h),
                (px, py + size, fence_h),
            ]
            faces = [
                [0, 1, 2], [0, 2, 3],
                [4, 5, 6], [4, 6, 7],
                [0, 1, 5], [0, 5, 4],
                [2, 3, 7], [2, 7, 6],
                [0, 3, 7], [0, 7, 4],
                [1, 2, 6], [1, 6, 5],
            ]
            xs = [v[0] for v in verts]
            ys = [v[1] for v in verts]
            zs = [v[2] for v in verts]
            return xs, ys, zs, faces
