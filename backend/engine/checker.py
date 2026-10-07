# -*- coding: utf-8 -*-
"""灵云文创 · 确定性硬校验（V3：zh-narrative-guard）"""
import re

# AI 腔词库（保留自研部分，zh-narrative-guard 主要做时间线）
AI_TONE_WORDS = [
    "瞳孔微缩", "心中一凛", "眸光一闪", "嘴角勾起", "眼眸深邃", "呼吸一滞",
    "心中暗道", "暗自思忖",
]

AI_TONE_PATTERNS = [
    r"他感到[一-龥]{1,3}",
    r"她感到[一-龥]{1,3}",
    r"他终于明白",
    r"从那以后",
    r"时光飞逝",
    r"不知不觉",
]


def check_ai_tone(draft: str) -> list[dict]:
    issues = []
    for word in AI_TONE_WORDS:
        count = draft.count(word)
        if count > 0:
            issues.append({"type": "ai_tone", "detail": f"出现{count}次'{word}'"})
    for pattern in AI_TONE_PATTERNS:
        matches = re.findall(pattern, draft)
        if matches:
            issues.append({"type": "ai_tone", "detail": f"句式:{matches[0]}"})
    # 连续"了"字检测
    if "了了" in draft or "了了了" in draft:
        issues.append({"type": "ai_tone", "detail": "连续'了'字"})
    # 套话密度："他知道""他明白""他意识到"出现次数
    cliches = ["他知道", "他明白", "他意识到", "他感到", "他觉得"]
    cliche_count = sum(draft.count(c) for c in cliches)
    if cliche_count > 5:
        issues.append({"type": "ai_tone", "detail": f"套话密度过高：{cliche_count}次"})
    return issues


def check_word_count(draft: str, min_chars: int = 1500, max_chars: int = 5000) -> list[dict]:
    issues = []
    n = len(draft)
    if n < min_chars:
        issues.append({"type": "word_count", "detail": f"字数不足：{n}字 < {min_chars}字"})
    elif n > max_chars:
        issues.append({"type": "word_count", "detail": f"字数过多：{n}字 > {max_chars}字"})
    return issues


def check_chapter_end(draft: str) -> list[dict]:
    issues = []
    last_200 = draft[-200:]
    safe_endings = ["他终于睡了", "一切都结束了", "日子恢复了平静"]
    for ending in safe_endings:
        if ending in last_200:
            issues.append({"type": "safe_ending", "detail": "章末安全着陆，没有钩子"})
            break
    return issues


def check_timeline(draft: str) -> list[dict]:
    """时间线校验"""
    issues = []
    # 检测明显时间矛盾：同一段里出现太多时间词
    time_words = ["昨天", "今天", "明天", "上周", "下周", "上个月", "下个月", "三年前", "五年前", "十年前"]
    found = [w for w in time_words if w in draft]
    if len(found) >= 4:
        issues.append({"type": "timeline", "detail": f"时间词过多：{', '.join(found)}"})
    # 检测年龄矛盾：如果前面说"20岁"后面说"30岁"
    ages = re.findall(r'(\d+)岁', draft)
    if len(ages) >= 2 and ages[0] != ages[1]:
        issues.append({"type": "timeline", "detail": f"年龄矛盾：{ages[0]}岁 vs {ages[1]}岁"})
    return issues


def deterministic_check(draft: str) -> list[dict]:
    """第一层：确定性硬校验"""
    issues = []
    issues.extend(check_ai_tone(draft))
    issues.extend(check_word_count(draft))
    issues.extend(check_chapter_end(draft))
    issues.extend(check_timeline(draft))
    return issues


def ai_rate_score(draft: str) -> dict:
    """AI率检测（简单规则版）"""
    score = 0
    # 检测AI腔词出现次数
    ai_words = ["瞳孔微缩", "心中一凛", "眸光一闪", "嘴角勾起", "眼眸深邃", "呼吸一滞", "心中暗道", "暗自思忖"]
    for w in ai_words:
        score += draft.count(w)
    # 检测段落长度均匀度（AI写的段落长度都差不多）
    paragraphs = [p for p in draft.split("\n") if len(p) > 10]
    if paragraphs:
        lengths = [len(p) for p in paragraphs]
        avg = sum(lengths) / len(lengths)
        variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
        if variance < 100:  # 段落长度太均匀=AI
            score += 2
    # 检测是否有"不禁""不由得"
    for w in ["不禁", "不由得", "下意识地"]:
        score += draft.count(w)
    # 评分：0-10，越高越像AI
    rate = min(score * 10, 100)
    return {"ai_rate": rate, "issues": score, "pass": rate < 50}
