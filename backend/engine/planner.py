# -*- coding: utf-8 -*-
"""灵云文创 · 卷弧双层滚动规划（借鉴 InkOS 卷弧设计）"""
"""初始只规划前 2 卷骨架 + 第 1 卷详细章节，后续卷在写作推进到时再展开"""
from engine.llm import chat


def plan_volumes(total_chapters: int, canon: dict) -> dict:
    """规划全书卷弧骨架"""
    prompt = f"""你是网文架构师。根据以下设定，规划全书卷弧。

【设定】
{json.dumps(canon, ensure_ascii=False, indent=2)[:1500]}

【总章数】{total_chapters}章

输出 JSON：
{{
  "volumes": [
    {{
      "volume_num": 1,
      "chapter_range": "1-30",
      "title": "第一卷标题",
      "summary": "本卷核心冲突（100字）",
      "climax_chapter": 28,
      "ending_hook": "卷末钩子"
    }}
  ]
}}

直接输出 JSON。"""

    text = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8, max_tokens=2000,
    )
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"volumes": []}


def plan_chapter_detail(chapter: int, volume: dict, canon: dict, active_hooks: dict) -> dict:
    """为当前章生成详细 beat"""
    prompt = f"""你是网文导演。为第 {chapter} 章生成详细 beat。

【当前卷】
{json.dumps(volume, ensure_ascii=False)}

【设定】
{json.dumps(canon, ensure_ascii=False)[:1000]}

【待回收伏笔】
{json.dumps({k: v['summary'] for k, v in list(active_hooks.items())[:3]}, ensure_ascii=False)}

输出 JSON：
{{
  "goal": "本章目标",
  "conflict": "核心冲突",
  "characters": ["出场人物"],
  "emotion": "主情绪",
  "intensity": 1-10,
  "is_climax": false,
  "ending_hook": "章末钩子"
}}

直接输出 JSON。"""

    text = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7, max_tokens=800,
    )
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"goal": "推进剧情", "conflict": "未知", "emotion": "平", "intensity": 5, "is_climax": False, "ending_hook": "..."}


import json
