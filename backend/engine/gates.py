# -*- coding: utf-8 -*-
"""灵云文创 · write_gates 三道门
prewrite: director 出合同（已在 director.py 做了）
precommit: commit 前检查 draft 覆盖了 must_cover_nodes、无占位符
postcommit: commit 后检查伏笔回收、events 落盘
"""
import re


def precommit_check(draft: str, beat: dict) -> list:
    """返回问题列表，空列表=通过"""
    issues = []

    # 1. 占位符扫描
    placeholders = re.findall(r'(TODO|FIXME|xxx|XXX|【待补】|\[占位\]|placeholder)', draft)
    if placeholders:
        issues.append(f"发现占位符: {set(placeholders)}")

    # 2. 字数检查
    wc = len(draft)
    if wc < 1500:
        issues.append(f"字数不足: {wc}字（要求2000+）")
    elif wc > 5000:
        issues.append(f"字数过多: {wc}字（要求<5000）")

    # 3. must_cover_nodes 关键词覆盖（简单匹配）
    for node in beat.get("must_cover_nodes", []):
        # 取节点里最长的词做匹配
        keywords = [w for w in re.split(r'[，。、；：]', node) if len(w) >= 2]
        if keywords and not any(k in draft for k in keywords):
            issues.append(f"未覆盖节点: {node[:30]}")

    # 4. forbidden_zones 检查
    for fz in beat.get("forbidden_zones", []):
        keywords = [w for w in re.split(r'[，。、；：]', fz) if len(w) >= 2]
        if keywords and any(k in draft for k in keywords[:2]):
            issues.append(f"出现禁写内容: {fz[:30]}")

    return issues


def postcommit_check(conn, chapter: int, hook_to_resolve) -> list:
    """commit 后检查：伏笔回收成功没、events 落盘没"""
    issues = []
    if hook_to_resolve:
        row = conn.execute("SELECT status FROM foreshadow_contracts WHERE id=?",
                           (int(hook_to_resolve),)).fetchone()
        if row and row["status"] != "resolved":
            issues.append(f"伏笔 #{hook_to_resolve} 未标记为 resolved")
    event_count = conn.execute("SELECT COUNT(*) c FROM events WHERE chapter=?",
                               (chapter,)).fetchone()["c"]
    if event_count == 0:
        issues.append("本章没有 events 落盘")
    return issues


def postaudit_check(audit_result: dict) -> dict:
    """第4道门：审计后判定是否需要重写
    返回: {"need_rewrite": bool, "reason": str, "severity": "ok|warn|fail"}
    """
    score = audit_result.get("overall_score", 80)
    ooc = audit_result.get("ooc_count", 0)
    timeline_conflict = audit_result.get("timeline_conflict", 0)
    lore_break = audit_result.get("lore_break", 0)

    reasons = []
    if ooc >= 2:
        reasons.append(f"OOC 达 {ooc} 处")
    if timeline_conflict >= 1:
        reasons.append(f"时间线矛盾 {timeline_conflict} 处")
    if lore_break >= 1:
        reasons.append(f"设定崩坏 {lore_break} 处")
    if score < 60:
        reasons.append(f"总分 {score} 太低")

    if score < 50 or ooc >= 3 or lore_break >= 2:
        return {"need_rewrite": True, "reason": "；".join(reasons), "severity": "fail"}
    if reasons:
        return {"need_rewrite": False, "reason": "；".join(reasons) + "（记录但不重写）", "severity": "warn"}
    return {"need_rewrite": False, "reason": "通过", "severity": "ok"}


def prewrite_contract_check(beat: dict) -> list:
    """第0道门：写前合同完整性检查"""
    issues = []
    if not beat.get("goal"):
        issues.append("beat 缺 goal")
    if not beat.get("hook"):
        issues.append("beat 缺 hook（章末钩子）")
    if not beat.get("must_cover_nodes"):
        issues.append("beat 缺 must_cover_nodes（要写什么）")
    return issues
