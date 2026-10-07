# -*- coding: utf-8 -*-
"""灵云文创 · Reviewer Agent（审稿）"""
"""5 维审查：设定一致性 / 时间线 / 叙事连贯 / 角色一致性(OOC) / 爽点密度"""
import json
from engine.llm import chat


def review_chapter(draft: str, task_brief: str) -> dict:
    prompt = f"""你是网文审稿编辑。审查以下章节，输出 JSON。

【任务书】
{task_brief[:2000]}

【正文】
{draft}

审查维度：
1. **设定一致性**：有没有和设定矛盾的地方？（角色名/境界/世界观）
2. **时间线**：时间推进是否合理？有没有时间错乱？
3. **叙事连贯**：剧情是否连贯？有没有突兀跳转？
4. **角色一致性(OOC)**：角色行为是否符合人设？有没有崩坏？
5. **爽点密度**：本章有没有爽点/钩子？节奏是否够紧凑？

输出 JSON：
{{
  "summary": "本章内容摘要（100字内）",
  "critical": ["严重问题1", "严重问题2"],
  "warnings": ["建议改进1", "建议改进2"],
  "ooc_issues": ["角色崩坏问题"],
  "pacing_score": 1-10,
  "has_climax": true/false
}}

直接输出 JSON。"""

    text = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=800, fast=True,
    )
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"summary": "", "critical": [], "warnings": [], "ooc_issues": [], "pacing_score": 5, "has_climax": False}
