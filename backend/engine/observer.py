# -*- coding: utf-8 -*-
"""灵云文创 · Observer Agent（观察者）"""
"""每章写完后自我反思：这章做了什么/改变了什么/有没有遗漏"""
from engine.llm import chat


def reflect_chapter(chapter: int, draft: str, beat: dict, truth_state: dict) -> dict:
    """Observer：观察本章执行结果，返回反思报告"""
    prompt = f"""你是小说观察者。根据本章内容，输出反思报告。

【本章 Beat】
目标：{beat.get('goal', '')}
冲突：{beat.get('conflict', '')}
预期情绪：{beat.get('emotion', '')}

【本章正文摘要】
{draft[:1500]}

【当前故事状态】
人物：{json.dumps(list(truth_state.get('characters', {}).keys()), ensure_ascii=False)}
待回收伏笔：{json.dumps(list(truth_state.get('hooks', {}).keys()), ensure_ascii=False)}

输出 JSON：
{{
  "what_happened": "本章实际发生了什么（100字内）",
  "what_changed": "哪些东西改变了（人物状态/关系/资源）",
  "beat_met": true/false,  // Beat 的目标达成了吗
  "unexpected": "有没有计划外的事情发生",
  "next_chapter_hint": "下一章应该接什么（一句话）",
  "missed_hooks": ["本章应该回收但没回收的伏笔"]
}}

直接输出 JSON。"""

    text = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=800,
    )
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"what_happened": "", "what_changed": "", "beat_met": True, "unexpected": "", "next_chapter_hint": "", "missed_hooks": []}


import json
