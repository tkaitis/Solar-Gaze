from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from models.building import BuildingGeometry, NearbyStructure
from models.solar import ShadowResult, SolarPosition, SunPath
from services.geometry_builder import GeometryBuilder
from services.solar_engine import SolarEngine
from visualization.color_themes import COLORS


class Scene3D:
    """Assemble a Plotly 3D figure with building, sun path, and shadows."""

    def __init__(self):
        self.fig = go.Figure()

    def build_scene(
        self,
        geometry: BuildingGeometry,
        sun_position: SolarPosition | None,
        sun_path: SunPath | None,
        shadow: ShadowResult | None,
        nearby: list[NearbyStructure] | None = None,
    ) -> go.Figure:
        self.fig = go.Figure()
        self._compute_sizes(geometry)

        self._add_ground_plane(geometry)
        self._add_compass_rose(geometry)
        self._add_building(geometry)

        if nearby:
            self._add_nearby_structures(nearby, geometry)

        if sun_path:
            self._add_sun_path(sun_path)

        if sun_position and sun_position.is_above_horizon:
            self._add_sun_sphere(sun_position)

        if shadow:
            self._add_shadow(shadow)

        self._configure_layout(geometry)
        return self.fig

    def build_animated_scene(
        self,
        geometry: BuildingGeometry,
        sun_path: SunPath,
        anim_positions: list[SolarPosition],
        anim_shadows: list[ShadowResult | None],
        nearby: list[NearbyStructure] | None = None,
    ) -> go.Figure:
        """Build a scene with Plotly animation frames for smooth client-side playback."""
        self.fig = go.Figure()
        self._compute_sizes(geometry)

        # Static traces
        self._add_ground_plane(geometry)
        self._add_compass_rose(geometry)
        self._add_building(geometry)

        if nearby:
            self._add_nearby_structures(nearby, geometry)

        self._add_sun_path(sun_path)

        # Record static trace count — dynamic traces come after this
        n_static = len(self.fig.data)

        # Add initial dynamic traces: sun marker, sun ray, shadow
        first_pos = anim_positions[0] if anim_positions else None
        first_shadow = anim_shadows[0] if anim_shadows else None

        if first_pos:
            sx, sy, sz = SolarEngine.sun_sphere_coords(first_pos, self.sun_radius)
        else:
            sx, sy, sz = 0, 0, 0

        # Dynamic trace 0: Sun marker (index n_static)
        self.fig.add_trace(
            go.Scatter3d(
                x=[sx], y=[sy], z=[sz],
                mode="markers",
                marker=dict(size=12, color=COLORS["sun"], symbol="circle"),
                name="Sun",
                hoverinfo="text",
                hovertext=f"Az: {first_pos.azimuth:.1f} El: {first_pos.elevation:.1f}" if first_pos else "",
            )
        )

        # Dynamic trace 1: Sun ray (index n_static + 1)
        self.fig.add_trace(
            go.Scatter3d(
                x=[sx, sx * 0.3], y=[sy, sy * 0.3], z=[sz, 0],
                mode="lines",
                line=dict(color=COLORS["sun"], width=1, dash="dash"),
                showlegend=False,
                hoverinfo="skip",
            )
        )

        # Dynamic trace 2: Shadow (index n_static + 2)
        shadow_trace = self._build_shadow_trace(first_shadow)
        self.fig.add_trace(shadow_trace)

        # Build animation frames
        frames = []
        slider_steps = []

        for i, (pos, shadow) in enumerate(zip(anim_positions, anim_shadows)):
            sx, sy, sz = SolarEngine.sun_sphere_coords(pos, self.sun_radius)
            label = pos.timestamp.strftime("%H:%M")

            frame_data = [
                go.Scatter3d(
                    x=[sx], y=[sy], z=[sz],
                    mode="markers",
                    marker=dict(size=12, color=COLORS["sun"], symbol="circle"),
                    name="Sun",
                    hoverinfo="text",
                    hovertext=f"Az: {pos.azimuth:.1f} El: {pos.elevation:.1f}",
                ),
                go.Scatter3d(
                    x=[sx, sx * 0.3], y=[sy, sy * 0.3], z=[sz, 0],
                    mode="lines",
                    line=dict(color=COLORS["sun"], width=1, dash="dash"),
                    showlegend=False,
                    hoverinfo="skip",
                ),
                self._build_shadow_trace(shadow),
            ]

            frames.append(go.Frame(
                data=frame_data,
                traces=[n_static, n_static + 1, n_static + 2],
                name=label,
            ))

            slider_steps.append(dict(
                method="animate",
                label=label,
                args=[[label], dict(
                    frame=dict(duration=150, redraw=True),
                    transition=dict(duration=100),
                    mode="immediate",
                )],
            ))

        self.fig.frames = frames

        # Play/Pause buttons — Plotly washes out bgcolor, so use very saturated colors
        self.fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    showactive=False,
                    y=-0.02,
                    x=0.0,
                    xanchor="left",
                    bgcolor="rgb(0,140,0)",
                    bordercolor="rgb(0,100,0)",
                    font=dict(color="rgb(0,80,0)", size=14, family="Inter, Segoe UI, sans-serif"),
                    buttons=[
                        dict(
                            label="\u25B6\uFE0F Play",
                            method="animate",
                            args=[None, dict(
                                frame=dict(duration=150, redraw=True),
                                fromcurrent=True,
                                transition=dict(duration=100),
                            )],
                        ),
                    ],
                ),
                dict(
                    type="buttons",
                    showactive=False,
                    y=-0.02,
                    x=0.08,
                    xanchor="left",
                    bgcolor="rgb(210,160,0)",
                    bordercolor="rgb(180,120,0)",
                    font=dict(color="rgb(120,80,0)", size=14, family="Inter, Segoe UI, sans-serif"),
                    buttons=[
                        dict(
                            label="\u23F8\uFE0F Pause",
                            method="animate",
                            args=[[None], dict(
                                frame=dict(duration=0, redraw=False),
                                mode="immediate",
                                transition=dict(duration=0),
                            )],
                        ),
                    ],
                ),
            ],
            sliders=[dict(
                active=0,
                steps=slider_steps,
                x=0.15,
                len=0.82,
                pad=dict(b=5, t=40),
                bgcolor="#d0d7de",
                activebgcolor="#1a3a5c",
                bordercolor="#8899aa",
                borderwidth=1,
                ticklen=4,
                tickcolor="#8899aa",
                font=dict(size=10, color="#555", family="Inter, Segoe UI, sans-serif"),
                currentvalue=dict(
                    prefix="Time: ",
                    font=dict(size=13, color="#1a3a5c", family="Inter, Segoe UI, sans-serif"),
                    xanchor="center",
                ),
                transition=dict(duration=100),
            )],
        )

        self._configure_layout(geometry, extra_bottom_margin=60)
        return self.fig

    def _compute_sizes(self, geometry: BuildingGeometry):
        w, d, h = geometry.width, geometry.depth, geometry.total_height
        half_diag = np.sqrt((w / 2) ** 2 + (d / 2) ** 2 + h ** 2)
        max_dim = max(w, d, h)
        self.sun_radius = max(half_diag * 1.8, max_dim + 15)
        self.ground_size = max(max_dim * 1.3, 15)

    @staticmethod
    def _build_shadow_trace(shadow: ShadowResult | None) -> go.Mesh3d:
        """Build a Mesh3d trace for a shadow polygon (or invisible placeholder)."""
        if not shadow or not shadow.shadow_vertices or len(shadow.shadow_vertices) < 3:
            return go.Mesh3d(
                x=[0, 0, 0], y=[0, 0, 0], z=[0, 0, 0],
                i=[0], j=[1], k=[2],
                color=COLORS["shadow"],
                opacity=0.0,
                name="Shadow",
                hoverinfo="skip",
                showlegend=False,
            )

        verts = list(shadow.shadow_vertices)
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [0.01] * len(verts)

        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)

        xs.append(cx)
        ys.append(cy)
        zs.append(0.01)
        center_idx = len(xs) - 1

        angles = [np.arctan2(y - cy, x - cx) for x, y in verts]
        sorted_indices = sorted(range(len(verts)), key=lambda idx: angles[idx])

        i_faces, j_faces, k_faces = [], [], []
        n = len(sorted_indices)
        for idx in range(n):
            i_faces.append(center_idx)
            j_faces.append(sorted_indices[idx])
            k_faces.append(sorted_indices[(idx + 1) % n])

        return go.Mesh3d(
            x=xs, y=ys, z=zs,
            i=i_faces, j=j_faces, k=k_faces,
            color=COLORS["shadow"],
            opacity=0.5,
            name="Shadow",
            hoverinfo="name",
            showlegend=False,
        )

    def _add_ground_plane(self, geometry: BuildingGeometry):
        g = self.ground_size
        cx = geometry.width / 2
        cy = geometry.depth / 2

        self.fig.add_trace(
            go.Mesh3d(
                x=[-g + cx, g + cx, g + cx, -g + cx],
                y=[-g + cy, -g + cy, g + cy, g + cy],
                z=[0, 0, 0, 0],
                i=[0, 0],
                j=[1, 2],
                k=[2, 3],
                color=COLORS["ground"],
                opacity=0.6,
                name="Ground",
                showlegend=False,
                hoverinfo="skip",
            )
        )

        # Grid lines
        for offset in np.arange(-g, g + 1, 10):
            self.fig.add_trace(
                go.Scatter3d(
                    x=[offset + cx, offset + cx],
                    y=[-g + cy, g + cy],
                    z=[0.01, 0.01],
                    mode="lines",
                    line=dict(color=COLORS["ground_grid"], width=1),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            self.fig.add_trace(
                go.Scatter3d(
                    x=[-g + cx, g + cx],
                    y=[offset + cy, offset + cy],
                    z=[0.01, 0.01],
                    mode="lines",
                    line=dict(color=COLORS["ground_grid"], width=1),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    def _add_compass_rose(self, geometry: BuildingGeometry):
        cx = geometry.width / 2
        cy = geometry.depth / 2
        r = self.ground_size * 0.85

        directions = [
            ("N", 0, COLORS["compass_n"]),
            ("S", 180, COLORS["compass_s"]),
            ("E", 90, COLORS["compass_e"]),
            ("W", 270, COLORS["compass_w"]),
        ]

        for label, az, color in directions:
            az_rad = np.radians(az)
            x = cx + r * np.sin(az_rad)
            y = cy + r * np.cos(az_rad)

            # Line from center
            self.fig.add_trace(
                go.Scatter3d(
                    x=[cx, x],
                    y=[cy, y],
                    z=[0.02, 0.02],
                    mode="lines",
                    line=dict(color=color, width=3),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            # Label
            self.fig.add_trace(
                go.Scatter3d(
                    x=[x],
                    y=[y],
                    z=[1.0],
                    mode="text",
                    text=[label],
                    textfont=dict(size=16, color=color),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    def _add_building(self, geometry: BuildingGeometry):
        xs, ys, zs, faces, _, _ = GeometryBuilder.build_mesh(geometry)
        i_faces = [f[0] for f in faces]
        j_faces = [f[1] for f in faces]
        k_faces = [f[2] for f in faces]

        self.fig.add_trace(
            go.Mesh3d(
                x=xs,
                y=ys,
                z=zs,
                i=i_faces,
                j=j_faces,
                k=k_faces,
                color=COLORS["building"],
                opacity=0.85,
                name="Building",
                flatshading=True,
                hoverinfo="name",
            )
        )

        # Wireframe edges for building outline
        edges = set()
        for f in faces:
            for a, b in [(f[0], f[1]), (f[1], f[2]), (f[2], f[0])]:
                edge = (min(a, b), max(a, b))
                edges.add(edge)

        edge_x, edge_y, edge_z = [], [], []
        for a, b in edges:
            edge_x.extend([xs[a], xs[b], None])
            edge_y.extend([ys[a], ys[b], None])
            edge_z.extend([zs[a], zs[b], None])

        self.fig.add_trace(
            go.Scatter3d(
                x=edge_x,
                y=edge_y,
                z=edge_z,
                mode="lines",
                line=dict(color=COLORS["building_edge"], width=2),
                name="Edges",
                showlegend=False,
                hoverinfo="skip",
            )
        )

        # Front-face indicator
        self._add_front_indicator(geometry)

    def _add_front_indicator(self, geometry: BuildingGeometry):
        """Draw a colored bar and label on the building's front face to show orientation."""
        w = geometry.width
        d = geometry.depth
        h = geometry.wall_height
        cx, cy = w / 2, d / 2

        front_pts = [
            (w * 0.2, 0, 0.1),
            (w * 0.8, 0, 0.1),
            (w * 0.8, 0, h * 0.15),
            (w * 0.2, 0, h * 0.15),
        ]

        label_pt = (w / 2, -1.5, h * 0.5)

        if geometry.orientation != 0.0:
            theta = np.radians(geometry.orientation)
            cos_t = np.cos(theta)
            sin_t = np.sin(theta)

            def rotate(x, y):
                dx, dy = x - cx, y - cy
                return cx + dx * cos_t + dy * sin_t, cy - dx * sin_t + dy * cos_t

            front_pts = [(rotate(x, y)[0], rotate(x, y)[1], z) for x, y, z in front_pts]
            lx, ly = rotate(label_pt[0], label_pt[1])
            label_pt = (lx, ly, label_pt[2])

        fx = [p[0] for p in front_pts] + [front_pts[0][0]]
        fy = [p[1] for p in front_pts] + [front_pts[0][1]]
        fz = [p[2] for p in front_pts] + [front_pts[0][2]]

        self.fig.add_trace(
            go.Scatter3d(
                x=fx, y=fy, z=fz,
                mode="lines",
                line=dict(color="#e74c3c", width=6),
                name="Front",
                showlegend=False,
                hoverinfo="skip",
            )
        )

        self.fig.add_trace(
            go.Scatter3d(
                x=[label_pt[0]], y=[label_pt[1]], z=[label_pt[2]],
                mode="text",
                text=["FRONT"],
                textfont=dict(size=11, color="#e74c3c"),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    def _add_nearby_structures(
        self, structures: list[NearbyStructure], geometry: BuildingGeometry
    ):
        direction_offsets = {
            "N": (0, 1),
            "NE": (1, 1),
            "E": (1, 0),
            "SE": (1, -1),
            "S": (0, -1),
            "SW": (-1, -1),
            "W": (-1, 0),
            "NW": (-1, 1),
        }

        for idx, struct in enumerate(structures):
            offset = direction_offsets.get(
                struct.relative_position.upper(), (1, 0)
            )
            dist = max(geometry.width, geometry.depth) * 0.8
            pos_x = geometry.width / 2 + offset[0] * dist
            pos_y = geometry.depth / 2 + offset[1] * dist

            color = COLORS["tree"] if struct.type == "tree" else COLORS["structure"]
            xs, ys, zs, faces = GeometryBuilder.build_nearby_structure(
                struct.type, struct.estimated_height, (pos_x, pos_y)
            )
            i_f = [f[0] for f in faces]
            j_f = [f[1] for f in faces]
            k_f = [f[2] for f in faces]

            self.fig.add_trace(
                go.Mesh3d(
                    x=xs,
                    y=ys,
                    z=zs,
                    i=i_f,
                    j=j_f,
                    k=k_f,
                    color=color,
                    opacity=0.7,
                    name=struct.description or struct.type,
                    showlegend=False,
                    hoverinfo="name",
                )
            )

    def _add_sun_path(self, sun_path: SunPath):
        radius = self.sun_radius
        xs, ys, zs = SolarEngine.sun_path_3d_coords(sun_path, radius)

        if not xs:
            return

        self.fig.add_trace(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="lines",
                line=dict(color=COLORS["sun_path"], width=4),
                name="Sun Path",
                hoverinfo="skip",
            )
        )

        # Hourly markers
        hourly = [
            p
            for p in sun_path.above_horizon
            if p.timestamp.minute == 0
        ]
        hx, hy, hz, labels = [], [], [], []
        for p in hourly:
            sx, sy, sz = SolarEngine.sun_sphere_coords(p, radius)
            hx.append(sx)
            hy.append(sy)
            hz.append(sz)
            labels.append(p.timestamp.strftime("%H:%M"))

        if hx:
            self.fig.add_trace(
                go.Scatter3d(
                    x=hx,
                    y=hy,
                    z=hz,
                    mode="markers+text",
                    marker=dict(
                        size=4, color=COLORS["sun_marker"], symbol="circle"
                    ),
                    text=labels,
                    textposition="top center",
                    textfont=dict(size=9, color=COLORS["text"]),
                    name="Hourly",
                    showlegend=False,
                    hoverinfo="text",
                )
            )

    def _add_sun_sphere(self, sun_position: SolarPosition):
        radius = self.sun_radius
        sx, sy, sz = SolarEngine.sun_sphere_coords(sun_position, radius)

        self.fig.add_trace(
            go.Scatter3d(
                x=[sx],
                y=[sy],
                z=[sz],
                mode="markers",
                marker=dict(size=12, color=COLORS["sun"], symbol="circle"),
                name="Sun",
                hovertext=f"Az: {sun_position.azimuth:.1f} El: {sun_position.elevation:.1f}",
                hoverinfo="text",
            )
        )

        # Sun ray line to ground
        self.fig.add_trace(
            go.Scatter3d(
                x=[sx, sx * 0.3],
                y=[sy, sy * 0.3],
                z=[sz, 0],
                mode="lines",
                line=dict(color=COLORS["sun"], width=1, dash="dash"),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    def _add_shadow(self, shadow: ShadowResult):
        trace = self._build_shadow_trace(shadow)
        self.fig.add_trace(trace)

    def _configure_layout(self, geometry: BuildingGeometry, extra_bottom_margin: int = 0):
        scene_range = self.sun_radius * 1.05

        cx = geometry.width / 2
        cy = geometry.depth / 2

        self.fig.update_layout(
            scene=dict(
                xaxis=dict(
                    title="East ->",
                    range=[cx - scene_range, cx + scene_range],
                    showbackground=False,
                    showgrid=False,
                    zeroline=False,
                ),
                yaxis=dict(
                    title="North ->",
                    range=[cy - scene_range, cy + scene_range],
                    showbackground=False,
                    showgrid=False,
                    zeroline=False,
                ),
                zaxis=dict(
                    title="Up",
                    range=[0, scene_range],
                    showbackground=False,
                    showgrid=False,
                    zeroline=False,
                ),
                aspectmode="data",
                dragmode="turntable",
                camera=dict(
                    eye=dict(x=1.3, y=-1.3, z=0.8),
                    up=dict(x=0, y=0, z=1),
                ),
                bgcolor=COLORS["background"],
            ),
            margin=dict(l=0, r=0, t=0, b=extra_bottom_margin),
            showlegend=True,
            legend=dict(
                x=0.02,
                y=0.98,
                bgcolor="rgba(255,255,255,0.8)",
                font=dict(size=10),
            ),
            height=650,
        )
