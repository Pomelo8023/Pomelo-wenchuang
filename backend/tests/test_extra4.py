# -*- coding: utf-8 -*-
"""引擎开关 + Story Bible 纯逻辑测试（不调 LLM）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.settings import DEFAULTS, get_toggles, set_toggle


def test_get_toggles_default():
    t = get_toggles({})
    for k, v in DEFAULTS.items():
        assert t[k] == v, f"{k} 默认值不对"


def test_get_toggles_override():
    canon = {"engine_toggles": {"critics": False, "patrol_interval": 20}}
    t = get_toggles(canon)
    assert t["critics"] is False
    assert t["patrol_interval"] == 20
    # 未设置的仍用默认
    assert t["scenes"] is True


def test_set_toggle_unknown_key():
    canon = {}
    canon = set_toggle(canon, "not_exist_key", True)
    assert "not_exist_key" not in canon.get("engine_toggles", {})


def test_set_toggle_writes():
    canon = {}
    canon = set_toggle(canon, "critics", False)
    assert canon["engine_toggles"]["critics"] is False


def test_toggles_unknown_value_ignored():
    # 存储里如果有不在 DEFAULTS 的 key，get_toggles 应过滤掉
    canon = {"engine_toggles": {"scenes": True, "hacker_key": "x"}}
    t = get_toggles(canon)
    assert "hacker_key" not in t
