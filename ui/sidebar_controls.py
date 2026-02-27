from __future__ import annotations

import streamlit as st

from models.building import BuildingGeometry
from ui.session_state import LOCATION_PRESETS

METERS_PER_FOOT = 0.3048
FEET_PER_METER = 3.28084


def render_sidebar():
    """Render all sidebar controls. Returns True if AI analysis was requested."""
    ai_requested = False

    with st.sidebar:
        st.title("Solar Gaze")
        st.caption("Enterprise Solar Path & Shadow Analysis")

        # --- Building Images ---
        ai_requested = _render_image_upload()

        st.divider()

        # --- Building Dimensions ---
        _render_building_controls()

        st.divider()

        # --- Location ---
        _render_location_controls()

        st.divider()

        # --- Date & Time ---
        _render_datetime_controls()

    return ai_requested


def _render_image_upload() -> bool:
    st.subheader("AI Building Analysis")
    st.caption(
        "Upload building photos and AI Vision will automatically "
        "detect dimensions, roof type, orientation, materials, and "
        "nearby structures — then update the 3D model to match."
    )

    aerial_file = st.file_uploader(
        "Aerial / Google Maps View",
        type=["jpg", "jpeg", "png", "webp"],
        key="aerial_upload",
        help="Screenshot from Google Maps satellite view works best",
    )
    front_file = st.file_uploader(
        "Front Photo",
        type=["jpg", "jpeg", "png", "webp"],
        key="front_upload",
        help="Street-level photo of the building front",
    )

    if aerial_file or front_file:
        cols = st.columns(2)
        if aerial_file:
            cols[0].image(aerial_file, caption="Aerial", use_container_width=True)
        if front_file:
            cols[1].image(front_file, caption="Front", use_container_width=True)

    # Show which AI provider is available
    from services.vision_analyzer import _detect_provider
    provider = _detect_provider()
    provider_labels = {"openai": "OpenAI GPT-4o", "gemini": "Google Gemini", "anthropic": "Anthropic Claude"}
    provider_label = provider_labels.get(provider, "")

    if provider != "none":
        st.caption(f"AI Provider: **{provider_label}**")

    # Show what AI already detected
    if st.session_state.get("ai_analyzed"):
        st.success("AI analysis applied to 3D model", icon="✅")

    analyze_clicked = st.button(
        "Analyze with AI",
        type="primary",
        disabled=not (aerial_file or front_file),
        use_container_width=True,
        help="Uses AI vision to extract building geometry from photos",
    )

    if analyze_clicked and (aerial_file or front_file):
        if provider == "none":
            st.error(
                "No AI API key found. Add one of these to your `.env` file:\n\n"
                "- `GEMINI_API_KEY=...` (Google Gemini)\n"
                "- `OPENAI_API_KEY=...` (OpenAI GPT-4o)\n"
                "- `ANTHROPIC_API_KEY=...` (Anthropic Claude)"
            )
            return False

        images = []
        for f in [aerial_file, front_file]:
            if f is not None:
                content_type = f.type or "image/jpeg"
                images.append((f.getvalue(), content_type))
        st.session_state["pending_images"] = images
        return True

    return False


def _render_building_controls():
    st.subheader("Building Dimensions")

    if st.session_state.get("ai_analysis") and not st.session_state.get("ai_confirmed"):
        analysis = st.session_state["ai_analysis"]
        st.info(
            f"AI detected: {analysis.building_type}, "
            f"{analysis.stories} stories, "
            f"confidence: {analysis.confidence}"
        )
        if analysis.notes:
            st.caption(analysis.notes)

    # Unit toggle
    use_imperial = st.toggle(
        "Use feet (ft)",
        value=st.session_state.get("use_imperial", False),
        key="input_use_imperial",
    )
    st.session_state.use_imperial = use_imperial

    if use_imperial:
        unit = "ft"
        # Display values converted to feet, store back in meters
        disp_width = st.session_state.building_width * FEET_PER_METER
        disp_depth = st.session_state.building_depth * FEET_PER_METER
        disp_height = st.session_state.building_wall_height * FEET_PER_METER

        new_width_ft = st.number_input(
            f"Width ({unit}) — East-West",
            min_value=3.0,
            max_value=660.0,
            value=round(disp_width, 1),
            step=1.0,
            key="input_width",
        )
        new_depth_ft = st.number_input(
            f"Depth ({unit}) — North-South",
            min_value=3.0,
            max_value=660.0,
            value=round(disp_depth, 1),
            step=1.0,
            key="input_depth",
        )
        new_height_ft = st.number_input(
            f"Wall Height ({unit})",
            min_value=3.0,
            max_value=330.0,
            value=round(disp_height, 1),
            step=1.0,
            key="input_wall_height",
        )
        st.session_state.building_width = new_width_ft * METERS_PER_FOOT
        st.session_state.building_depth = new_depth_ft * METERS_PER_FOOT
        st.session_state.building_wall_height = new_height_ft * METERS_PER_FOOT
    else:
        unit = "m"
        st.session_state.building_width = st.number_input(
            f"Width ({unit}) — East-West",
            min_value=1.0,
            max_value=200.0,
            value=st.session_state.building_width,
            step=0.5,
            key="input_width",
        )
        st.session_state.building_depth = st.number_input(
            f"Depth ({unit}) — North-South",
            min_value=1.0,
            max_value=200.0,
            value=st.session_state.building_depth,
            step=0.5,
            key="input_depth",
        )
        st.session_state.building_wall_height = st.number_input(
            f"Wall Height ({unit})",
            min_value=1.0,
            max_value=100.0,
            value=st.session_state.building_wall_height,
            step=0.5,
            key="input_wall_height",
        )

    roof_options = [
        "flat", "gable", "hip", "shed", "mansard",
        "gambrel", "butterfly", "sawtooth", "dutch_gable",
    ]
    current_roof = st.session_state.building_roof_type
    if current_roof not in roof_options:
        current_roof = "gable"
    current_idx = roof_options.index(current_roof)
    st.session_state.building_roof_type = st.selectbox(
        "Roof Type",
        options=roof_options,
        index=current_idx,
        format_func=lambda x: x.replace("_", " ").title(),
        key="input_roof_type",
    )

    if st.session_state.building_roof_type != "flat":
        st.session_state.building_roof_pitch = st.slider(
            "Roof Pitch (degrees)",
            min_value=5.0,
            max_value=75.0,
            value=st.session_state.building_roof_pitch,
            step=1.0,
            key="input_roof_pitch",
        )

    st.session_state.building_orientation = st.slider(
        "Building Orientation (degrees from N)",
        min_value=0.0,
        max_value=359.0,
        value=st.session_state.building_orientation,
        step=1.0,
        key="input_orientation",
    )


def _render_location_controls():
    st.subheader("Location")

    preset_names = ["Custom"] + sorted(LOCATION_PRESETS.keys())
    current_preset = st.session_state.get("location_name", "Custom")
    if current_preset not in preset_names:
        current_preset = "Custom"

    selected_preset = st.selectbox(
        "Location Presets",
        preset_names,
        index=preset_names.index(current_preset),
        key="location_preset_select",
    )

    if selected_preset != "Custom" and selected_preset != st.session_state.get(
        "location_name"
    ):
        preset = LOCATION_PRESETS[selected_preset]
        st.session_state.latitude = preset["lat"]
        st.session_state.longitude = preset["lon"]
        st.session_state.timezone = preset["tz"]
        st.session_state.location_name = selected_preset
        st.rerun()

    st.session_state.latitude = st.number_input(
        "Latitude",
        min_value=-90.0,
        max_value=90.0,
        value=st.session_state.latitude,
        step=0.01,
        format="%.4f",
        key="input_lat",
    )
    st.session_state.longitude = st.number_input(
        "Longitude",
        min_value=-180.0,
        max_value=180.0,
        value=st.session_state.longitude,
        step=0.01,
        format="%.4f",
        key="input_lon",
    )

    import pytz

    all_tz = sorted(pytz.all_timezones)
    current_tz_idx = (
        all_tz.index(st.session_state.timezone)
        if st.session_state.timezone in all_tz
        else 0
    )
    st.session_state.timezone = st.selectbox(
        "Timezone",
        options=all_tz,
        index=current_tz_idx,
        key="input_tz",
    )

    # Coordinates help
    with st.expander("How to find coordinates"):
        st.markdown(
            """**Google Maps (Desktop)**
1. Go to [maps.google.com](https://maps.google.com)
2. Right-click the building location
3. Click the coordinates at the top of the menu — they copy to clipboard
4. Format: `latitude, longitude` (e.g. `47.3769, 8.5417`)

**Google Maps (Mobile)**
1. Long-press on the building location
2. The coordinates appear in the search bar or info panel at the bottom
3. Tap to copy

**Apple Maps / iPhone**
1. Long-press the location to drop a pin
2. Tap the pin, then swipe up on the info card
3. Coordinates are listed under the address

**iPhone Compass App**
1. Open the Compass app
2. Your current coordinates are shown at the bottom of the screen

**GPS Coordinates App**
- Search for "GPS Coordinates" in your app store for dedicated tools with copy-paste support"""
        )


def _render_datetime_controls():
    st.subheader("Date & Time")

    st.session_state.selected_date = st.date_input(
        "Date",
        value=st.session_state.selected_date,
        key="input_date",
    )

    st.session_state.selected_hour = st.slider(
        "Hour",
        min_value=0,
        max_value=23,
        value=st.session_state.selected_hour,
        key="input_hour",
    )

    st.session_state.selected_minute = st.slider(
        "Minute",
        min_value=0,
        max_value=59,
        value=st.session_state.selected_minute,
        step=5,
        key="input_minute",
    )

    # Animation controls
    st.session_state.animate = st.checkbox(
        "Animate through day",
        value=st.session_state.animate,
        key="input_animate",
    )

    if st.session_state.animate:
        st.session_state.animation_speed = st.select_slider(
            "Animation speed",
            options=[0.5, 1.0, 2.0, 4.0],
            value=st.session_state.animation_speed,
            format_func=lambda x: f"{x}x",
            key="input_anim_speed",
        )
