# -*- coding: utf-8 -*-
"""补充测试3"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.route import route, ACTIONS
from engine import checker, gates


class TestRouteFinal:
    def test_all_actions_exist(self):
        assert len(ACTIONS) == 7
    def test_route_returns_string(self):
        assert isinstance(route({}), str)
    def test_retry_zero(self):
        s = {"has_arc_plan": True, "has_current_draft": True, "is_reviewed": True, "review_passed": False, "retry_count": 0}
        assert route(s) == "write_chapter"


class TestCheckerFinal:
    def test_returns_list(self):
        assert isinstance(checker.deterministic_check("测试"), list)
    def test_each_issue_has_detail(self):
        for i in checker.deterministic_check("他瞳孔微缩。"):
            assert "detail" in i


class TestGatesFinal:
    def test_returns_list(self):
        assert isinstance(gates.precommit_check("测试", {}), list)


class TestAPIFinal:
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    def test_root(self):
        assert self.c.get("/").status_code == 200
    def test_docs(self):
        assert self.c.get("/docs").status_code == 200
