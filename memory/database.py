import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "showrunner.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            show_name TEXT NOT NULL,
            director_style TEXT,
            visual_references TEXT,
            tone TEXT,
            color_palette TEXT,
            mood TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS stage_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            stage INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project_id, stage, key)
        );
    """)
    conn.commit()
    conn.close()


# ── Projects ──────────────────────────────────────────────────────────────────

def save_project(show_name, director_style, visual_references, tone, color_palette, mood):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO projects (show_name, director_style, visual_references, tone, color_palette, mood)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (show_name, director_style, visual_references, tone, color_palette, mood))
    project_id = c.lastrowid
    conn.commit()
    conn.close()
    return project_id


def list_projects():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_project(project_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Stage data (JSON blobs keyed by stage + key) ──────────────────────────────

def save_stage_data(project_id, stage, key, value):
    conn = get_connection()
    conn.execute("""
        INSERT INTO stage_data (project_id, stage, key, value)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(project_id, stage, key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
    """, (project_id, stage, key, json.dumps(value)))
    conn.commit()
    conn.close()


def load_stage_data(project_id, stage, key, default=None):
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM stage_data WHERE project_id=? AND stage=? AND key=?",
        (project_id, stage, key)
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row["value"])
    return default


def completed_stages(project_id):
    """Return set of stage numbers that have at least one saved record."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT stage FROM stage_data WHERE project_id=?", (project_id,)
    ).fetchall()
    conn.close()
    return {r["stage"] for r in rows}
