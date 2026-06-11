"""
All prompts and external model instructions live here.
No prompt strings should be defined inline in stage files.
"""

# ── Stage 2: Story Understanding ──────────────────────────────────────────────
SCRIPT_PARSE_PROMPT = """
You are a professional script analyst. Given the episode script below, extract a structured scene breakdown.

For each scene return a JSON object with these exact keys:
- scene_number (int, starting at 1)
- location (string — interior/exterior, place, time of day, e.g. "INT. SAFE HOUSE - NIGHT")
- characters (list of strings — character names as written in the script, uppercase)
- emotional_beat (string — one precise phrase capturing the dominant emotion of the scene, e.g. "quiet dread before action", "desperate grief breaking into rage")
- summary (string — 1-2 sentences describing what happens in the scene)

Return a JSON array of scene objects. Return valid JSON only — no commentary, no markdown fences, no explanation outside the JSON.

SCRIPT:
{script}
"""

EMOTIONAL_BEAT_MODEL = "claude-haiku-4-5-20251001"

# ── Stage 3: Storyboard Automation ────────────────────────────────────────────
STORYBOARD_PROMPT = """
You are a cinematographer and storyboard artist working on a micro-drama episode.

DIRECTOR'S CINEMATIC GRAMMAR:
- Style: {director_style}
- Visual References: {visual_references}
- Color Palette: {color_palette}
- Tone: {tone}
- Mood: {mood}

SCENE TO STORYBOARD:
- Scene Number: {scene_number}
- Location: {location}
- Characters: {characters}
- Emotional Beat: {emotional_beat}
- Scene Summary: {summary}

Based on the director's style and the scene's emotional beat, generate a storyboard specification.

Return a JSON object with exactly these keys:
- shot_type (string — one of: close-up, medium close-up, medium, wide, extreme wide, over-the-shoulder, two-shot, insert, POV)
- camera_angle (string — e.g. eye-level, low angle, high angle, dutch tilt, bird's eye, worm's eye)
- framing_notes (string — one sentence maximum on composition and depth of field, reflecting the director's style)
- visual_description (string — one vivid sentence describing exactly what the camera sees, written like a shot description in a shooting script)

Return valid JSON only. No commentary outside the JSON.
"""

STORYBOARD_MODEL = "claude-haiku-4-5-20251001"

# ── Stage 3: Storyboard Automation ────────────────────────────────────────────
# ── Stage 4: Video Generation ─────────────────────────────────────────────────
VIDEO_GEN_PROMPT_TEMPLATE = """{visual_description} {shot_type} shot, {camera_angle}. {framing_notes} Color palette: {color_palette}. Mood: {mood}. Tone: {tone}. Director style: {director_style}. Emotional register: {emotional_beat}. Cinematic, high production value, no text or subtitles. Duration: 5 seconds."""

# ── Stage 6: Audio + Lip Sync ──────────────────────────────────────────────────
VOICE_CLONE_INSTRUCTION_TEMPLATE = """
[VOICE CLONE INSTRUCTION — Scene {scene_number}]
Characters in scene: {characters}
Emotional beat: {emotional_beat}
Tone notes: {tone}
Provider: ElevenLabs
Action: Clone voice per character profile, generate dialogue audio for this scene.
"""

LIP_SYNC_MAPPING_TEMPLATE = """
[LIP SYNC MAPPING — Scene {scene_number}]
Video clip: scene_{scene_number}_STUB.mp4
Audio clip: scene_{scene_number}_voice_STUB.mp3
Provider: Sync.so
Action: Align mouth movement to generated audio.
"""

MUSIC_SELECTION_TEMPLATE = """
[MUSIC SELECTION — Scene {scene_number}]
Mood: {mood}
Emotional beat: {emotional_beat}
Action: Select music variant from licensed library matching mood. Fade in at scene start, fade out at end.
"""
