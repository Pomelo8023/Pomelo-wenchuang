# -*- coding: utf-8 -*-
"""补充测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.route import route, ACTIONS
from engine import checker, gates


class TestRoute:
    def test_empty(self): assert route({}) == "plan_arc"
    def test_no_draft(self): assert route({"has_arc_plan": True}) == "write_chapter"
    def test_no_review(self): assert route({"has_arc_plan": True, "has_current_draft": True}) == "review_chapter"
    def test_retry(self):
        s = {"has_arc_plan": True, "has_current_draft": True, "is_reviewed": True, "review_passed": False, "retry_count": 1}
        assert route(s) == "write_chapter"
    def test_max_retry(self):
        s = {"has_arc_plan": True, "has_current_draft": True, "is_reviewed": True, "review_passed": False, "retry_count": 2}
        assert route(s) == "wait_for_arbiter"
    def test_commit(self):
        s = {"has_arc_plan": True, "has_current_draft": True, "is_reviewed": True, "review_passed": True, "is_committed": False}
        assert route(s) == "commit_chapter"
    def test_next(self):
        s = {"has_arc_plan": True, "has_current_draft": True, "is_reviewed": True, "review_passed": True, "is_committed": True}
        assert route(s) == "next_chapter"
    def test_done(self): assert route({"is_completed": True}) == "complete"
    def test_actions(self): assert "write_chapter" in ACTIONS


class TestChecker:
    def test_short(self):
        issues = checker.deterministic_check("短" * 100)
        assert any("字数" in i["detail"] for i in issues)
    def test_long(self):
        issues = checker.deterministic_check("长" * 6000)
        assert any("字数" in i["detail"] for i in issues)
    def test_tone(self):
        issues = checker.deterministic_check("他瞳孔微缩。")
        assert len(issues) > 0


class TestGates:
    def test_todo(self):
        issues = gates.precommit_check("这是TODO待写内容", {})
        assert any("TODO" in i for i in issues)
    def test_short(self):
        issues = gates.precommit_check("短" * 100, {})
        assert any("字数" in i for i in issues)


class TestAPI:
    def test_delete(self):
        from fastapi.testclient import TestClient
        from main import app
        c = TestClient(app)
        c.post("/api/projects", json={"name": "test-del-xyz"})
        r = c.delete("/api/projects/test-del-xyz")
        assert r.status_code == 200
    def test_list(self):
        from fastapi.testclient import TestClient
        from main import app
        c = TestClient(app)
        r = c.get("/api/projects")
        assert r.status_code == 200
    def test_health(self):
        from fastapi.testclient import TestClient
        from main import app
        c = TestClient(app)
        r = c.get("/health")
        assert r.status_code == 200
