# -*- coding: utf-8 -*-
"""灵云文创 · CRUD 封装（产品级）"""
import json
import sqlite3
from pathlib import Path


def get_conn(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")
    migrate_schema(conn)
    return conn


def migrate_schema(conn: sqlite3.Connection):
    """轻量 schema 迁移：旧项目 DB 打开时自动补齐缺失表/列（幂等）。"""
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(entities)").fetchall()}
        if cols and "archetype" not in cols:
            conn.execute("ALTER TABLE entities ADD COLUMN archetype TEXT DEFAULT 'npc'")
            conn.commit()
    except Exception:
        pass
    # 老项目缺 state_changes / relationships 表时自动补建（幂等）
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS state_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT, chapter INTEGER, change_type TEXT,
            old_value TEXT, new_value TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity1_id TEXT, entity2_id TEXT, relation_type TEXT,
            strength INTEGER DEFAULT 0, first_chapter INTEGER, last_chapter INTEGER)""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_state_changes_entity ON state_changes(entity_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_state_changes_chapter ON state_changes(chapter)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships ON relationships(entity1_id, entity2_id)")
        conn.commit()
    except Exception:
        pass


def init_db(db_path: str | Path):
    schema = Path(__file__).parent / "schema.sql"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema.read_text(encoding="utf-8"))
    # FTS5 全文索引（失败则回退 LIKE）
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chapters_fts USING fts5(chapter, title, content)")
    except Exception:
        pass
    conn.commit()
    conn.close()


# ===== progress =====
def get_progress(conn) -> dict:
    row = conn.execute("SELECT * FROM progress WHERE id=1").fetchone()
    if not row:
        conn.execute("INSERT INTO progress (id) VALUES (1)")
        conn.commit()
        return {"current_chapter": 0, "total_chapters": 100, "status": "idle", "current_step": "", "retry_count": 0, "last_error": ""}
    return dict(row)


def update_progress(conn, **kwargs):
    sets = ", ".join(f"{k}=?" for k in kwargs)
    conn.execute(f"UPDATE progress SET {sets} WHERE id=1", list(kwargs.values()))
    conn.commit()


# ===== chapters =====
def save_chapter(conn, chapter: int, title: str, content: str, summary: str = "", commit_json: str = ""):
    conn.execute("""
        INSERT OR REPLACE INTO chapters (chapter, title, content, summary, word_count, commit_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (chapter, title, content, summary, len(content), commit_json))
    # 同步 FTS
    try:
        conn.execute("DELETE FROM chapters_fts WHERE chapter=?", (chapter,))
        conn.execute("INSERT INTO chapters_fts (chapter, title, content) VALUES (?, ?, ?)",
                     (chapter, title, content))
    except Exception:
        pass
    conn.commit()


def get_chapter(conn, chapter: int) -> dict | None:
    row = conn.execute("SELECT * FROM chapters WHERE chapter=?", (chapter,)).fetchone()
    return dict(row) if row else None


def list_chapters(conn) -> list[dict]:
    rows = conn.execute("SELECT chapter, title, word_count, review_score FROM chapters ORDER BY chapter").fetchall()
    return [dict(r) for r in rows]


# ===== entities (人物) =====
def upsert_character(conn, data: dict):
    data = dict(data)
    data.setdefault("archetype", "npc")  # 兜底：旧调用方没带 archetype 时用默认
    conn.execute("""
        INSERT OR REPLACE INTO entities (id, name, aliases, role_type, realm, personality, abilities, state, first_chapter, last_chapter, notes, archetype)
        VALUES (:id, :name, :aliases, :role_type, :realm, :personality, :abilities, :state, :first_chapter, :last_chapter, :notes, :archetype)
    """, data)
    conn.commit()


def list_characters(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM entities ORDER BY role_type, name").fetchall()
    return [dict(r) for r in rows]


def get_character(conn, eid: str) -> dict | None:
    row = conn.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
    return dict(row) if row else None


# ===== state_changes (状态变化) =====
def add_state_change(conn, entity_id: str, chapter: int, change_type: str, old_value: str, new_value: str):
    conn.execute("""
        INSERT INTO state_changes (entity_id, chapter, change_type, old_value, new_value)
        VALUES (?, ?, ?, ?, ?)
    """, (entity_id, chapter, change_type, old_value, new_value))
    conn.commit()


def list_state_changes(conn, entity_id: str = None, chapter: int = None) -> list[dict]:
    q = "SELECT * FROM state_changes WHERE 1=1"
    params = []
    if entity_id:
        q += " AND entity_id=?"
        params.append(entity_id)
    if chapter:
        q += " AND chapter=?"
        params.append(chapter)
    q += " ORDER BY chapter DESC, id DESC"
    rows = conn.execute(q, params).fetchall()
    return [dict(r) for r in rows]


# ===== relationships (人物关系) =====
def add_relationship(conn, e1: str, e2: str, rtype: str, strength: int, chapter: int):
    conn.execute("""
        INSERT INTO relationships (entity1_id, entity2_id, relation_type, strength, first_chapter, last_chapter)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (e1, e2, rtype, strength, chapter, chapter))
    conn.commit()


def list_relationships(conn) -> list[dict]:
    rows = conn.execute("""
        SELECT r.*, e1.name as entity1_name, e2.name as entity2_name
        FROM relationships r
        JOIN entities e1 ON r.entity1_id = e1.id
        JOIN entities e2 ON r.entity2_id = e2.id
        ORDER BY r.strength DESC
    """).fetchall()
    return [dict(r) for r in rows]


# ===== foreshadow_contracts (伏笔契约) =====
def add_foreshadow(conn, data: dict) -> int:
    cur = conn.execute("""
        INSERT INTO foreshadow_contracts (plant_chapter, plant_summary, type, strength)
        VALUES (:plant_chapter, :plant_summary, :type, :strength)
    """, data)
    conn.commit()
    return cur.lastrowid


def resolve_foreshadow(conn, fid: int, chapter: int, summary: str):
    conn.execute("""
        UPDATE foreshadow_contracts
        SET resolve_chapter=?, resolve_summary=?, status='resolved'
        WHERE id=?
    """, (chapter, summary, fid))
    conn.commit()


def list_active_foreshadows(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM foreshadow_contracts WHERE status='active' ORDER BY plant_chapter").fetchall()
    return [dict(r) for r in rows]


def list_all_foreshadows(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM foreshadow_contracts ORDER BY plant_chapter").fetchall()
    return [dict(r) for r in rows]


# ===== events (关键事件) =====
def add_event(conn, chapter: int, etype: str, summary: str, importance: int = 5):
    conn.execute("""
        INSERT INTO events (chapter, event_type, summary, importance)
        VALUES (?, ?, ?, ?)
    """, (chapter, etype, summary, importance))
    conn.commit()


def list_events(conn, chapter: int = None) -> list[dict]:
    q = "SELECT * FROM events"
    params = []
    if chapter:
        q += " WHERE chapter=?"
        params.append(chapter)
    q += " ORDER BY chapter, importance DESC"
    rows = conn.execute(q, params).fetchall()
    return [dict(r) for r in rows]


# ===== logs =====
def add_log(conn, chapter: int = None, stage: str = "", status: str = "info", latency_ms: int = 0, error: str = ""):
    conn.execute("""
        INSERT INTO logs (chapter, stage, status, latency_ms, error)
        VALUES (?, ?, ?, ?, ?)
    """, (chapter, stage, status, latency_ms, error))
    conn.commit()


def list_logs(conn, limit: int = 50) -> list[dict]:
    rows = conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# ===== project_meta =====
def get_meta(conn) -> dict:
    rows = conn.execute("SELECT key, value FROM project_meta").fetchall()
    return {r["key"]: r["value"] for r in rows}


def update_meta(conn, **kwargs):
    for k, v in kwargs.items():
        conn.execute("INSERT OR REPLACE INTO project_meta (key, value) VALUES (?, ?)", (k, str(v)))
    conn.commit()


# ===== api_keys.json =====
KEYS_FILE = Path(__file__).parent.parent.parent / "api_keys.json"


def load_keys() -> dict:
    if KEYS_FILE.exists():
        return json.loads(KEYS_FILE.read_text(encoding="utf-8"))
    return {}


def save_keys(keys: dict):
    KEYS_FILE.write_text(json.dumps(keys, indent=2, ensure_ascii=False), encoding="utf-8")
