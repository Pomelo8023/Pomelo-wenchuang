# -*- coding: utf-8 -*-
"""灵云文创 · Route 事实决策表（V3 确定性 Engine 核心）"""
"""纯事实判断，零 LLM 开销，决定下一步执行什么"""


def route(state: dict) -> str:
    """
    根据当前状态，决定下一步动作。
    纯事实判断，不调用 LLM。

    state 字段：
    - is_completed: bool（全部章节完成）
    - has_arc_plan: bool（有没有卷弧规划）
    - has_current_draft: bool（当前章有没有草稿）
    - is_reviewed: bool（草稿审查过没有）
    - review_passed: bool（审查通过没有）
    - retry_count: int（重写次数）
    - is_committed: bool（章节已提交没有）
    """
    # 1. 全部完成
    if state.get("is_completed"):
        return "complete"

    # 2. 没有卷弧规划 → 让 Architect 规划
    if not state.get("has_arc_plan"):
        return "plan_arc"

    # 3. 没有当前章草稿 → Writer 写
    if not state.get("has_current_draft"):
        return "write_chapter"

    # 4. 有草稿，没审查 → Editor 审查
    if not state.get("is_reviewed"):
        return "review_chapter"

    # 5. 审查不通过，重写次数 < 2 → Writer 重写
    if not state.get("review_passed") and state.get("retry_count", 0) < 2:
        return "write_chapter"

    # 6. 审查不通过，重写次数 >= 2 → Arbiter 仲裁
    if not state.get("review_passed") and state.get("retry_count", 0) >= 2:
        return "wait_for_arbiter"

    # 7. 审查通过，没提交 → 提交
    if state.get("review_passed") and not state.get("is_committed"):
        return "commit_chapter"

    # 8. 已提交，下一章
    return "next_chapter"


# 动作说明
ACTIONS = {
    "plan_arc": "Architect 规划卷弧",
    "write_chapter": "Writer 写正文",
    "review_chapter": "Editor 审查",
    "commit_chapter": "提交章节",
    "next_chapter": "进入下一章",
    "wait_for_arbiter": "Arbiter 仲裁（按需唤醒）",
    "complete": "全书完成",
}
