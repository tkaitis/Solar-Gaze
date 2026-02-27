from __future__ import annotations

import base64
import json
import os

from dotenv import load_dotenv

from models.building import BuildingAnalysis, BuildingGeometry, NearbyStructure

load_dotenv()


def _get_secret(key: str) -> str | None:
    """Read a secret from .env or Streamlit Cloud secrets."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key)
    except Exception:
        return None

VISION_PROMPT = """You are an expert architectural surveyor. Analyze the building image(s) and extract precise structural measurements for a 3D model.

STEP 1 — IDENTIFY SCALE REFERENCES in the image. Look for ANY of these and count them:
- Doors (standard ~2.1m tall, ~0.9m wide)
- Windows (standard ~1.2m wide x 1.5m tall)
- Garage doors (~2.4m tall x 5m wide)
- Cars (~4.5m long x 1.8m wide)
- People (~1.7m tall)
- Story height: ~3.0m residential, ~3.5m commercial, ~4.5m industrial
- Standard brick: 215mm x 65mm (count visible courses)
- Pavement slabs: typically 600mm x 600mm
- Road lane width: ~3.5m

STEP 2 — MEASURE THE BUILDING using those references:
- WIDTH: the building's longest horizontal face dimension (meters)
- DEPTH: the perpendicular dimension (meters). If only one view, estimate depth as 60-80% of width for residential, 50-70% for commercial.
- WALL HEIGHT: measure from ground to where the roof starts (eave line), NOT to the roof peak. Count stories x story height. A 2-story house is typically 6-7m wall height.
- ROOF PITCH: estimate the angle of the roof slope in degrees. A shallow roof is 15-20°, moderate is 25-35°, steep is 40-55°.

STEP 3 — IDENTIFY THE ROOF TYPE. Choose the BEST match:
- "flat" — no visible slope, may have parapet
- "gable" — classic triangle, two sloping sides meeting at a ridge
- "hip" — all four sides slope inward to the ridge
- "shed" — single slope, one side higher than the other
- "mansard" — steep lower slope, shallow upper slope (French style)
- "gambrel" — barn-style, each side has two slopes (steep lower, shallow upper)
- "butterfly" — V-shaped, two slopes angling down toward center
- "sawtooth" — repeating ridges (industrial/factory)
- "dutch_gable" — hip roof with a small gable (vertical triangle) at the top

STEP 4 — ESTIMATE ORIENTATION from aerial view (if available):
- 0° = front faces North, 90° = front faces East, 180° = front faces South, 270° = front faces West
- If no aerial view, use 0° as default

CONSTRAINTS — values must stay within these ranges:
- width: 1.0 to 200.0 meters
- depth: 1.0 to 200.0 meters
- wall_height: 1.0 to 100.0 meters
- roof_pitch: 5.0 to 75.0 degrees
- orientation: 0.0 to 359.0 degrees

Return ONLY a JSON object (no markdown, no code fences, no explanation):
{
    "geometry": {
        "width": <float>,
        "depth": <float>,
        "wall_height": <float>,
        "roof_type": "<one of the types above>",
        "roof_pitch": <float>,
        "orientation": <float>
    },
    "building_type": "<residential|commercial|industrial|mixed>",
    "stories": <int>,
    "materials": ["<material1>", "<material2>"],
    "confidence": "<low|medium|high>",
    "notes": "<brief description including what scale references you used>",
    "nearby_structures": [
        {
            "type": "<tree|fence|wall|shed|garage|building|other>",
            "description": "<brief description>",
            "relative_position": "<N|NE|E|SE|S|SW|W|NW>",
            "estimated_height": <float, meters>
        }
    ]
}"""


def _detect_provider() -> str:
    """Auto-detect which AI provider is configured, preferring OpenAI > Gemini > Anthropic."""
    if _get_secret("OPENAI_API_KEY"):
        return "openai"
    if _get_secret("GEMINI_API_KEY") or _get_secret("GOOGLE_API_KEY"):
        return "gemini"
    if _get_secret("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "none"


class VisionAnalyzer:
    """Extract building geometry from photos using AI vision (Gemini, OpenAI, or Anthropic)."""

    def __init__(self, provider: str | None = None):
        self.provider = provider or _detect_provider()

        if self.provider == "gemini":
            import google.generativeai as genai
            api_key = _get_secret("GEMINI_API_KEY") or _get_secret("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel("gemini-2.0-flash-001")

        elif self.provider == "openai":
            import openai
            api_key = _get_secret("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found")
            self.client = openai.OpenAI(api_key=api_key)

        elif self.provider == "anthropic":
            import anthropic
            api_key = _get_secret("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found")
            self.client = anthropic.Anthropic(api_key=api_key)

        else:
            raise ValueError(
                "No AI API key found. Set one of: GEMINI_API_KEY, OPENAI_API_KEY, "
                "or ANTHROPIC_API_KEY in your .env file."
            )

    def analyze_images(self, images: list[tuple[bytes, str]]) -> BuildingAnalysis:
        """Analyze building images and return extracted geometry."""
        if self.provider == "gemini":
            raw_text = self._call_gemini(images)
        elif self.provider == "openai":
            raw_text = self._call_openai(images)
        elif self.provider == "anthropic":
            raw_text = self._call_anthropic(images)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        return self._parse_response(raw_text)

    def _call_gemini(self, images: list[tuple[bytes, str]]) -> str:
        """Call Google Gemini with vision."""
        from PIL import Image
        import io

        parts = []
        for img_bytes, media_type in images:
            img = Image.open(io.BytesIO(img_bytes))
            parts.append(img)
        parts.append(VISION_PROMPT)

        response = self.client.generate_content(parts)
        return response.text.strip()

    def _call_openai(self, images: list[tuple[bytes, str]]) -> str:
        """Call OpenAI GPT-4o with vision."""
        content = []
        for img_bytes, media_type in images:
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{b64}",
                    "detail": "high",
                },
            })
        content.append({"type": "text", "text": VISION_PROMPT})

        response = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2000,
            temperature=0.1,
            messages=[
                {"role": "system", "content": "You are an expert architectural surveyor. Return ONLY valid JSON, no markdown fences."},
                {"role": "user", "content": content},
            ],
        )
        return response.choices[0].message.content.strip()

    def _call_anthropic(self, images: list[tuple[bytes, str]]) -> str:
        """Call Anthropic Claude with vision."""
        content = []
        for img_bytes, media_type in images:
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64,
                },
            })
        content.append({"type": "text", "text": VISION_PROMPT})

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text.strip()

    @staticmethod
    def _parse_response(raw_text: str) -> BuildingAnalysis:
        """Parse JSON response from any provider into BuildingAnalysis."""
        # Strip markdown code fences if present
        if "```" in raw_text:
            lines = raw_text.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            raw_text = "\n".join(lines)

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return BuildingAnalysis(
                notes=f"Failed to parse AI response: {raw_text[:200]}",
                confidence="low",
            )

        geom_data = data.get("geometry", {})

        # Validate roof_type against known types
        valid_roofs = {
            "flat", "gable", "hip", "shed", "mansard",
            "gambrel", "butterfly", "sawtooth", "dutch_gable",
        }
        roof_type = geom_data.get("roof_type", "gable")
        if roof_type not in valid_roofs:
            roof_type = "gable"

        def _clamp(val, lo, hi, default):
            try:
                v = float(val)
                return max(lo, min(hi, v))
            except (TypeError, ValueError):
                return default

        geometry = BuildingGeometry(
            width=_clamp(geom_data.get("width"), 1.0, 200.0, 10.0),
            depth=_clamp(geom_data.get("depth"), 1.0, 200.0, 8.0),
            wall_height=_clamp(geom_data.get("wall_height"), 1.0, 100.0, 6.0),
            roof_type=roof_type,
            roof_pitch=_clamp(geom_data.get("roof_pitch"), 5.0, 75.0, 30.0),
            orientation=_clamp(geom_data.get("orientation"), 0.0, 359.0, 0.0),
        )

        nearby = []
        for ns in data.get("nearby_structures", []):
            nearby.append(
                NearbyStructure(
                    type=ns.get("type", "other"),
                    description=ns.get("description", ""),
                    relative_position=ns.get("relative_position", ""),
                    estimated_height=float(ns.get("estimated_height", 3.0)),
                )
            )

        return BuildingAnalysis(
            geometry=geometry,
            building_type=data.get("building_type", "residential"),
            stories=int(data.get("stories", 1)),
            materials=data.get("materials", []),
            confidence=data.get("confidence", "medium"),
            notes=data.get("notes", ""),
            nearby_structures=nearby,
        )
