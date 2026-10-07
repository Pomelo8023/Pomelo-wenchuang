# -*- coding: utf-8 -*-
"""灵云文创 · 引擎开关（设置页可调）
所有开关存在项目 canon.json 的 engine_toggles 字段里，未设置时用默认值。
"""

DEFAULTS = {
    "roleplay": True,          # 角色扮演排演
    "critics": True,            # 多批评者深审
    "scenes": True,             # DOC 场景拆解
    "vector_rag": False,       # 向量语义检索（默认关，需先建索引）
    "auto_patrol": True,        # 跨章矛盾巡检
    "patrol_interval": 10,      # 每 N 章巡检一次
    "auto_export": True,        # 全书写完自动导出
    "state_changes": True,      # 写人物状态变化表
    "inter_chapter_delay": 0,   # 章间等待秒数（防限流，默认不等待）
}


def get_toggles(canon: dict) -> dict:
    """从 canon 读取开关，缺省补默认值。"""
    t = dict(DEFAULTS)
    stored = canon.get("engine_toggles") or {}
    if isinstance(stored, dict):
        t.update({k: v for k, v in stored.items() if k in DEFAULTS})
    return t


def set_toggle(canon: dict, key: str, value) -> dict:
    """写回一个开关（不改 canon 其他字段）。"""
    if key not in DEFAULTS:
        return canon
    t = canon.get("engine_toggles") or {}
    t[key] = value
    canon["engine_toggles"] = t
    return canon
