import streamlit as st
from memory.database import save_project, list_projects, get_project


def render(state: dict):
    st.header("Stage 1 — Director Memory")
    st.caption("Define the cinematic grammar for this project. Everything downstream inherits from this record.")

    # ── Project selector ───────────────────────────────────────────────────────
    projects = list_projects()
    project_options = {f"[{p['id']}] {p['show_name']}": p["id"] for p in projects}

    col_new, col_load = st.columns([1, 1])

    with col_new:
        st.subheader("New Project")
        with st.form("stage1_form"):
            show_name = st.text_input("Show Name *", placeholder="e.g. Neon Dharma")
            director_style = st.text_area(
                "Director Style Notes",
                placeholder="e.g. Mira Nair meets Blade Runner — intimate faces, neon-drenched environments",
                height=100,
            )
            visual_references = st.text_area(
                "Visual References",
                placeholder="e.g. Parasite (2019), Mindhunter (Netflix), Euphoria color grading",
                height=80,
            )
            tone = st.text_input("Tone", placeholder="e.g. Tense, melancholic, darkly comic")
            color_palette = st.text_input(
                "Color Palette", placeholder="e.g. Deep teals, amber highlights, desaturated skin tones"
            )
            mood = st.text_input("Mood", placeholder="e.g. Claustrophobic dread with moments of fragile hope")

            submitted = st.form_submit_button("Save Project →", type="primary")

        if submitted:
            if not show_name.strip():
                st.error("Show Name is required.")
            else:
                project_id = save_project(
                    show_name.strip(),
                    director_style.strip(),
                    visual_references.strip(),
                    tone.strip(),
                    color_palette.strip(),
                    mood.strip(),
                )
                state["project_id"] = project_id
                state["stage1_complete"] = True
                st.success(f"Project saved — ID {project_id}")
                st.rerun()

    with col_load:
        st.subheader("Load Existing Project")
        if project_options:
            selected_label = st.selectbox("Select project", list(project_options.keys()))
            if st.button("Load →"):
                state["project_id"] = project_options[selected_label]
                state["stage1_complete"] = True
                st.rerun()
        else:
            st.info("No projects yet. Create one on the left.")

    # ── Active project display ─────────────────────────────────────────────────
    if state.get("project_id"):
        project = get_project(state["project_id"])
        if project:
            st.divider()
            st.subheader("Active Project")
            cols = st.columns(2)
            cols[0].metric("Show", project["show_name"])
            cols[0].write(f"**Tone:** {project['tone'] or '—'}")
            cols[0].write(f"**Mood:** {project['mood'] or '—'}")
            cols[1].write(f"**Director Style:** {project['director_style'] or '—'}")
            cols[1].write(f"**Visual Refs:** {project['visual_references'] or '—'}")
            cols[1].write(f"**Color Palette:** {project['color_palette'] or '—'}")

            st.divider()
            if st.button("Proceed to Stage 2 →", type="primary"):
                state["current_stage"] = 2
                st.rerun()
