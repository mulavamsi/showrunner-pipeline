from __future__ import annotations

import streamlit as st
from memory.database import save_stage_data, load_stage_data, get_project, completed_stages
from config.settings import (
    VOICE_CLONE_INSTRUCTION_TEMPLATE,
    LIP_SYNC_MAPPING_TEMPLATE,
    MUSIC_SELECTION_TEMPLATE,
)


def _pick_music_variant(mood: str, emotional_beat: str) -> str:
    mood_l = (mood or "").lower()
    beat_l = (emotional_beat or "").lower()
    if any(w in beat_l for w in ("dread", "tension", "confrontation", "inevitable", "danger")):
        return "Tense strings — low pulse, no melody"
    if any(w in beat_l for w in ("grief", "loss", "sorrow", "despair")):
        return "Sparse piano — single motif, reverb tail"
    if any(w in beat_l for w in ("surveillance", "tactical", "awareness", "alert")):
        return "Minimal percussion — irregular beat, no harmony"
    if any(w in beat_l for w in ("revelation", "shock", "surprise", "deadly")):
        return "Sudden silence → single bass hit"
    if "war" in mood_l or "dark" in mood_l:
        return "Dark ambient drone — industrial texture"
    return "Neutral underscore — light texture, mood-matched"


def render(state: dict):
    st.header("Stage 6 — Audio + Lip Sync")
    st.caption(
        "Displays voice clone instructions, lip sync mappings, and music selections "
        "for each scene. All outputs are stubbed — no audio is generated or rendered."
    )

    project_id = state.get("project_id")
    if not project_id:
        st.warning("No active project. Go to Stage 1 first.")
        if st.button("← Go to Stage 1"):
            state["current_stage"] = 1
            st.rerun()
        return

    project = get_project(project_id)
    breakdown = load_stage_data(project_id, 2, "scene_breakdown")
    approvals = load_stage_data(project_id, 3, "approvals") or {}

    if not breakdown:
        st.warning("No scene breakdown found. Complete Stage 2 first.")
        if st.button("← Go to Stage 2"):
            state["current_stage"] = 2
            st.rerun()
        return

    approved_scenes = [s for s in breakdown if approvals.get(str(s["scene_number"]))]
    if not approved_scenes:
        st.error("No approved scenes. Return to Stage 3 and approve scenes first.")
        if st.button("← Go to Stage 3"):
            state["current_stage"] = 3
            st.rerun()
        return

    st.info(
        f"Active project: **{project['show_name']}** — "
        f"generating audio + lip sync plan for {len(approved_scenes)} scene(s)"
    )

    # ── Per-scene audio plan ───────────────────────────────────────────────────
    audio_plan = {}

    st.divider()
    st.subheader("Audio + Lip Sync Plan")

    for scene in approved_scenes:
        key = str(scene["scene_number"])
        characters = scene.get("characters", [])
        emotional_beat = scene.get("emotional_beat", "")
        music_variant = _pick_music_variant(project.get("mood", ""), emotional_beat)

        voice_instruction = VOICE_CLONE_INSTRUCTION_TEMPLATE.format(
            scene_number=scene["scene_number"],
            characters=", ".join(characters) if characters else "UNKNOWN",
            emotional_beat=emotional_beat,
            tone=project.get("tone") or "Not specified",
        ).strip()

        lip_sync = LIP_SYNC_MAPPING_TEMPLATE.format(
            scene_number=scene["scene_number"],
        ).strip()

        music = MUSIC_SELECTION_TEMPLATE.format(
            scene_number=scene["scene_number"],
            mood=project.get("mood") or "Not specified",
            emotional_beat=emotional_beat,
        ).strip()

        audio_plan[key] = {
            "voice_instruction": voice_instruction,
            "lip_sync": lip_sync,
            "music_variant": music_variant,
            "music_stub": music,
        }

        with st.expander(
            f"Scene {scene['scene_number']} — {scene['location']}",
            expanded=True,
        ):
            tab1, tab2, tab3 = st.tabs(["Voice Clone", "Lip Sync", "Music"])

            with tab1:
                st.markdown("**`[STUB — VOICE CLONE INSTRUCTION]`**")
                st.code(voice_instruction, language=None)
                st.caption("STUB: Would be sent to ElevenLabs voice clone API. Output: `scene_{}_voice_STUB.mp3`".format(scene["scene_number"]))

            with tab2:
                st.markdown("**`[STUB — LIP SYNC MAPPING]`**")
                st.code(lip_sync, language=None)
                st.caption("STUB: Would be sent to Sync.so. Aligns mouth movement in `scene_{n}_STUB.mp4` to `scene_{n}_voice_STUB.mp3`.".replace("{n}", str(scene["scene_number"])))

            with tab3:
                st.markdown("**`[STUB — MUSIC SELECTION]`**")
                st.markdown(f"**Selected variant:** `{music_variant}`")
                st.code(music, language=None)
                st.caption("STUB: Music variant selected from licensed library based on mood and emotional beat. No audio file rendered.")

    save_stage_data(project_id, 6, "audio_plan", audio_plan)

    # ── DEPLOY-READY summary card ──────────────────────────────────────────────
    st.divider()
    st.subheader("DEPLOY-READY Summary")

    show_name = project.get("show_name", "Untitled")
    episode_number = load_stage_data(project_id, 2, "parse_source") and "EP01" or "EP01"

    st.markdown(
        f"""
<div style="border: 2px solid #00cc66; border-radius: 12px; padding: 24px; background: #0a1f14;">

### ✅ {show_name} — Episode 01

| Field | Value |
|---|---|
| Show | **{show_name}** |
| Episode | EP01 |
| Total Scenes | {len(approved_scenes)} |
| Estimated Runtime | {sum(5 for _ in approved_scenes)}s |
| Director Style | {project.get('director_style') or '—'} |
| Color Palette | {project.get('color_palette') or '—'} |
| Mood | {project.get('mood') or '—'} |
| Tone | {project.get('tone') or '—'} |

#### Pipeline Stages

| Stage | Status |
|---|---|
| 1. Director Memory | ✅ Complete |
| 2. Story Understanding | ✅ Complete |
| 3. Storyboard Automation | ✅ Complete |
| 4. Video Generation | ✅ STUB |
| 5. Auto Editing | ✅ STUB |
| 6. Audio + Lip Sync | ✅ STUB |

#### Output Artifacts (Stubbed)
{chr(10).join(f"- `scene_{s['scene_number']}_STUB.mp4` + `scene_{s['scene_number']}_voice_STUB.mp3`" for s in approved_scenes)}
- `episode_rough_cut_STUB.mp4`

</div>
""",
        unsafe_allow_html=True,
    )

    st.success(
        "All 6 stages complete. V1 PoC pipeline is DEPLOY-READY. "
        "Replace STUB steps with real API calls to go live."
    )

    st.caption("V1 PoC — Showrunner AI Micro-Drama Pipeline")
