# -*- coding: utf-8 -*-
"""patrol 巡检纯逻辑测试（mock LLM）"""
import sys, os, json, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import patrol


def _make_db(chapters):
    """建内存 DB，chapters = [(ch, title, content)]"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE chapters (chapter INTEGER, title TEXT, content TEXT)")
    for c, t, ct in chapters:
        conn.execute("INSERT INTO chapters VALUES (?,?,?)", (c, t, ct))
    conn.commit()
    return conn


def test_patrol_too_few_chapters(monkeypatch):
    """只有1章时直接返回空，不调 LLM"""
    conn = _make_db([(1, "第一章", "内容" * 100)])
    called = [False]
    def fake_chat(*a, **kw):
        called[0] = True
        return '{"issues": []}'
    monkeypatch.setattr(patrol, "chat", fake_chat)
    result = patrol.patrol_recent(conn, up_to_chapter=1, lookback=10)
    assert result == []
    assert called[0] is False, "章数不足不应调 LLM"


def test_patrol_parses_issues(monkeypatch):
    """正常返回时解析 issues 数组"""
    conn = _make_db([
        (1, "第一章", "内容A" * 100),
        (2, "第二章", "内容B" * 100),
    ])
    llm_out = json.dumps({"issues": ["人物性格突变", "时间线错乱"]})
    monkeypatch.setattr(patrol, "chat", lambda *a, **kw: llm_out)
    result = patrol.patrol_recent(conn, up_to_chapter=2, lookback=10)
    assert len(result) == 2
    assert "人物性格突变" in result[0]


def test_patrol_bad_json_returns_empty(monkeypatch):
    """LLM 返回坏 JSON 时静默返回空"""
    conn = _make_db([
        (1, "第一章", "内容A" * 100),
        (2, "第二章", "内容B" * 100),
    ])
    monkeypatch.setattr(patrol, "chat", lambda *a, **kw: "这不是JSON")
    result = patrol.patrol_recent(conn, up_to_chapter=2, lookback=10)
    assert result == []


def test_patrol_codeblock_json(monkeypatch):
    """LLM 返回 ```json 包裹时也能解析"""
    conn = _make_db([
        (1, "第一章", "内容A" * 100),
        (2, "第二章", "内容B" * 100),
    ])
    monkeypatch.setattr(patrol, "chat", lambda *a, **kw: '```json\n{"issues": ["已死人物又出现"]}\n```')
    result = patrol.patrol_recent(conn, up_to_chapter=2, lookback=10)
    assert len(result) == 1
