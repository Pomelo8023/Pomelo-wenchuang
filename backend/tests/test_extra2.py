# -*- coding: utf-8 -*-
"""补充测试2"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.route import route, ACTIONS
from engine import checker, gates
from fastapi.testclient import TestClient
from main import app
c = TestClient(app)


class TestRouteMore:
    def test_plan_arc(self): assert route({}) == "plan_arc"
    def test_no_plan(self): assert route({"has_arc_plan": False}) == "plan_arc"
    def test_draft_no_review(self):
        s = {"has_arc_plan": True, "has_current_draft": True, "is_reviewed": False}
        assert route(s) == "review_chapter"
    def test_review_pass_no_commit(self):
        s = {"has_arc_plan": True, "has_current_draft": True, "is_reviewed": True, "review_passed": True, "is_committed": False}
        assert route(s) == "commit_chapter"
    def test_review_pass_committed(self):
        s = {"has_arc_plan": True, "has_current_draft": True, "is_reviewed": True, "review_passed": True, "is_committed": True}
        assert route(s) == "next_chapter"
    def test_actions_keys(self):
        assert "plan_arc" in ACTIONS
        assert "write_chapter" in ACTIONS
        assert "review_chapter" in ACTIONS
        assert "commit_chapter" in ACTIONS
        assert "next_chapter" in ACTIONS
        assert "wait_for_arbiter" in ACTIONS
        assert "complete" in ACTIONS


class TestCheckerMore:
    def test_short_draft(self):
        issues = checker.deterministic_check("短" * 100)
        assert len(issues) > 0
    def test_long_draft(self):
        issues = checker.deterministic_check("长" * 6000)
        assert len(issues) > 0
    def test_tone_word(self):
        issues = checker.deterministic_check("他瞳孔微缩。")
        assert len(issues) > 0
    def test_tone_word2(self):
        issues = checker.deterministic_check("他心中一凛。")
        assert len(issues) > 0
    def test_no_false_positive(self):
        issues = checker.deterministic_check("")
        assert isinstance(issues, list)


class TestGatesMore:
    def test_todo(self):
        issues = gates.precommit_check("这是TODO待写内容", {})
        assert any("TODO" in i for i in issues)
    def test_short(self):
        issues = gates.precommit_check("短" * 100, {})
        assert any("字数" in i for i in issues)
    def test_long(self):
        issues = gates.precommit_check("长" * 6000, {})
        assert any("字数" in i for i in issues)


class TestAPIMore:
    def test_health(self):
        assert c.get("/health").status_code == 200
    def test_projects(self):
        assert c.get("/api/projects").status_code == 200
    def test_genres(self):
        assert c.get("/api/genres").status_code == 200
    def test_version(self):
        assert c.get("/api/version").status_code == 200
    def test_delete(self):
        c.post("/api/projects", json={"name": "test-del-2"})
        assert c.delete("/api/projects/test-del-2").status_code == 200
