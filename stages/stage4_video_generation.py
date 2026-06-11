from __future__ import annotations

import streamlit as st
from memory.database import save_stage_data, load_stage_data, get_project
from config.settings import VIDEO_GEN_PROMPT_TEMPLATE


def _build_prompt(scene: dict, shot: dict, project: dict) -> str:
    return VIDEO_GEN_PROMPT_TEMPLATE.format(
        visual_description=shot.get("visual_description", "").strip(),
        shot_type=shot.get("shot_type", "").strip(),
        camera_angle=shot.get("camera_angle", "").strip(),
        framing_notes=shot.get("framing_notes", "").strip(),
        color_palette=project.get("color_palette") or "not specified",
        mood=project.get("mood") or "not specified",
        tone=project.get("tone") or "not specified",
        director_style=project.get("director_style") or "not specified",
        emotional_beat=scene.get("emotional_beat", "").strip(),
    )


def render(state: dict):
    st.header("Stage 4 — Video Generation")
    st.caption(
        "Displays the full video generation prompt for each approved scene. "
        "No API call is made — prompts are printed and labeled STUB."
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
    storyboard = load_stage_data(project_id, 3, "storyboard") or {}
    approvals = load_stage_data(project_id, 3, "approvals") or {}

    if not breakdown:
        st.warning("No scene breakdown found. Complete Stage 2 first.")
        if st.button("← Go to Stage 2"):
            state["current_stage"] = 2
            st.rerun()
        return

    if not storyboard:
        st.warning("No storyboard found. Complete Stage 3 first.")
        if st.button("← Go to Stage 3"):
            state["current_stage"] = 3
            st.rerun()
        return

    # ── Approval gate check ────────────────────────────────────────────────────
    approved_scenes = [
        s for s in breakdown if approvals.get(str(s["scene_number"]))
    ]
    unapproved = [
        s for s in breakdown if not approvals.get(str(s["scene_number"]))
    ]

    st.info(f"Active project: **{project['show_name']}** — {len(approved_scenes)} of {len(breakdown)} scene(s) approved in Stage 3")

    if unapproved:
        st.warning(
            f"{len(unapproved)} scene(s) not yet approved in Stage 3: "
            + ", ".join(f"Scene {s['scene_number']}" for s in unapproved)
            + ". Showing prompts for approved scenes only."
        )

    if not approved_scenes:
        st.error("No approved scenes. Return to Stage 3 and approve at least one scene.")
        if st.button("← Go to Stage 3"):
            state["current_stage"] = 3
            st.rerun()
        return

    # ── Build and save prompts ─────────────────────────────────────────────────
    prompts = load_stage_data(project_id, 4, "video_prompts") or {}

    # Regenerate prompts for all approved scenes (cheap, no API call)
    for scene in approved_scenes:
        key = str(scene["scene_number"])
        shot = storyboard.get(key, {})
        prompts[key] = _build_prompt(scene, shot, project)

    save_stage_data(project_id, 4, "video_prompts", prompts)

    # ── Display prompts scene by scene ─────────────────────────────────────────
    st.divider()
    st.subheader(f"Video Generation Prompts — {len(approved_scenes)} Scene(s)")

    for scene in approved_scenes:
        key = str(scene["scene_number"])
        shot = storyboard.get(key, {})
        prompt_text = prompts.get(key, "")

        with st.expander(
            f"Scene {scene['scene_number']} — {scene['location']}",
            expanded=True,
        ):
            # Source fields summary
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**From Stage 3 (Storyboard)**")
                st.write(f"Shot type: `{shot.get('shot_type', '—')}`")
                st.write(f"Camera angle: `{shot.get('camera_angle', '—')}`")
                st.write(f"Framing: {shot.get('framing_notes', '—')}")
            with col2:
                st.markdown("**From Stages 1 & 2**")
                st.write(f"Emotional beat: *{scene.get('emotional_beat', '—')}*")
                st.write(f"Director style: {project.get('director_style') or '—'}")
                st.write(f"Palette / Mood: {project.get('color_palette') or '—'} / {project.get('mood') or '—'}")

            st.markdown("---")

            # The STUB prompt
            st.markdown("**`[STUB — VIDEO GENERATION PROMPT]`**")
            st.code(prompt_text, language=None)

            st.caption(
                f"⚠️ STUB: This prompt would be sent to Runway Gen-3 / Kling 1.5. "
                f"No video clip has been generated. Output: `scene_{scene['scene_number']}_STUB.mp4`"
            )

    # ── Proceed ────────────────────────────────────────────────────────────────
    st.divider()
    st.success(f"All {len(approved_scenes)} prompt(s) generated. Ready for Stage 5.")
    if st.button("Proceed to Stage 5 — Auto Editing →", type="primary"):
        state["current_stage"] = 5
        st.rerun()
