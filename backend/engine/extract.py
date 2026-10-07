# -*- coding: utf-8 -*-
"""灵云文创 · 数据提取（借鉴 webnovel-writer data-agent）"""
import json
from engine.llm import chat


def extract_chapter_data(content: str, chapter: int) -> dict:
    prompt = f"""从以下章节提取结构化信息，输出严格 JSON：

【正文】
{content}

输出格式：
{{
  "characters": [
    {{"name": "角色名", "state_change": "本章状态变化", "is_new": false}}
  ],
  "events": [
    {{"type": "fight|dialogue|discovery|transition", "summary": "100字内", "location": "地点"}}
  ],
  "new_foreshadows": [
    {{"summary": "埋下的伏笔", "type": "悬念|情感|爽点|世界观", "strength": "strong|medium|weak"}}
  ],
  "foreshadow_updates": [
    {{"id": "已有伏笔id", "action": "mention|advance|resolve", "note": "本章怎么处理的"}}
  ],
  "relation_changes": [
    {{"a": "角色A名", "b": "角色B名", "type": "friend|enemy|lover|family|mentor", "delta": 10}}
  ],
  "resource_changes": [
    {{"item": "钱/法宝/能力名", "delta": "+1000两 / -1颗丹药 / 突破到筑基", "reason": "为什么变"}}
  ]
}}

没有的字段给空数组。不要解释，直接输出 JSON。"""

    text = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1000,
        fast=True,
    )
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"characters": [], "events": [], "new_foreshadows": [],
                "relation_changes": [], "resource_changes": []}
