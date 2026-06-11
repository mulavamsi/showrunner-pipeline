from __future__ import annotations

import streamlit as st
from memory.database import save_stage_data, load_stage_data, get_project

TRANSITION_CYCLE = ["hard cut", "smash cut", "dissolve"]

DURATION_MAP = {
    "close-up": 4,
    "medium close-up": 5,
    "medium": 5,
    "wide": 6,
    "extreme wide": 7,
    "over-the-shoulder": 4,
    "two-shot": 5,
    "insert": 3,
    "pov": 4,
}


def _estimate_duration(shot_type: str) -> int:
    return DURATION_MAP.get(shot_type.lower().strip(), 5)


def _build_cut_list(breakdown: list[dict], storyboard: dict) -> list[dict]:
    cuts = []
    for i, scene in enumerate(breakdown):
        key = str(scene["scene_number"])
        shot = storyboard.get(key, {})
        shot_type = shot.get("shot_type", "medium")
        duration = _estimate_duration(shot_type)
        transition = TRANSITION_CYCLE[i % len(TRANSITION_CYCLE)] if i < len(breakdown) - 1 else "—"
        cuts.append({
            "scene_number": scene["scene_number"],
            "location": scene["location"],
            "clip_file": f"scene_{scene['scene_number']}_STUB.mp4",
            "shot_type": shot_type,
            "duration_sec": duration,
            "transition_to_next": transition,
            "emotional_beat": scene.get("emotional_beat", ""),
        })
    return cuts


def render(state: dict):
    st.header("Stage 5 — Auto Editing")
    st.caption(
        "Assembles a rough cut order from the approved scene clips. "
        "Duration and transitions are estimated — no video file is produced."
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

    approved_scenes = [s for s in breakdown if approvals.get(str(s["scene_number"]))]
    if not approved_scenes:
        st.error("No approved scenes. Return to Stage 3 and approve scenes first.")
        if st.button("← Go to Stage 3"):
            state["current_stage"] = 3
            st.rerun()
        return

    st.info(
        f"Active project: **{project['show_name']}** — "
        f"assembling {len(approved_scenes)} approved clip(s)"
    )

    # ── Build and persist cut list ─────────────────────────────────────────────
    cut_list = _build_cut_list(approved_scenes, storyboard)
    save_stage_data(project_id, 5, "cut_list", cut_list)

    total_duration = sum(c["duration_sec"] for c in cut_list)

    # ── Summary stats ──────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Scenes", len(cut_list))
    col2.metric("Estimated Runtime", f"{total_duration}s")
    col3.metric("Output File", "episode_rough_cut_STUB.mp4")

    st.divider()
    st.subheader("Rough Cut Assembly List")
    st.caption("STUB — no video rendering occurs. Clip order, durations, and transitions are estimates.")

    # ── Timeline table ─────────────────────────────────────────────────────────
    for i, cut in enumerate(cut_list):
        is_last = i == len(cut_list) - 1

        with st.container():
            cols = st.columns([1, 4, 2, 2, 2])
            cols[0].markdown(f"**#{cut['scene_number']}**")
            cols[1].markdown(f"`{cut['clip_file']}`  \n*{cut['location']}*")
            cols[2].markdown(f"Shot: `{cut['shot_type']}`")
            cols[3].markdown(f"Duration: **{cut['duration_sec']}s**")
            if is_last:
                cols[4].markdown("*(end)*")
            else:
                cols[4].markdown(f"↓ `{cut['transition_to_next']}`")

        st.caption(f"Emotional register: *{cut['emotional_beat']}*")
        if not is_last:
            st.markdown("---")

    # ── Editing notes ──────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Editing Notes")
    st.markdown(f"""
| Field | Value |
|---|---|
| Cut style | {project.get('director_style') or 'Not specified'} |
| Mood target | {project.get('mood') or 'Not specified'} |
| Tone | {project.get('tone') or 'Not specified'} |
| Total runtime | {total_duration} seconds |
| Assembly file | `episode_rough_cut_STUB.mp4` |
""")
    st.caption("STUB: This assembly list would be passed to an NLE (DaVinci Resolve / Premiere) or programmatic editor (MoviePy). No render has occurred.")

    # ── Proceed ────────────────────────────────────────────────────────────────
    st.divider()
    st.success(f"Rough cut assembled — {len(cut_list)} scene(s), {total_duration}s estimated runtime. Ready for Stage 6.")
    if st.button("Proceed to Stage 6 — Audio + Lip Sync →", type="primary"):
        state["current_stage"] = 6
        st.rerun()
