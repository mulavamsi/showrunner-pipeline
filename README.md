# Showrunner Pipeline

An AI-powered micro-drama production pipeline built with Python, Streamlit, SQLite, and the Claude API. The pipeline takes a director's creative vision and an episode script and walks through every production stage — from storyboard to audio planning — generating the artifacts that would be sent to real video and audio APIs.

Built as a V1 proof-of-concept: Stages 1–3 make real Claude API calls. Production stages 4–6 are fully scaffolded and labeled STUB, ready to be wired to Runway, ElevenLabs, and Sync.so.

---

## The 6 Stages

| # | Stage | What it does | API |
|---|---|---|---|
| 1 | **Director Memory** | Capture show name, director style, visual references, tone, color palette, mood. Saved to SQLite. | — |
| 2 | **Story Understanding** | Paste or upload an episode script. Claude extracts scene list, characters, location, and emotional beat per scene. | Claude (Haiku) |
| 3 | **Storyboard Automation** | For each scene, Claude generates shot type, camera angle, framing notes, and a visual description — informed by the director's style and emotional beat. Human approval required per scene before proceeding. | Claude (Haiku) |
| 4 | **Video Generation** | Assembles the full video generation prompt for each approved scene (visual description + shot + director style + emotional beat). Displays prompt labeled STUB — no clip is rendered. | STUB → Runway Gen-3 / Kling 1.5 |
| 5 | **Auto Editing** | Builds a rough cut assembly list: scene order, estimated clip duration (derived from shot type), and transition type between scenes. | STUB → MoviePy / DaVinci |
| 6 | **Audio + Lip Sync** | Per scene: voice clone instruction (ElevenLabs), lip sync mapping (Sync.so), and music variant selection. Ends with a DEPLOY-READY summary card showing all 6 stages complete. | STUB → ElevenLabs / Sync.so |

---

## Stack

- **Python 3.9+**
- **Streamlit** — UI and navigation
- **SQLite** — project and stage data persistence (no server required)
- **Anthropic Python SDK** — Claude API calls in Stages 2 & 3
- **python-dotenv** — API key management

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/mulavamsikrishna96/showrunner-pipeline.git
cd showrunner-pipeline

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Anthropic API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

Get an API key at [console.anthropic.com](https://console.anthropic.com).

---

## Running

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Use the sidebar to navigate between stages. Complete each stage in order — later stages are gated on earlier ones.

---

## Project Structure

```
showrunner-pipeline/
├── app.py                          # Streamlit entry point + sidebar nav
├── requirements.txt
├── .env                            # ANTHROPIC_API_KEY (gitignored)
├── config/
│   └── settings.py                 # All prompt templates and model names
├── memory/
│   └── database.py                 # SQLite helpers (projects + stage_data tables)
└── stages/
    ├── stage1_director_memory.py
    ├── stage2_story_understanding.py
    ├── stage3_storyboard_automation.py
    ├── stage4_video_generation.py
    ├── stage5_auto_editing.py
    └── stage6_audio_lipsync.py
```

---

## Wiring the STUB Stages to Real APIs

| Stage | STUB target | What to replace |
|---|---|---|
| 4 | Runway Gen-3 / Kling 1.5 | Send `video_prompts[key]` to the video generation API; store returned clip URL |
| 5 | MoviePy / DaVinci Resolve API | Pass `cut_list` to an NLE or programmatic editor |
| 6 — voice | ElevenLabs | POST `voice_instruction` payload to `/v1/text-to-speech` |
| 6 — lip sync | Sync.so | POST video + audio clip pair to Sync.so job API |
| 6 — music | Licensed music library API | Use `music_variant` string to query and select a track |

---

## License

MIT
