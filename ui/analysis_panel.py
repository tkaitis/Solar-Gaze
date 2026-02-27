from __future__ import annotations

import streamlit as st

from models.building import BuildingGeometry
from models.solar import ShadowResult, SolarPosition, SunPath

BEARING_DIRS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def render_analysis_panel(
    sun_position: SolarPosition | None,
    sun_path: SunPath | None,
    shadow: ShadowResult | None,
    geometry: BuildingGeometry,
):
    """Render a professional dashboard panel below the 3D scene."""

    # --- Solar data ---
    solar_items = []
    if sun_position and sun_position.is_above_horizon:
        solar_items.append(("Azimuth", f"{sun_position.azimuth:.1f}&deg;"))
        solar_items.append(("Elevation", f"{sun_position.elevation:.1f}&deg;"))
    elif sun_position:
        solar_items.append(("Status", "Below horizon"))
        solar_items.append(("Elevation", f"{sun_position.elevation:.1f}&deg;"))
    else:
        solar_items.append(("Status", "&mdash;"))

    if sun_path:
        if sun_path.sunrise:
            solar_items.append(("Sunrise", sun_path.sunrise.strftime("%H:%M")))
        if sun_path.sunset:
            solar_items.append(("Sunset", sun_path.sunset.strftime("%H:%M")))
        solar_items.append(("Day Length", f"{sun_path.day_length_hours:.1f} hrs"))

    # --- Shadow data ---
    shadow_items = []
    if shadow:
        shadow_items.append(("Length", f"{shadow.shadow_length:.1f} m"))
        shadow_items.append(("Area", f"{shadow.shadow_area:.1f} m&sup2;"))
        idx = round(shadow.shadow_bearing / 22.5) % 16
        compass = BEARING_DIRS[idx]
        shadow_items.append(("Direction", f"{compass} ({shadow.shadow_bearing:.0f}&deg;)"))
    else:
        shadow_items.append(("Status", "No shadow"))

    # --- Building data ---
    building_items = []
    building_items.append((
        "Footprint",
        f"{geometry.width:.0f} &times; {geometry.depth:.0f} m",
    ))
    building_items.append(("Roof", geometry.roof_type.replace("_", " ").title()))
    if geometry.roof_type != "flat":
        building_items.append(("Pitch", f"{geometry.roof_pitch:.0f}&deg;"))
        ridge = geometry.compute_ridge_height()
        building_items.append(("Height", f"{geometry.wall_height + ridge:.1f} m"))
    else:
        building_items.append(("Height", f"{geometry.wall_height:.1f} m"))
    building_items.append(("Orientation", f"{geometry.orientation:.0f}&deg; from N"))

    html = _build_dashboard(
        ("Solar Position", "#f59e0b", solar_items),
        ("Shadow Analysis", "#6366f1", shadow_items),
        ("Building", "#0ea5e9", building_items),
    )
    st.markdown(html, unsafe_allow_html=True)


def _build_dashboard(*cards: tuple[str, str, list[tuple[str, str]]]) -> str:
    """Build a 3-column card layout with professional styling."""

    card_html_list = []
    for title, accent, items in cards:
        rows = ""
        for label, value in items:
            rows += (
                f'<div style="display:flex; justify-content:space-between; '
                f'align-items:baseline; padding:5px 0; '
                f'border-bottom:1px solid rgba(0,0,0,0.04);">'
                f'<span style="color:#64748b; font-size:12px; font-weight:500;">{label}</span>'
                f'<span style="color:#0f172a; font-size:13px; font-weight:600; '
                f'letter-spacing:-0.01em;">{value}</span>'
                f'</div>'
            )

        card_html_list.append(
            f'<div style="'
            f"flex:1; min-width:200px; "
            f"background:linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); "
            f"border:1px solid #e2e8f0; "
            f"border-radius:10px; "
            f"overflow:hidden; "
            f"box-shadow:0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04); "
            f'">'
            # Header strip
            f'<div style="'
            f"background:linear-gradient(135deg, {accent} 0%, {accent}dd 100%); "
            f"padding:8px 14px; "
            f'">'
            f'<span style="'
            f"color:#fff; font-size:11px; font-weight:700; "
            f"text-transform:uppercase; letter-spacing:0.8px; "
            f"font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif; "
            f'">{title}</span>'
            f'</div>'
            # Body
            f'<div style="padding:8px 14px 10px 14px;">'
            f'{rows}'
            f'</div>'
            f'</div>'
        )

    return (
        f'<div style="'
        f"display:flex; gap:12px; flex-wrap:wrap; "
        f"font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif; "
        f"margin-top:8px; "
        f'">'
        f'{"".join(card_html_list)}'
        f'</div>'
    )
