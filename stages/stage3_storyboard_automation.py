from __future__ import annotations

import json
import os
import re
import anthropic
import fal_client
import streamlit as st
from dotenv import load_dotenv
from memory.database import save_stage_data, load_stage_data, get_project
from config.settings import (
    STORYBOARD_PROMPT, STORYBOARD_MODEL,
    IMAGE_GEN_MODEL, IMAGE_GEN_PROMPT_TEMPLATE,
)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Fal.ai picks up FAL_KEY from environment automatically
_fal_key = (
    st.secrets.get("FAL_KEY", "")
    if hasattr(st, "secrets")
    else os.environ.get("FAL_KEY", "")
)
if _fal_key:
    os.environ["FAL_KEY"] = _fal_key


# ── Claude storyboard call ────────────────────────────────────────────────────

def _parse_shot_response(raw: str) -> dict:
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
    return _parse_shot_response(msg.content[0].text.strip())


# ── Fal.ai image generation ───────────────────────────────────────────────────

def _build_image_prompt(shot: dict, project: dict) -> str:
    return IMAGE_GEN_PROMPT_TEMPLATE.format(
        visual_description=shot.get("visual_description", "").strip(),
        shot_type=shot.get("shot_type", "medium").strip(),
        camera_angle=shot.get("camera_angle", "eye-level").strip(),
        framing_notes=shot.get("framing_notes", "").strip(),
        color_palette=project.get("color_palette") or "natural",
        mood=project.get("mood") or "neutral",
        director_style=project.get("director_style") or "cinematic",
    )


def _generate_image(shot: dict, project: dict) -> str:
    """Call Fal.ai Flux and return the image URL."""
    image_prompt = _build_image_prompt(shot, project)
    result = fal_client.subscribe(
        IMAGE_GEN_MODEL,
        arguments={
            "prompt": image_prompt,
            "image_size": "landscape_16_9",
            "num_inference_steps": 4,
            "num_images": 1,
            "enable_safety_checker": True,
        },
    )
    return result["images"][0]["url"], image_prompt


# ── Main render ───────────────────────────────────────────────────────────────

def render(state: dict):
    st.header("Stage 3 — Storyboard Automation")
    st.caption(
        "Claude generates shot type, camera angle, framing, and visual description "
        "for each scene. Generate a reference image per scene using Fal.ai / Flux."
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

    # ── Director context ───────────────────────────────────────────────────────
    with st.expander("Director grammar being used in this storyboard"):
        c1, c2 = st.columns(2)
        c1.markdown(f"**Style:** {project.get('director_style') or '—'}")
        c1.markdown(f"**Tone:** {project.get('tone') or '—'}")
        c1.markdown(f"**Mood:** {project.get('mood') or '—'}")
        c2.markdown(f"**Visual Refs:** {project.get('visual_references') or '—'}")
        c2.markdown(f"**Color Palette:** {project.get('color_palette') or '—'}")

    # ── Load persisted data ────────────────────────────────────────────────────
    storyboard = load_stage_data(project_id, 3, "storyboard") or {}
    approvals = load_stage_data(project_id, 3, "approvals") or {}
    images = load_stage_data(project_id, 3, "images") or {}  # {scene_key: {url, prompt}}

    # ── Generate all / clear controls ─────────────────────────────────────────
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
            save_stage_data(project_id, 3, "images", {})
            st.rerun()

    # ── Scene-by-scene display ─────────────────────────────────────────────────
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
            scene_image = images.get(key)

            icon = "✅" if is_approved else "⬜"
            with st.expander(
                f"{icon} Scene {scene['scene_number']} — {scene['location']}",
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

                # ── Storyboard fields ──────────────────────────────────────────
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
                edited_vd = st.text_area(
                    "Edit visual description",
                    value=shot.get("visual_description", ""),
                    height=90,
                    key=f"vd_{key}",
                    label_visibility="collapsed",
                )
                if edited_vd != shot.get("visual_description", ""):
                    storyboard[key]["visual_description"] = edited_vd
                    images.pop(key, None)  # clear cached image — description changed
                    save_stage_data(project_id, 3, "storyboard", storyboard)
                    save_stage_data(project_id, 3, "images", images)
                st.caption(f"Emotional beat from Stage 2: *{scene.get('emotional_beat', '—')}*")

                # ── Image generation ───────────────────────────────────────────
                st.markdown("---")

                if scene_image:
                    st.image(
                        scene_image["url"],
                        caption=f"Generated with Flux — Scene {scene['scene_number']}",
                        use_container_width=True,
                    )
                    with st.expander("View image prompt"):
                        st.code(scene_image["prompt"], language=None)
                    img_col1, img_col2 = st.columns(2)
                    with img_col1:
                        if st.button("Regenerate Image", key=f"regen_img_{key}"):
                            with st.spinner("Calling Fal.ai / Flux…"):
                                try:
                                    url, prompt = _generate_image(shot, project)
                                    images[key] = {"url": url, "prompt": prompt}
                                    save_stage_data(project_id, 3, "images", images)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Image generation failed: {e}")
                else:
                    fal_available = bool(os.environ.get("FAL_KEY"))
                    if fal_available:
                        if st.button("Generate Image ✦", key=f"gen_img_{key}", type="primary"):
                            with st.spinner("Calling Fal.ai / Flux… (~5-10s)"):
                                try:
                                    url, prompt = _generate_image(shot, project)
                                    images[key] = {"url": url, "prompt": prompt}
                                    save_stage_data(project_id, 3, "images", images)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Image generation failed: {e}")
                    else:
                        st.caption("⚠️ FAL_KEY not set — add it to .env or Streamlit secrets to enable image generation.")

                # ── Per-scene storyboard regenerate ───────────────────────────
                if st.button("Regenerate Storyboard", key=f"regen_{key}"):
                    with st.spinner("Calling Claude…"):
                        try:
                            shot = _generate_shot(scene, project)
                            storyboard[key] = shot
                            approvals[key] = False
                            images.pop(key, None)
                            save_stage_data(project_id, 3, "storyboard", storyboard)
                            save_stage_data(project_id, 3, "approvals", approvals)
                            save_stage_data(project_id, 3, "images", images)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                # ── Approval checkbox ──────────────────────────────────────────
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
            st.warning(f"Approve all scenes before proceeding. Pending: {', '.join(unapproved)}")
        else:
            st.success("All scenes approved. Ready for Stage 4.")
            if st.button("Proceed to Stage 4 — Video Generation →", type="primary"):
                state["current_stage"] = 4
                st.rerun()

    elif not storyboard and breakdown:
        st.info("Click 'Generate All Scenes' to call Claude for each scene.")
