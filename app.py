import streamlit as st
from memory.database import init_db, completed_stages

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Showrunner Pipeline",
    page_icon="🎬",
    layout="wide",
)

# ── DB init ───────────────────────────────────────────────────────────────────
init_db()

# ── Session state defaults ────────────────────────────────────────────────────
if "current_stage" not in st.session_state:
    st.session_state["current_stage"] = 1
if "project_id" not in st.session_state:
    st.session_state["project_id"] = None
if "stage1_complete" not in st.session_state:
    st.session_state["stage1_complete"] = False

state = st.session_state

# ── Stage metadata ────────────────────────────────────────────────────────────
STAGES = [
    (1, "Director Memory"),
    (2, "Story Understanding"),
    (3, "Storyboard Automation"),
    (4, "Video Generation"),
    (5, "Auto Editing"),
    (6, "Audio + Lip Sync"),
]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎬 Showrunner")
    st.caption("AI Micro-Drama Pipeline — V1 PoC")
    st.divider()

    if state["project_id"]:
        done = completed_stages(state["project_id"])
        # Stage 1 always counts as done once a project is loaded
        done = done | {1}
    else:
        done = set()

    for num, label in STAGES:
        is_current = num == state["current_stage"]
        is_done = num in done

        if is_done:
            icon = "✅"
        elif is_current:
            icon = "▶️"
        else:
            icon = "⬜"

        button_label = f"{icon} {num}. {label}"
        button_type = "primary" if is_current else "secondary"

        if st.button(button_label, key=f"nav_{num}", use_container_width=True, type=button_type):
            state["current_stage"] = num
            st.rerun()

    st.divider()
    st.caption(f"Active project ID: {state['project_id'] or '—'}")

# ── Progress bar ──────────────────────────────────────────────────────────────
progress_val = (state["current_stage"] - 1) / (len(STAGES) - 1) if len(STAGES) > 1 else 0
st.progress(progress_val, text=f"Stage {state['current_stage']} of {len(STAGES)}")

# ── Stage routing ─────────────────────────────────────────────────────────────
from stages import (
    stage1_director_memory,
    stage2_story_understanding,
    stage3_storyboard_automation,
    stage4_video_generation,
    stage5_auto_editing,
    stage6_audio_lipsync,
)

stage_map = {
    1: stage1_director_memory.render,
    2: stage2_story_understanding.render,
    3: stage3_storyboard_automation.render,
    4: stage4_video_generation.render,
    5: stage5_auto_editing.render,
    6: stage6_audio_lipsync.render,
}

stage_map[state["current_stage"]](state)
