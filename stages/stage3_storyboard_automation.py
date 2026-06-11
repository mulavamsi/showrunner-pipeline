from __future__ import annotations

import json
import os
import re
import anthropic
import streamlit as st
from dotenv import load_dotenv
from memory.database import save_stage_data, load_stage_data, get_project
from config.settings import STORYBOARD_PROMPT, STORYBOARD_MODEL

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


# ── Claude call (per scene) ────────────────────────────────────────────────────

def _parse_shot_response(raw: str) -> dict:
    """Parse Claude's response, falling back to regex extraction if JSON is truncated."""
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            parsed = parsed[0]
        return parsed
    except json.JSONDecodeError:
        def _extract(field: str) -> str:
            m = re.search(rf'"{field}"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
            return m.group(1) if m else ""

        return {
            "shot_type": _extract("shot_type"),
            "camera_angle": _extract("camera_angle"),
            "framing_notes": _extract("framing_notes"),
            "visual_description": _extract("visual_description"),
        }


def _generate_shot(scene: dict, project: dict) -> dict:
    prompt = STORYBOARD_PROMPT.format(
        director_style=project.get("director_style") or "Not specified",
        visual_references=project.get("visual_references") or "Not specified",
        color_palette=project.get("color_palette") or "Not specified",
        tone=project.get("tone") or "Not specified",
        mood=project.get("mood") or "Not specified",
        scene_number=scene["scene_number"],
        location=scene["location"],
        characters=", ".join(scene.get("characters", [])),
        emotional_beat=scene.get("emotional_beat", ""),
        summary=scene.get("summary", ""),
    )

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=STORYBOARD_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    return _parse_shot_response(raw)


# ── Main render ───────────────────────────────────────────────────────────────

def render(state: dict):
    st.header("Stage 3 — Storyboard Automation")
    st.caption(
        "Claude generates shot type, camera angle, framing, and visual description "
        "for each scene — informed by the director's style and each scene's emotional beat."
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

    if not breakdown:
        st.warning("No scene breakdown found. Complete Stage 2 first.")
        if st.button("← Go to Stage 2"):
            state["current_stage"] = 2
            st.rerun()
        return

    st.info(f"Active project: **{project['show_name']}** — {len(breakdown)} scene(s) from Stage 2")

    # ── Director context summary ───────────────────────────────────────────────
    with st.expander("Director grammar being used in this storyboard"):
        c1, c2 = st.columns(2)
        c1.markdown(f"**Style:** {project.get('director_style') or '—'}")
        c1.markdown(f"**Tone:** {project.get('tone') or '—'}")
        c1.markdown(f"**Mood:** {project.get('mood') or '—'}")
        c2.markdown(f"**Visual Refs:** {project.get('visual_references') or '—'}")
        c2.markdown(f"**Color Palette:** {project.get('color_palette') or '—'}")

    # ── Load existing storyboard + approvals ───────────────────────────────────
    storyboard = load_stage_data(project_id, 3, "storyboard") or {}
    approvals = load_stage_data(project_id, 3, "approvals") or {}

    # ── Generate all / regenerate controls ────────────────────────────────────
    st.subheader("Generate Storyboard")
    col_gen, col_regen = st.columns([2, 1])

    with col_gen:
        if st.button("Generate All Scenes →", type="primary", disabled=bool(storyboard)):
            progress = st.progress(0, text="Calling Claude…")
            errors = []
            for i, scene in enumerate(breakdown):
                key = str(scene["scene_number"])
                try:
                    shot = _generate_shot(scene, project)
                    storyboard[key] = shot
                except Exception as e:
                    errors.append(f"Scene {scene['scene_number']}: {e}")
                    storyboard[key] = {"error": str(e)}
                progress.progress((i + 1) / len(breakdown), text=f"Scene {scene['scene_number']} done")

            save_stage_data(project_id, 3, "storyboard", storyboard)
            progress.empty()
            if errors:
                st.warning(f"Completed with {len(errors)} error(s): {'; '.join(errors)}")
            else:
                st.success(f"Storyboard generated for {len(breakdown)} scene(s).")
            st.rerun()

    with col_regen:
        if storyboard and st.button("Clear & Regenerate"):
            save_stage_data(project_id, 3, "storyboard", {})
            save_stage_data(project_id, 3, "approvals", {})
            st.rerun()

    # ── Scene-by-scene display + approval ─────────────────────────────────────
    if storyboard:
        st.divider()
        st.subheader("Review & Approve")

        approved_count = sum(1 for s in breakdown if approvals.get(str(s["scene_number"])))
        total = len(breakdown)

        st.caption(f"{approved_count} of {total} scene(s) approved")
        st.progress(approved_count / total if total else 0)

        for scene in breakdown:
            key = str(scene["scene_number"])
            shot = storyboard.get(key, {})
            is_approved = approvals.get(key, False)

            border_color = "✅" if is_approved else "⬜"
            with st.expander(
                f"{border_color} Scene {scene['scene_number']} — {scene['location']}",
                expanded=not is_approved,
            ):
                if "error" in shot:
                    st.error(f"Generation failed: {shot['error']}")
                    if st.button(f"Retry scene {scene['scene_number']}", key=f"retry_{key}"):
                        try:
                            shot = _generate_shot(scene, project)
                            storyboard[key] = shot
                            save_stage_data(project_id, 3, "storyboard", storyboard)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                    continue

                # Storyboard fields
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Shot Type**")
                    st.write(shot.get("shot_type", "—"))
                    st.markdown("**Camera Angle**")
                    st.write(shot.get("camera_angle", "—"))
                with col2:
                    st.markdown("**Framing Notes**")
                    st.write(shot.get("framing_notes", "—"))

                st.markdown("**Visual Description**")
                st.info(shot.get("visual_description", "—"))

                # Emotional beat reminder
                st.caption(f"Emotional beat from Stage 2: *{scene.get('emotional_beat', '—')}*")

                # Per-scene regenerate
                if st.button(f"Regenerate this scene", key=f"regen_{key}"):
                    with st.spinner("Calling Claude…"):
                        try:
                            shot = _generate_shot(scene, project)
                            storyboard[key] = shot
                            approvals[key] = False
                            save_stage_data(project_id, 3, "storyboard", storyboard)
                            save_stage_data(project_id, 3, "approvals", approvals)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                # Approval checkbox
                new_approval = st.checkbox(
                    "Approve this scene",
                    value=is_approved,
                    key=f"approve_{key}",
                )
                if new_approval != is_approved:
                    approvals[key] = new_approval
                    save_stage_data(project_id, 3, "approvals", approvals)
                    st.rerun()

        # ── Proceed gate ───────────────────────────────────────────────────────
        st.divider()
        all_approved = approved_count == total and total > 0
        unapproved = [
            f"Scene {s['scene_number']}" for s in breakdown
            if not approvals.get(str(s["scene_number"]))
        ]

        if not all_approved:
            st.warning(
                f"Approve all scenes before proceeding. Pending: {', '.join(unapproved)}"
            )
        else:
            st.success("All scenes approved. Ready for Stage 4.")
            if st.button("Proceed to Stage 4 — Video Generation →", type="primary"):
                state["current_stage"] = 4
                st.rerun()

    elif not storyboard and breakdown:
        st.info("Click 'Generate All Scenes' to call Claude for each scene.")
