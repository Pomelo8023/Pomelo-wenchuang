# -*- coding: utf-8 -*-
"""story_bible 测试（mock LLM）"""
import sys, os, json, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import story_bible


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE relationships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity1_id TEXT, entity2_id TEXT, relation_type TEXT,
        strength INTEGER DEFAULT 0, first_chapter INTEGER, last_chapter INTEGER)""")
    conn.commit()
    return conn


def test_story_bible_merges_facts(monkeypatch):
    conn = _make_db()
    canon = {"story_bible": {"facts": []}}
    llm_out = json.dumps({
        "new_facts": ["新地点：黑风寨", "新物品：玄铁剑"],
        "relations": [{"e1": "林凡", "e2": "苏月", "type": "ally", "strength": 20}],
        "world_note": "主角抵达边境"
    })
    monkeypatch.setattr(story_bible, "chat", lambda *a, **kw: llm_out)
    r = story_bible.update_story_bible(conn, canon, "test", 1, "第一章", "正文", {"characters": []})
    assert r["facts_added"] == 2
    assert r["relations_added"] == 1
    assert len(canon["story_bible"]["facts"]) == 2
    assert canon["story_bible"]["world_state"] == "主角抵达边境"


def test_story_bible_upsert_relation(monkeypatch):
    """已有关系更新 strength，不重复插入"""
    conn = _make_db()
    conn.execute("INSERT INTO relationships (entity1_id, entity2_id, relation_type, strength, first_chapter, last_chapter) VALUES ('林凡','苏月','ally',10,1,1)")
    conn.commit()
    canon = {}
    llm_out = json.dumps({
        "new_facts": [],
        "relations": [{"e1": "林凡", "e2": "苏月", "type": "ally", "strength": 50}]
    })
    monkeypatch.setattr(story_bible, "chat", lambda *a, **kw: llm_out)
    story_bible.update_story_bible(conn, canon, "test", 2, "第二章", "正文", {})
    rows = conn.execute("SELECT * FROM relationships WHERE entity1_id='林凡'").fetchall()
    assert len(rows) == 1, "不应重复插入"
    assert rows[0]["strength"] == 50
    assert rows[0]["last_chapter"] == 2


def test_story_bible_bad_json_silent(monkeypatch):
    conn = _make_db()
    canon = {}
    monkeypatch.setattr(story_bible, "chat", lambda *a, **kw: "坏JSON")
    r = story_bible.update_story_bible(conn, canon, "test", 1, "第一章", "正文", {})
    assert r["facts_added"] == 0
    assert "error" in r


def test_story_bible_skips_empty_relation(monkeypatch):
    """关系缺字段时跳过，不崩"""
    conn = _make_db()
    canon = {}
    llm_out = json.dumps({
        "new_facts": ["某事实"],
        "relations": [{"e1": "", "e2": "苏月", "type": "ally", "strength": 10}]
    })
    monkeypatch.setattr(story_bible, "chat", lambda *a, **kw: llm_out)
    r = story_bible.update_story_bible(conn, canon, "test", 1, "第一章", "正文", {})
    assert r["relations_added"] == 0
    assert r["facts_added"] == 1
