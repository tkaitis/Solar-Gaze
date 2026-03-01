from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from models.building import BuildingAnalysis, BuildingGeometry, WallGlazing, WindowConfig


LOCATION_REGIONS = {
    "North America": {
        "New York": {"lat": 40.7128, "lon": -74.0060, "tz": "America/New_York"},
        "Los Angeles": {"lat": 34.0522, "lon": -118.2437, "tz": "America/Los_Angeles"},
        "Chicago": {"lat": 41.8781, "lon": -87.6298, "tz": "America/Chicago"},
        "Houston": {"lat": 29.7604, "lon": -95.3698, "tz": "America/Chicago"},
        "Phoenix": {"lat": 33.4484, "lon": -112.0740, "tz": "America/Phoenix"},
        "Philadelphia": {"lat": 39.9526, "lon": -75.1652, "tz": "America/New_York"},
        "San Antonio": {"lat": 29.4241, "lon": -98.4936, "tz": "America/Chicago"},
        "San Diego": {"lat": 32.7157, "lon": -117.1611, "tz": "America/Los_Angeles"},
        "Dallas": {"lat": 32.7767, "lon": -96.7970, "tz": "America/Chicago"},
        "San Francisco": {"lat": 37.7749, "lon": -122.4194, "tz": "America/Los_Angeles"},
        "Seattle": {"lat": 47.6062, "lon": -122.3321, "tz": "America/Los_Angeles"},
        "Denver": {"lat": 39.7392, "lon": -104.9903, "tz": "America/Denver"},
        "Washington DC": {"lat": 38.9072, "lon": -77.0369, "tz": "America/New_York"},
        "Boston": {"lat": 42.3601, "lon": -71.0589, "tz": "America/New_York"},
        "Atlanta": {"lat": 33.7490, "lon": -84.3880, "tz": "America/New_York"},
        "Miami": {"lat": 25.7617, "lon": -80.1918, "tz": "America/New_York"},
        "Toronto": {"lat": 43.6532, "lon": -79.3832, "tz": "America/Toronto"},
        "Vancouver": {"lat": 49.2827, "lon": -123.1207, "tz": "America/Vancouver"},
        "Montreal": {"lat": 45.5017, "lon": -73.5673, "tz": "America/Toronto"},
        "Mexico City": {"lat": 19.4326, "lon": -99.1332, "tz": "America/Mexico_City"},
    },
    "South America": {
        "Sao Paulo": {"lat": -23.5505, "lon": -46.6333, "tz": "America/Sao_Paulo"},
        "Buenos Aires": {"lat": -34.6037, "lon": -58.3816, "tz": "America/Argentina/Buenos_Aires"},
        "Rio de Janeiro": {"lat": -22.9068, "lon": -43.1729, "tz": "America/Sao_Paulo"},
        "Bogota": {"lat": 4.7110, "lon": -74.0721, "tz": "America/Bogota"},
        "Lima": {"lat": -12.0464, "lon": -77.0428, "tz": "America/Lima"},
        "Santiago": {"lat": -33.4489, "lon": -70.6693, "tz": "America/Santiago"},
    },
    "Europe": {
        "London": {"lat": 51.5074, "lon": -0.1278, "tz": "Europe/London"},
        "Paris": {"lat": 48.8566, "lon": 2.3522, "tz": "Europe/Paris"},
        "Berlin": {"lat": 52.5200, "lon": 13.4050, "tz": "Europe/Berlin"},
        "Madrid": {"lat": 40.4168, "lon": -3.7038, "tz": "Europe/Madrid"},
        "Rome": {"lat": 41.9028, "lon": 12.4964, "tz": "Europe/Rome"},
        "Amsterdam": {"lat": 52.3676, "lon": 4.9041, "tz": "Europe/Amsterdam"},
        "Vienna": {"lat": 48.2082, "lon": 16.3738, "tz": "Europe/Vienna"},
        "Barcelona": {"lat": 41.3874, "lon": 2.1686, "tz": "Europe/Madrid"},
        "Munich": {"lat": 48.1351, "lon": 11.5820, "tz": "Europe/Berlin"},
        "Milan": {"lat": 45.4642, "lon": 9.1900, "tz": "Europe/Rome"},
        "Prague": {"lat": 50.0755, "lon": 14.4378, "tz": "Europe/Prague"},
        "Brussels": {"lat": 50.8503, "lon": 4.3517, "tz": "Europe/Brussels"},
        "Stockholm": {"lat": 59.3293, "lon": 18.0686, "tz": "Europe/Stockholm"},
        "Oslo": {"lat": 59.9139, "lon": 10.7522, "tz": "Europe/Oslo"},
        "Copenhagen": {"lat": 55.6761, "lon": 12.5683, "tz": "Europe/Copenhagen"},
        "Helsinki": {"lat": 60.1699, "lon": 24.9384, "tz": "Europe/Helsinki"},
        "Warsaw": {"lat": 52.2297, "lon": 21.0122, "tz": "Europe/Warsaw"},
        "Budapest": {"lat": 47.4979, "lon": 19.0402, "tz": "Europe/Budapest"},
        "Lisbon": {"lat": 38.7223, "lon": -9.1393, "tz": "Europe/Lisbon"},
        "Dublin": {"lat": 53.3498, "lon": -6.2603, "tz": "Europe/Dublin"},
        "Zurich": {"lat": 47.3769, "lon": 8.5417, "tz": "Europe/Zurich"},
        "Geneva": {"lat": 46.2044, "lon": 6.1432, "tz": "Europe/Zurich"},
        "Athens": {"lat": 37.9838, "lon": 23.7275, "tz": "Europe/Athens"},
        "Bucharest": {"lat": 44.4268, "lon": 26.1025, "tz": "Europe/Bucharest"},
        "Moscow": {"lat": 55.7558, "lon": 37.6173, "tz": "Europe/Moscow"},
        "St Petersburg": {"lat": 59.9343, "lon": 30.3351, "tz": "Europe/Moscow"},
        "Nicosia": {"lat": 35.1856, "lon": 33.3823, "tz": "Asia/Nicosia"},
    },
    "Turkey": {
        "Istanbul": {"lat": 41.0082, "lon": 28.9784, "tz": "Europe/Istanbul"},
        "Ankara": {"lat": 39.9334, "lon": 32.8597, "tz": "Europe/Istanbul"},
        "Mersin": {"lat": 36.8121, "lon": 34.6415, "tz": "Europe/Istanbul"},
        "Izmir": {"lat": 38.4192, "lon": 27.1287, "tz": "Europe/Istanbul"},
        "Antalya": {"lat": 36.8969, "lon": 30.7133, "tz": "Europe/Istanbul"},
    },
    "Middle East": {
        "Dubai": {"lat": 25.2048, "lon": 55.2708, "tz": "Asia/Dubai"},
        "Abu Dhabi": {"lat": 24.4539, "lon": 54.3773, "tz": "Asia/Dubai"},
        "Riyadh": {"lat": 24.7136, "lon": 46.6753, "tz": "Asia/Riyadh"},
        "Doha": {"lat": 25.2854, "lon": 51.5310, "tz": "Asia/Qatar"},
        "Tel Aviv": {"lat": 32.0853, "lon": 34.7818, "tz": "Asia/Jerusalem"},
        "Beirut": {"lat": 33.8938, "lon": 35.5018, "tz": "Asia/Beirut"},
        "Tehran": {"lat": 35.6892, "lon": 51.3890, "tz": "Asia/Tehran"},
    },
    "Africa": {
        "Cairo": {"lat": 30.0444, "lon": 31.2357, "tz": "Africa/Cairo"},
        "Cape Town": {"lat": -33.9249, "lon": 18.4241, "tz": "Africa/Johannesburg"},
        "Johannesburg": {"lat": -26.2041, "lon": 28.0473, "tz": "Africa/Johannesburg"},
        "Lagos": {"lat": 6.5244, "lon": 3.3792, "tz": "Africa/Lagos"},
        "Nairobi": {"lat": -1.2921, "lon": 36.8219, "tz": "Africa/Nairobi"},
        "Casablanca": {"lat": 33.5731, "lon": -7.5898, "tz": "Africa/Casablanca"},
        "Addis Ababa": {"lat": 9.0250, "lon": 38.7469, "tz": "Africa/Addis_Ababa"},
        "Dar es Salaam": {"lat": -6.7924, "lon": 39.2083, "tz": "Africa/Dar_es_Salaam"},
    },
    "South Asia": {
        "Mumbai": {"lat": 19.0760, "lon": 72.8777, "tz": "Asia/Kolkata"},
        "Delhi": {"lat": 28.7041, "lon": 77.1025, "tz": "Asia/Kolkata"},
        "Bangalore": {"lat": 12.9716, "lon": 77.5946, "tz": "Asia/Kolkata"},
        "Kolkata": {"lat": 22.5726, "lon": 88.3639, "tz": "Asia/Kolkata"},
        "Chennai": {"lat": 13.0827, "lon": 80.2707, "tz": "Asia/Kolkata"},
        "Karachi": {"lat": 24.8607, "lon": 67.0011, "tz": "Asia/Karachi"},
        "Dhaka": {"lat": 23.8103, "lon": 90.4125, "tz": "Asia/Dhaka"},
    },
    "East & Southeast Asia": {
        "Tokyo": {"lat": 35.6762, "lon": 139.6503, "tz": "Asia/Tokyo"},
        "Osaka": {"lat": 34.6937, "lon": 135.5023, "tz": "Asia/Tokyo"},
        "Seoul": {"lat": 37.5665, "lon": 126.9780, "tz": "Asia/Seoul"},
        "Beijing": {"lat": 39.9042, "lon": 116.4074, "tz": "Asia/Shanghai"},
        "Shanghai": {"lat": 31.2304, "lon": 121.4737, "tz": "Asia/Shanghai"},
        "Guangzhou": {"lat": 23.1291, "lon": 113.2644, "tz": "Asia/Shanghai"},
        "Shenzhen": {"lat": 22.5431, "lon": 114.0579, "tz": "Asia/Shanghai"},
        "Hong Kong": {"lat": 22.3193, "lon": 114.1694, "tz": "Asia/Hong_Kong"},
        "Taipei": {"lat": 25.0330, "lon": 121.5654, "tz": "Asia/Taipei"},
        "Singapore": {"lat": 1.3521, "lon": 103.8198, "tz": "Asia/Singapore"},
        "Bangkok": {"lat": 13.7563, "lon": 100.5018, "tz": "Asia/Bangkok"},
        "Kuala Lumpur": {"lat": 3.1390, "lon": 101.6869, "tz": "Asia/Kuala_Lumpur"},
        "Jakarta": {"lat": -6.2088, "lon": 106.8456, "tz": "Asia/Jakarta"},
        "Manila": {"lat": 14.5995, "lon": 120.9842, "tz": "Asia/Manila"},
        "Ho Chi Minh City": {"lat": 10.8231, "lon": 106.6297, "tz": "Asia/Ho_Chi_Minh"},
        "Hanoi": {"lat": 21.0278, "lon": 105.8342, "tz": "Asia/Ho_Chi_Minh"},
    },
    "Oceania": {
        "Sydney": {"lat": -33.8688, "lon": 151.2093, "tz": "Australia/Sydney"},
        "Melbourne": {"lat": -37.8136, "lon": 144.9631, "tz": "Australia/Melbourne"},
        "Brisbane": {"lat": -27.4698, "lon": 153.0251, "tz": "Australia/Brisbane"},
        "Perth": {"lat": -31.9505, "lon": 115.8605, "tz": "Australia/Perth"},
        "Auckland": {"lat": -36.8485, "lon": 174.7633, "tz": "Pacific/Auckland"},
    },
}

# Flat lookup for backward compatibility
LOCATION_PRESETS = {}
for _cities in LOCATION_REGIONS.values():
    LOCATION_PRESETS.update(_cities)


def init_session_state():
    defaults = {
        # Location
        "latitude": 37.7749,
        "longitude": -122.4194,
        "timezone": "America/Los_Angeles",
        "location_name": "San Francisco",
        "location_region": "North America",
        # Date/Time
        "selected_date": date.today(),
        "selected_hour": 12,
        "selected_minute": 0,
        # Building geometry
        "building_width": 10.0,
        "building_depth": 8.0,
        "building_wall_height": 6.0,
        "building_roof_type": "gable",
        "building_roof_pitch": 30.0,
        "building_orientation": 0.0,
        # Units
        "use_imperial": False,
        # AI analysis
        "ai_analysis": None,
        "ai_analyzed": False,
        # Animation
        "animate": False,
        "animation_speed": 1.0,
        "animation_hour": 6.0,
        # Windows & glazing
        "glazing_south": "none",
        "glazing_north": "none",
        "glazing_east": "none",
        "glazing_west": "none",
        "win_width_south": 50,
        "win_height_south": 50,
        "win_sill_south": 15,
        "win_width_north": 50,
        "win_height_north": 50,
        "win_sill_north": 15,
        "win_width_east": 50,
        "win_height_east": 50,
        "win_sill_east": 15,
        "win_width_west": 50,
        "win_height_west": 50,
        "win_sill_west": 15,
        "transparent_building": False,
        # UI
        "show_help": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_building_geometry() -> BuildingGeometry:
    return BuildingGeometry(
        width=st.session_state.building_width,
        depth=st.session_state.building_depth,
        wall_height=st.session_state.building_wall_height,
        roof_type=st.session_state.building_roof_type,
        roof_pitch=st.session_state.building_roof_pitch,
        orientation=st.session_state.building_orientation,
    )


def get_window_config() -> WindowConfig:
    """Build a WindowConfig from current session state."""
    def _wall(direction: str) -> WallGlazing:
        return WallGlazing(
            glazing_type=st.session_state.get(f"glazing_{direction}", "none"),
            window_width_frac=st.session_state.get(f"win_width_{direction}", 50) / 100,
            window_height_frac=st.session_state.get(f"win_height_{direction}", 50) / 100,
            sill_height_frac=st.session_state.get(f"win_sill_{direction}", 15) / 100,
        )
    return WindowConfig(
        south=_wall("south"),
        north=_wall("north"),
        east=_wall("east"),
        west=_wall("west"),
    )


def get_selected_datetime() -> datetime:
    return datetime.combine(
        st.session_state.selected_date,
        datetime.min.time().replace(
            hour=st.session_state.selected_hour,
            minute=st.session_state.selected_minute,
        ),
    )
