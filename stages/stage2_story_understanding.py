from __future__ import annotations

import json
import os
import re
import anthropic
import streamlit as st
from dotenv import load_dotenv
from memory.database import save_stage_data, load_stage_data, get_project
from config.settings import SCRIPT_PARSE_PROMPT, EMOTIONAL_BEAT_MODEL

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


# ── Heuristic scene splitter ──────────────────────────────────────────────────

def _split_scenes(script_text: str) -> list[dict]:
    """
    Split script into scenes on INT./EXT. headers.
    Returns list of dicts with scene_number, location, characters, summary.
    emotional_beat is left empty — filled by Claude.
    """
    scenes = []
    current_lines = []
    current_header = None

    _location_words = {
        "INT", "EXT", "CUT", "FADE", "DAY", "NIGHT", "DAWN", "DUSK",
        "CONTINUOUS", "LATER", "ANGLE", "CLOSE", "WIDE", "SHOT", "BACK",
        "OVER", "MOMENTS",
    }

    for line in script_text.splitlines():
        stripped = line.strip()
        if re.match(r"^(INT\.|EXT\.|SCENE\s+\d+)", stripped, re.IGNORECASE):
            if current_lines and current_header is not None:
                scenes.append((current_header, "\n".join(current_lines)))
            current_header = stripped
            current_lines = [stripped]
        else:
            current_lines.append(stripped)

    if current_lines:
        header = current_header or "SCENE 1"
        scenes.append((header, "\n".join(current_lines)))

    if not scenes:
        scenes = [("FULL SCRIPT", script_text)]

    result = []
    for i, (header, body) in enumerate(scenes, start=1):
        caps = re.findall(r"\b[A-Z]{2,}\b", body)
        header_words = set(re.findall(r"\b[A-Z]{2,}\b", header))
        characters = list(dict.fromkeys([
            w for w in caps if w not in _location_words and w not in header_words
        ]))[:6]

        body_text = body.replace("\n", " ").strip()
        result.append({
            "scene_number": i,
            "location": header,
            "characters": characters if characters else ["UNKNOWN"],
            "emotional_beat": "",   # filled by Claude
            "summary": body_text[:150] + ("..." if len(body_text) > 150 else ""),
        })

    return result


# ── Claude API call ────────────────────────────────────────────────────────────

def _call_claude(script_text: str) -> list[dict] | None:
    """
    Send full script to Claude. Returns parsed scene list or None on failure.
    Claude is responsible for location, characters, emotional_beat, and summary.
    """
    prompt = SCRIPT_PARSE_PROMPT.format(script=script_text)
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=EMOTIONAL_BEAT_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()

    # Strip markdown fences if model adds them despite instructions
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)


def _parse_script(script_text: str) -> tuple[list[dict], str]:
    """
    Try Claude first. Fall back to heuristic splitter on any error.
    Returns (scenes, source) where source is 'claude' or 'heuristic'.
    """
    try:
        scenes = _call_claude(script_text)
        # Normalise: ensure scene_number is sequential
        for i, s in enumerate(scenes, start=1):
            s.setdefault("scene_number", i)
            s.setdefault("emotional_beat", "")
            s.setdefault("characters", [])
            s.setdefault("location", f"Scene {i}")
            s.setdefault("summary", "")
        return scenes, "claude"
    except Exception as e:
        st.warning(f"Claude API call failed ({e}). Falling back to heuristic parser.")
        return _split_scenes(script_text), "heuristic"


# ── Main render ───────────────────────────────────────────────────────────────

def render(state: dict):
    st.header("Stage 2 — Story Understanding")
    st.caption("Paste or upload your episode script. Claude extracts the structured scene breakdown.")

    project_id = state.get("project_id")
    if not project_id:
        st.warning("No active project. Go to Stage 1 first and create or load a project.")
        if st.button("← Go to Stage 1"):
            state["current_stage"] = 1
            st.rerun()
        return

    project = get_project(project_id)
    st.info(f"Active project: **{project['show_name']}** (ID {project_id})")

    # ── Script input ──────────────────────────────────────────────────────────
    st.subheader("1. Input Script")
    input_method = st.radio("Input method", ["Paste text", "Upload .txt file"], horizontal=True)

    script_text = ""

    if input_method == "Paste text":
        script_text = st.text_area(
            "Paste episode script here",
            height=300,
            placeholder="INT. APARTMENT - NIGHT\n\nARAV stands at the window...",
        )
    else:
        uploaded = st.file_uploader("Upload script (.txt)", type=["txt"])
        if uploaded:
            script_text = uploaded.read().decode("utf-8", errors="replace")
            st.success(f"Loaded: {uploaded.name} ({len(script_text):,} chars)")
            with st.expander("Preview uploaded script"):
                st.text(script_text[:1000] + ("..." if len(script_text) > 1000 else ""))

    # ── Extract button ────────────────────────────────────────────────────────
    st.subheader("2. Extract Scene Breakdown")

    col_run, col_clear = st.columns([2, 1])
    with col_run:
        if st.button("Extract Scene Breakdown →", type="primary", disabled=not script_text.strip()):
            with st.spinner("Calling Claude to parse script…"):
                scenes, source = _parse_script(script_text)
                save_stage_data(project_id, 2, "scene_breakdown", scenes)
                save_stage_data(project_id, 2, "raw_script", script_text)
                save_stage_data(project_id, 2, "parse_source", source)
                state["stage2_complete"] = True
            label = "Claude API" if source == "claude" else "heuristic fallback"
            st.success(f"Extracted {len(scenes)} scene(s) via {label}. Saved to project.")
            st.rerun()

    with col_clear:
        breakdown = load_stage_data(project_id, 2, "scene_breakdown")
        if breakdown and st.button("Clear & Re-extract"):
            save_stage_data(project_id, 2, "scene_breakdown", None)
            state["stage2_complete"] = False
            st.rerun()

    # ── Scene breakdown display ───────────────────────────────────────────────
    breakdown = load_stage_data(project_id, 2, "scene_breakdown")
    source = load_stage_data(project_id, 2, "parse_source", "unknown")

    if breakdown:
        st.divider()
        st.subheader("3. Scene Breakdown")

        # Block proceed if any emotional beat is missing
        missing_beats = [s for s in breakdown if not str(s.get("emotional_beat", "")).strip()]

        col_info, col_badge = st.columns([4, 1])
        with col_info:
            st.caption(f"{len(breakdown)} scene(s) — parsed via {source}")
        with col_badge:
            if missing_beats:
                st.error(f"{len(missing_beats)} beat(s) missing")
            else:
                st.success("All beats filled")

        for scene in breakdown:
            beat = str(scene.get("emotional_beat", "")).strip()
            beat_ok = bool(beat)
            label = f"Scene {scene['scene_number']} — {scene['location']}"
            if not beat_ok:
                label += "  ⚠️ beat missing"

            with st.expander(label, expanded=(len(breakdown) <= 6)):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Location**")
                    st.write(scene["location"])
                    st.markdown("**Emotional Beat**")
                    if beat_ok:
                        st.write(beat)
                    else:
                        st.error("Missing — re-extract or edit JSON below")
                with col2:
                    st.markdown("**Characters**")
                    st.write(", ".join(scene.get("characters", [])))
                    st.markdown("**Summary**")
                    st.write(scene.get("summary", ""))

        st.divider()

        with st.expander("Edit breakdown (JSON)"):
            edited_json = st.text_area(
                "Edit JSON directly — save before proceeding",
                value=json.dumps(breakdown, indent=2),
                height=300,
                key="json_editor",
            )
            if st.button("Save edits"):
                try:
                    parsed = json.loads(edited_json)
                    save_stage_data(project_id, 2, "scene_breakdown", parsed)
                    st.success("Saved.")
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {e}")

        # ── Proceed — gated on emotional beats ───────────────────────────────
        if missing_beats:
            st.warning(
                f"{len(missing_beats)} scene(s) still have no emotional beat. "
                "Re-extract or fill them in the JSON editor above before proceeding."
            )
        else:
            if st.button("Proceed to Stage 3 — Storyboard Automation →", type="primary"):
                state["current_stage"] = 3
                st.rerun()

    elif not script_text.strip():
        st.info("Paste or upload a script above, then click Extract.")
