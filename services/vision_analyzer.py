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

VISION_PROMPT = """Analyze this building image and extract structural measurements.

Use these scale references to estimate dimensions:
- Standard door height: ~2.1m
- Standard window: ~1.2m wide x 1.5m tall
- Garage door: ~2.4m high x 5m wide
- Average car length: ~4.5m
- Story height: ~3.0m (residential), ~4.0m (commercial)
- Standard brick: 215mm x 65mm

Return a JSON object with EXACTLY this structure (no markdown, no code fences):
{
    "geometry": {
        "width": <float, east-west dimension in meters>,
        "depth": <float, north-south dimension in meters>,
        "wall_height": <float, wall height in meters>,
        "roof_type": "<flat|gable|hip|shed|mansard|gambrel|butterfly|sawtooth|dutch_gable>",
        "roof_pitch": <float, degrees 0-80>,
        "orientation": <float, degrees 0-360, 0=north>
    },
    "building_type": "<residential|commercial|industrial|mixed>",
    "stories": <int>,
    "materials": ["<material1>", "<material2>"],
    "confidence": "<low|medium|high>",
    "notes": "<brief description of the building>",
    "nearby_structures": [
        {
            "type": "<tree|fence|wall|shed|garage|other>",
            "description": "<brief description>",
            "relative_position": "<N|NE|E|SE|S|SW|W|NW of building>",
            "estimated_height": <float, meters>
        }
    ]
}

If you cannot determine a measurement, use reasonable defaults:
- width: 10.0, depth: 8.0, wall_height: 6.0
- roof_type: gable, roof_pitch: 30
Be conservative with estimates. Note your confidence level."""


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
            self.client = genai.GenerativeModel("gemini-2.0-flash")

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
            max_tokens=1500,
            messages=[{"role": "user", "content": content}],
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

        geometry = BuildingGeometry(
            width=float(geom_data.get("width", 10.0)),
            depth=float(geom_data.get("depth", 8.0)),
            wall_height=float(geom_data.get("wall_height", 6.0)),
            roof_type=roof_type,
            roof_pitch=float(geom_data.get("roof_pitch", 30.0)),
            orientation=float(geom_data.get("orientation", 0.0)),
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
