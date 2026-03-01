# Theo's Solar Gazer

**Real-time 3D solar path, shadow, and interior daylight simulation for any building, anywhere in the world.**

A browser-based tool for architects, engineers, homeowners, and solar professionals to visualize how sunlight interacts with a building throughout the day and year — including shadow casting, sun path tracking, and light penetration through windows and glass walls.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red)
![Plotly](https://img.shields.io/badge/3D_Engine-Plotly-purple)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Features

### Solar Analysis
- **Sun path arc** with hourly position markers for any date and GPS location
- **Real-time sun position** — azimuth, elevation, sunrise/sunset, day length
- **120+ city presets** across 6 continents, or enter custom coordinates

### Shadow Simulation
- **Dynamic shadow projection** from the building onto the ground plane
- **Shadow metrics** — length, area, and compass direction
- **Full-day animation** — watch shadows sweep across the site from sunrise to sunset

### Interior Daylight
- **Window and glass wall configuration** on all four walls
- **Adjustable window dimensions** — width, height, and sill height
- **Interior light patches** — see exactly where sunlight falls on the floor through glazing
- **See-through mode** — make walls transparent to view interior light from any angle

### Building Modeling
- **9 roof types** — flat, gable, hip, shed, mansard, gambrel, butterfly, sawtooth, dutch gable
- **Adjustable pitch and orientation** (0-359 degrees)
- **Metric and imperial units**
- **Nearby structures** — trees and buildings that affect shadow context

### AI Vision (Optional)
- Upload an **aerial/satellite photo** and/or **street-level photo**
- AI automatically detects **dimensions, stories, roof type, materials, and nearby structures**
- Supports **OpenAI GPT-4o**, **Google Gemini**, and **Anthropic Claude**

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/tkaitis/Solar-Gaze.git
cd Solar-Gaze
pip install -r requirements.txt
```

### 2. Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

### 3. AI Vision (optional)

Create a `.env` file in the project root with one of:

```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## How It Works

1. **Set location** — pick a city or enter lat/lon coordinates
2. **Define building** — set dimensions, roof type, pitch, and orientation
3. **Configure windows** — choose solid wall, window, or glass wall for each face
4. **Pick date and time** — the 3D scene updates instantly with sun position and shadows
5. **Animate** — play through the full day to see shadows and interior light move
6. **AI analysis** — upload a photo to auto-detect building geometry

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit |
| 3D Engine | Plotly (WebGL) |
| Solar Math | pvlib |
| Geometry | NumPy, SciPy |
| AI Vision | OpenAI / Gemini / Anthropic |
| Data Models | Pydantic |

---

## Use Cases

- **Architects** — early-stage massing studies, facade orientation, daylighting strategy
- **Solar professionals** — panel placement, shading analysis, site assessment
- **Homeowners** — understand which rooms get sun and when, plan renovations
- **Real estate** — evaluate natural light as a property feature
- **Urban planners** — shadow impact studies for new developments
- **Students** — learn solar geometry and building science interactively

---

## Project Structure

```
Solar_Gaze/
  app.py                    # Main Streamlit application
  models/
    building.py             # Building geometry and AI analysis data models
    solar.py                # Solar position and path data models
  services/
    solar_engine.py         # Sun position and path calculations (pvlib)
    geometry_builder.py     # 3D mesh generation for buildings and structures
    shadow_calculator.py    # Shadow projection from sun position
    light_calculator.py     # Interior light patch computation through windows
    vision_analyzer.py      # AI vision analysis (OpenAI / Gemini / Anthropic)
  ui/
    sidebar_controls.py     # Sidebar inputs and controls
    session_state.py        # Streamlit session state management
    analysis_panel.py       # Dashboard metrics panel
  visualization/
    scene_3d.py             # Plotly 3D scene assembly and animation
    color_themes.py         # Color palette definitions
  assets/                   # Banner images and branding
  requirements.txt
  .env                      # API keys (not committed)
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

Built by [Theo Kaitis](https://github.com/tkaitis)
