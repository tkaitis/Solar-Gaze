"""Solar Gaze — Solar Path, Shadow & Photovoltaic Analysis"""

from __future__ import annotations

import os

import streamlit as st

st.set_page_config(
    page_title="Theo's Solar Gazer — Solar Path, Shadow & Photovoltaic Analysis",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Institutional CSS
st.markdown("""
<style>
    /* Remove default top padding so banner starts at very top */
    .block-container { padding-top: 0rem; padding-bottom: 0.5rem; }
    /* Hide Streamlit header on desktop, keep visible on mobile for sidebar toggle */
    @media (min-width: 768px) {
        header[data-testid="stHeader"] { display: none !important; }
    }
    /* On mobile, keep header visible but add padding so banner isn't hidden behind it */
    @media (max-width: 767px) {
        .block-container { padding-top: 3.5rem; }
    }
    /* Sidebar polish */
    [data-testid="stSidebar"] { background: #f7f9fb; }
    [data-testid="stSidebar"] h1 { font-size: 1.3rem; }
    [data-testid="stSidebar"] .stSubheader { font-size: 0.85rem; }
    /* Smaller metric overrides (fallback for non-table areas) */
    [data-testid="stMetric"] { padding: 4px 0; }
    [data-testid="stMetricValue"] { font-size: 0.95rem; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem; }
    /* Hide Streamlit branding on mobile — keep sidebar toggle and header intact */
    @media (max-width: 768px) {
        .stDeployButton,
        [data-testid="stToolbarActions"],
        [data-testid="manage-app-button"] {
            display: none !important;
        }
    }
    /* Hide bottom Streamlit footer and badges on all viewports */
    footer { display: none !important; }
    .viewerBadge_container__r5tak,
    .styles_viewerBadge__CvC9N,
    ._profileContainer_gzau3_53,
    ._profilePreview_gzau3_63,
    [data-testid="stStreamlitBadge"],
    .stAppDeployButton {
        display: none !important;
        visibility: hidden !important;
    }
</style>
""", unsafe_allow_html=True)

from models.solar import LocationConfig
from services.geometry_builder import GeometryBuilder
from services.light_calculator import LightCalculator
from services.shadow_calculator import ShadowCalculator
from services.solar_engine import SolarEngine
from services.pv_calculator import PVCalculator
from visualization.scene_3d import Scene3D
from ui.analysis_panel import render_analysis_panel
from ui.session_state import init_session_state, get_building_geometry, get_selected_datetime, get_window_config
from ui.sidebar_controls import render_sidebar
from ui.pv_sidebar import get_roof_pv_config, get_panel_spec, get_system_losses, get_financial_params
from ui.pv_dashboard import render_pv_dashboard

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "cigdem_flower2.jpeg")
HERO_PATH = os.path.join(os.path.dirname(__file__), "assets", "hero_banner.png")


def _render_hero_banner():
    """Render the hero banner with title overlay and help button."""
    import base64

    if os.path.exists(HERO_PATH):
        with open(HERO_PATH, "rb") as f:
            hero_b64 = base64.b64encode(f.read()).decode()

        banner_html = (
            '<div style="'
            'position:relative; width:100%; '
            'border-radius:12px; overflow:hidden; margin-bottom:10px; '
            'box-shadow:0 2px 12px rgba(0,0,0,0.12);">'
            # Background image — full width, natural aspect ratio, no cropping
            f'<img src="data:image/png;base64,{hero_b64}" '
            'style="width:100%; height:auto; display:block;" />'
            # Subtle gradient overlay — darker at top-right for title legibility
            '<div style="'
            'position:absolute; top:0; left:0; right:0; bottom:0; '
            'background:linear-gradient(135deg, rgba(0,0,0,0.0) 0%, '
            'rgba(0,0,0,0.0) 40%, rgba(0,0,0,0.45) 100%);">'
            '</div>'
            # Title + subtitle overlay — responsive positioning
            '<div style="'
            'position:absolute; top:30%; right:4%; '
            "font-family:'Inter','Segoe UI',system-ui,sans-serif; "
            'text-align:right;">'
            '<div style="font-size:clamp(14px, 3vw, 22px); font-weight:700; color:#fff; '
            'letter-spacing:0.3px; text-shadow:0 1px 6px rgba(0,0,0,0.7);">'
            "Theo's Solar Gazer"
            '</div>'
            '<div style="font-size:clamp(10px, 1.8vw, 13px); color:rgba(255,255,255,0.9); '
            'font-weight:500; letter-spacing:0.4px; margin-top:2px; '
            'text-shadow:0 1px 4px rgba(0,0,0,0.6);">'
            'Solar Path, Shadow &amp; Photovoltaic Analysis'
            '</div>'
            '</div>'
            '</div>'
        )
        st.markdown(banner_html, unsafe_allow_html=True)
    else:
        # Fallback if no hero image
        st.markdown(
            "<h2 style='margin:0; padding-top:6px; font-size:1.4rem; "
            "color:#1a3a5c;'>Theo's Solar Gazer</h2>",
            unsafe_allow_html=True,
        )


def main():
    init_session_state()

    # Render sidebar and check if AI analysis was requested
    ai_requested = render_sidebar()

    # Handle AI analysis
    if ai_requested:
        _handle_ai_analysis()

    # Build location config
    location = LocationConfig(
        latitude=st.session_state.latitude,
        longitude=st.session_state.longitude,
        timezone=st.session_state.timezone,
        name=st.session_state.get("location_name", ""),
    )

    # Get building geometry
    geometry = get_building_geometry()

    # Hero banner
    _render_hero_banner()

    # Help button (right-aligned, professional)
    help_cols = st.columns([3, 1])
    with help_cols[1]:
        help_label = "Hide Guide" if st.session_state.get("show_help") else "How to Use"
        if st.button(help_label, key="how_to_use_btn", type="secondary", use_container_width=True):
            st.session_state["show_help"] = not st.session_state.get("show_help", False)
            st.rerun()

    if st.session_state.get("show_help"):
        _show_how_to_use()

    # --- Route by mode ---
    app_mode = st.session_state.get("app_mode", "shadow")

    if app_mode == "pv":
        _run_pv_mode(location, geometry)
    else:
        _run_shadow_mode(location, geometry)


def _run_shadow_mode(location: LocationConfig, geometry):
    """Original shadow/sunlight analysis flow."""

    # Get selected datetime
    dt = get_selected_datetime()

    # Compute solar position and sun path
    sun_position = SolarEngine.compute_position(location, dt)
    sun_path = SolarEngine.compute_sun_path(location, dt.date())

    # Build the 3D mesh and compute shadow
    xs, ys, zs, faces, footprint, roof_verts = GeometryBuilder.build_mesh(geometry)

    shadow = None
    if sun_position.is_above_horizon:
        shadow = ShadowCalculator.compute_shadow(
            geometry, sun_position, roof_verts, footprint
        )

    # Get window config and compute light patches
    window_config = get_window_config()
    light_patches = []
    if window_config.has_any_glazing() and sun_position.is_above_horizon:
        light_patches = LightCalculator.compute_light_patches(
            geometry, sun_position, window_config
        )

    transparent_building = st.session_state.get("transparent_building", False)

    # Get nearby structures from AI analysis
    nearby = None
    if st.session_state.get("ai_analysis"):
        nearby = st.session_state["ai_analysis"].nearby_structures or None

    # Show AI analysis results or errors
    _show_ai_results_banner()

    if st.session_state.get("ai_error"):
        st.error(st.session_state["ai_error"])
        if st.button("Dismiss error", key="dismiss_ai_error"):
            st.session_state.pop("ai_error", None)
            st.rerun()

    # Enable scroll-zoom on desktop only; on touch devices it traps the page scroll
    plotly_config = {
        "scrollZoom": True,
        "modeBarButtonsToRemove": ["zoom3d", "pan3d", "resetCameraLastSave3d"],
    }

    # Full-width 3D scene
    if st.session_state.animate:
        above = sun_path.above_horizon
        if not above:
            st.warning("Sun never rises on this date at this location.")
        else:
            # Filter out very low sun angles to prevent shadow distortion
            usable = [p for p in above if p.elevation >= 5.0]
            if not usable:
                usable = above
            step = max(1, int(3 / st.session_state.animation_speed))
            anim_positions = usable[::step]

            anim_shadows = []
            anim_light_patches = []
            for pos in anim_positions:
                _, _, _, _, fp, rv = GeometryBuilder.build_mesh(geometry)
                s = ShadowCalculator.compute_shadow(geometry, pos, rv, fp)
                anim_shadows.append(s)
                if window_config.has_any_glazing():
                    lp = LightCalculator.compute_light_patches(geometry, pos, window_config)
                    anim_light_patches.append(lp)
                else:
                    anim_light_patches.append([])

            scene = Scene3D()
            fig = scene.build_animated_scene(
                geometry, sun_path, anim_positions, anim_shadows, nearby,
                window_config=window_config,
                anim_light_patches=anim_light_patches,
                transparent_building=transparent_building,
            )
            st.plotly_chart(
                fig, use_container_width=True, key="anim_scene", config=plotly_config
            )
    else:
        scene = Scene3D()
        fig = scene.build_scene(
            geometry, sun_position, sun_path, shadow, nearby,
            window_config=window_config,
            light_patches=light_patches,
            transparent_building=transparent_building,
        )
        st.plotly_chart(
            fig, use_container_width=True, key="main_3d_scene", config=plotly_config
        )

    # Disable scroll-zoom on touch devices to prevent trapping page scroll
    st.components.v1.html("""
    <script>
    if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
        document.querySelectorAll('.js-plotly-plot').forEach(function(el) {
            if (el._fullLayout) el._fullLayout.scene._scene.glplot.scrollZoom = false;
            el.style.touchAction = 'pan-y';
        });
    }
    </script>
    """, height=0)

    # Analysis panel below the rendering
    render_analysis_panel(sun_position, sun_path, shadow, geometry, light_patches)


def _run_pv_mode(location: LocationConfig, geometry):
    """Solar Panel Feasibility analysis flow."""
    roof = get_roof_pv_config()
    panel = get_panel_spec()
    losses = get_system_losses()
    financial = get_financial_params()

    with st.spinner("Computing PV feasibility..."):
        result = PVCalculator.compute_feasibility(
            lat=location.latitude,
            lon=location.longitude,
            tz=location.timezone,
            width=geometry.width,
            depth=geometry.depth,
            roof_pitch=geometry.roof_pitch,
            roof_type=geometry.roof_type,
            tilt_deg=roof.tilt_deg,
            azimuth_deg=roof.azimuth_deg,
            usable_roof_pct=roof.usable_roof_pct,
            auto_tilt=roof.auto_tilt,
            auto_azimuth=roof.auto_azimuth,
            rated_power_w=panel.rated_power_w,
            efficiency_pct=panel.efficiency_pct,
            temp_coeff_pmax=panel.temp_coeff_pmax,
            noct_c=panel.noct_c,
            panel_area_m2=panel.panel_area_m2,
            soiling=losses.soiling,
            shading=losses.shading,
            mismatch=losses.mismatch,
            wiring_dc=losses.wiring_dc,
            wiring_ac=losses.wiring_ac,
            inverter_eff=losses.inverter_eff,
            availability=losses.availability,
            electricity_rate=financial.electricity_rate,
            escalation=financial.escalation,
            cost_per_watt=financial.cost_per_watt,
            incentive_pct=financial.incentive_pct,
            degradation=financial.degradation,
            discount_rate=financial.discount_rate,
            analysis_period=financial.analysis_period,
            om_cost=financial.om_cost,
        )

    render_pv_dashboard(result)


def _show_how_to_use():
    """Display a professional how-to-use guide as a dismissible panel."""

    def _card(number, title, color, body):
        return (
            '<div style="flex:1; min-width:160px; background:#f8fafc; '
            'border-radius:8px; padding:12px 14px; border:1px solid #e2e8f0;">'
            f'<div style="font-size:13px; font-weight:700; color:{color}; '
            'text-transform:uppercase; letter-spacing:0.5px; margin-bottom:5px;">'
            f'{number}. {title}</div>'
            f'<div style="font-size:13px; color:#475569; line-height:1.6;">{body}</div>'
            '</div>'
        )

    cards = [
        _card("1", "Set Location", "#0ea5e9",
              "Choose a city from the <b>Location Presets</b> dropdown, or enter "
              "custom latitude/longitude. Right-click any spot in Google Maps to copy coordinates."),
        _card("2", "Define Building", "#0ea5e9",
              "Set <b>width, depth, wall height</b> in meters or feet. Pick a <b>roof type</b> "
              "(flat, gable, hip, mansard, gambrel, butterfly, sawtooth, dutch gable) "
              "and adjust pitch and orientation."),
        _card("3", "Windows & Glass Walls", "#10b981",
              "Set each wall to <b>Solid Wall</b>, <b>Window</b>, or <b>Glass Wall</b>. "
              "For windows, adjust <b>width %</b>, <b>height %</b>, and <b>sill height %</b>. "
              "Enable <b>See-through walls</b> to view interior light patches on the floor."),
        _card("4", "Pick Date and Time", "#0ea5e9",
              "Select a <b>date</b> and adjust the <b>hour/minute</b> sliders. The 3D scene "
              "updates in real time with sun position, path arc, and shadow projection."),
        _card("5", "Animate", "#f59e0b",
              "Tick <b>Animate through day</b> to watch the sun, shadow, and interior light "
              "move throughout the day. Use <b>Play</b> / <b>Pause</b> and the timeline slider."),
        _card("6", "AI Vision (Optional)", "#6366f1",
              "Upload an <b>aerial screenshot</b> and/or <b>front photo</b>. "
              "Click <b>Analyze with AI</b> to auto-detect dimensions, roof type, "
              "materials, and nearby structures. Requires an API key in .env."),
        _card("7", "Solar Panel Feasibility", "#10b981",
              "Switch to <b>Solar Panel Feasibility</b> mode to estimate energy yield, "
              "system sizing, and financial payback. Set your panel specs, adjust losses, "
              "and enter your electricity rate to see payback period and 25-year NPV."),
        _card("", "Tips", "#6366f1",
              "<b>Drag</b> to rotate the 3D view, <b>scroll</b> to zoom in/out. "
              "The red <b>FRONT</b> marker shows building orientation. "
              "The <b>orange arc</b> is the sun path. "
              "<b>Yellow patches</b> on the floor show sunlight entering through windows."),
    ]

    html = (
        '<div style="background:#fff; border:1px solid #e2e8f0; border-radius:10px; '
        "padding:16px 20px; margin-bottom:10px; "
        "font-family:'Inter','Segoe UI',system-ui,sans-serif; "
        'box-shadow:0 2px 8px rgba(0,0,0,0.06);">'
        '<div style="font-size:14px; font-weight:700; color:#1a3a5c; margin-bottom:10px;">'
        'Quick Start Guide</div>'
        '<div style="display:flex; flex-wrap:wrap; gap:10px;">'
        + "".join(cards)
        + '</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _show_ai_results_banner():
    """Show a compact professional banner for AI analysis results."""
    analysis = st.session_state.get("ai_analysis")
    if not analysis:
        return

    g = analysis.geometry
    roof_label = g.roof_type.replace("_", " ").title()

    # Build data pills
    pills = [
        f"<b>Type:</b> {analysis.building_type}",
        f"<b>Stories:</b> {analysis.stories}",
        f"<b>Size:</b> {g.width:.0f} x {g.depth:.0f} x {g.wall_height:.0f} m",
        f"<b>Roof:</b> {roof_label} ({g.roof_pitch:.0f}°)",
    ]
    if g.orientation > 0:
        pills.append(f"<b>Orientation:</b> {g.orientation:.0f}° from N")
    if analysis.materials:
        pills.append(f"<b>Materials:</b> {', '.join(analysis.materials)}")
    if analysis.nearby_structures:
        pills.append(f"<b>Nearby:</b> {len(analysis.nearby_structures)} structure(s)")

    pill_sep = '&nbsp;&nbsp;&middot;&nbsp;&nbsp;'
    pills_html = pill_sep.join(pills)

    notes_html = ""
    if analysis.notes:
        notes_html = (
            '<div style="font-size:12px; color:#64748b; margin-top:4px; '
            f'font-style:italic;">{analysis.notes}</div>'
        )

    banner_html = (
        '<div style="'
        'background:linear-gradient(135deg,#f0f9ff 0%,#e0f2fe 100%);'
        'border:1px solid #7dd3fc; border-left:4px solid #0284c7;'
        'border-radius:8px; padding:10px 16px; margin-bottom:8px;'
        "font-family:'Inter','Segoe UI',system-ui,sans-serif;"
        '">'
        '<div style="font-size:13px; font-weight:700; color:#0369a1;'
        'text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">'
        f'AI Vision Analysis &mdash; {analysis.confidence.upper()} Confidence'
        '</div>'
        f'<div style="font-size:13px; color:#334155; line-height:1.6;">{pills_html}</div>'
        f'{notes_html}'
        '</div>'
    )
    st.markdown(banner_html, unsafe_allow_html=True)


def _handle_ai_analysis():
    pending = st.session_state.get("pending_images")
    if not pending:
        return

    from services.vision_analyzer import VisionAnalyzer, _detect_provider

    provider = _detect_provider()
    provider_names = {"gemini": "Google Gemini", "openai": "OpenAI GPT-4o", "anthropic": "Anthropic Claude"}
    label = provider_names.get(provider, provider)

    with st.spinner(f"Analyzing building with {label}..."):
        try:
            analyzer = VisionAnalyzer()
            analysis = analyzer.analyze_images(pending)
            st.session_state["ai_analysis"] = analysis
            st.session_state["ai_analyzed"] = True

            # Apply AI-detected geometry — clamp to widget limits
            g = analysis.geometry
            st.session_state.building_width = max(1.0, min(200.0, g.width))
            st.session_state.building_depth = max(1.0, min(200.0, g.depth))
            st.session_state.building_wall_height = max(1.0, min(100.0, g.wall_height))
            st.session_state.building_roof_type = g.roof_type
            st.session_state.building_roof_pitch = max(5.0, min(75.0, g.roof_pitch))
            st.session_state.building_orientation = max(0.0, min(359.0, g.orientation))

            # Clear widget keys so they pick up the new values on rerun
            for wkey in [
                "input_width", "input_depth", "input_wall_height",
                "input_roof_type", "input_roof_pitch", "input_orientation",
            ]:
                st.session_state.pop(wkey, None)

            st.toast(
                f"AI detected: {g.width:.0f}x{g.depth:.0f}m, "
                f"{g.wall_height:.0f}m tall, {g.roof_type} roof "
                f"({analysis.confidence} confidence)",
                icon="✅",
            )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            st.session_state["ai_error"] = f"Vision analysis failed: {e}\n\n{tb}"
        finally:
            st.session_state.pop("pending_images", None)
            st.rerun()


if __name__ == "__main__":
    main()
