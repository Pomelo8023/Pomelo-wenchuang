# -*- coding: utf-8 -*-
"""灵云文创 · 39 维审计"""
import json, re
from engine.llm import chat


def dialogue_ratio(text: str) -> float:
    """计算对话占比（引号内字数/总字数）"""
    total = len(text)
    if total == 0: return 0
    quotes = re.findall(r'["「「](.*?)["」」]', text, re.S)
    dialogue = sum(len(q) for q in quotes)
    return round(dialogue / total * 100, 1)


def audit_33dim(draft: str, brief: str, truth_state: dict) -> dict:
    """33 维审计：InkOS 完整审计体系"""
    prompt = f"""你是网文审计员。审查以下章节，输出 JSON。

【任务书】
{brief[:2000]}

【正文】
{draft}

【故事状态】
人物：{json.dumps(list(truth_state.get('characters', {}).keys()), ensure_ascii=False)}
活跃伏笔数：{len(truth_state.get('hooks', {}))}

33 个审查维度（分 6 大类）：

A. 设定一致性（5 维）
1. 角色名一致性：有没有写错名字
2. 境界/能力一致性：有没有境界越界
3. 世界观规则：有没有违反世界规则
4. 物品状态：已毁物品有没有再出现
5. 地理一致性：地点有没有错乱

B. 时间线（5 维）
6. 时间推进合理
7. 无时间回跳
8. 闪回框架正确
9. 季节/天气一致
10. 节日/事件时间对

C. 叙事连贯（5 维）
11. 剧情连贯无突兀跳转
12. 因果关系成立
13. 信息密度均匀
14. 转场自然
15. 无逻辑断层

D. 角色一致性 OOC（6 维）
16. 主角行为符合人设
17. 配角行为符合人设
18. 对话风格一致
19. 情绪变化合理
20. 关系演变自然
21. 无角色突然黑化/洗白

E. 爽点与节奏（7 维）
22. 本章有爽点/钩子
23. 章末钩子强度
24. 节奏快慢合适
25. 铺垫/释放比例
26. 情绪曲线合理
27. 无注水段落
28. 无重复描写

F. AI 味（5 维）
29. 无"缓缓/淡淡/微微"副词
30. 无"他感到XX"情绪标签
31. 无段末总结句
32. 对话自然无辩论赛
33. 无"终于明白/从那以后"

G. 读者契约（InkOS精华，3维）
34. 开头承诺的爽点/悬念，本章有没有兑现
35. 本章推进了至少2个轴（剧情/知识/关系/地位/危险/资源/自我认知）
36. 后果来自角色选择，不是巧合/敌人降智/突然开挂

H. 番茄硬指标（3维）
37. 对话占比≥30%（统计引号内字数/总字数）
38. 本章有明确爽点或钩子（不连续两章无冲突）
39. 章末钩子强度≥上一章

输出 JSON：
{{
  "summary": "本章摘要（100字）",
  "critical": ["严重问题1", "严重问题2"],
  "warnings": ["建议改进1", "建议改进2"],
  "scores": {{
    "consistency": 1-10,
    "timeline": 1-10,
    "coherence": 1-10,
    "ooc": 1-10,
    "pacing": 1-10,
    "ai_tone": 1-10,
    "reader_contract": 1-10
  }},
  "axes_changed": ["本章改了哪2个轴"],
  "overall_score": 1-10
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
        return {"summary": "", "scores": {}, "critical": [], "warnings": [], "overall_score": 5}
