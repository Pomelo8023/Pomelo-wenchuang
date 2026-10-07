# -*- coding: utf-8 -*-
"""灵云文创 · Collective Critics（CRITICS）：多视角评审 + Leader 裁决
一次 LLM 调用让模型同时扮演三个批评者（读者/编辑/逻辑侦探），输出各自挑刺，再裁决是否重写。
"""
import json
from engine.llm import chat


def collective_review(draft: str, beat: dict, brief: str) -> dict:
    """多批评者评审。返回:
    {
      "reader_issues": [...],   # 读者视角：爽点/节奏/代入感
      "editor_issues": [...],   # 编辑视角：结构/冲突/钩子
      "logic_issues": [...],    # 逻辑侦探：人物一致性/时间线/设定矛盾
      "verdict": "pass|revise",
      "top_issues": [...],      # Leader 汇总的最关键的 1-3 条
    }
    """
    goal = (beat.get("goal") or "")[:100]
    prompt = f"""你是三位资深网文评审 + 一位主编。请从三个视角评审下面这章，然后主编裁决。

【本章目标】{goal}

【章节正文】
{draft[:3000]}

输出 JSON：
{{
  "reader_issues": ["读者视角挑刺：爽点不足/节奏拖沓/代入感差等，最多3条"],
  "editor_issues": ["编辑视角挑刺：结构松散/冲突不足/章末钩子弱等，最多3条"],
  "logic_issues": ["逻辑侦探挑刺：人物言行不一致/时间线矛盾/设定冲突等，最多3条"],
  "verdict": "pass 或 revise",
  "top_issues": ["主编汇总最关键的重写理由，最多2条，没有则空数组"]
}}

要求：
- 每个视角独立判断，不要互相抄
- 只有真正影响阅读体验的问题才写，吹毛求疵的不要写
- verdict=pass 表示这章不用重写
- 直接输出 JSON，不要解释。"""
    try:
        text = chat(messages=[{"role": "user", "content": prompt}], temperature=0.4, max_tokens=600, fast=True)
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(text)
        result.setdefault("reader_issues", [])
        result.setdefault("editor_issues", [])
        result.setdefault("logic_issues", [])
        result.setdefault("top_issues", [])
        result.setdefault("verdict", "pass")
        return result
    except Exception:
        return {"reader_issues": [], "editor_issues": [], "logic_issues": [],
                "verdict": "pass", "top_issues": []}
