# -*- coding: utf-8 -*-
"""灵云文创 · 文风学习（借鉴 InkOS style-guide）"""
from engine.llm import chat


def extract_style_guide(text: str) -> str:
    """从一段参考文本提取可执行的文风指南"""
    sample = text[:4000]
    prompt = f"""分析以下参考文本的文风，输出可执行的写作指南（100字内）。

分析维度：
1. 叙事距离（第一人称/第三人称？贴近主角还是上帝视角？）
2. 对话风格（简练/话多？带潜台词？）
3. 句式节奏（短句多/长句多？段落长短？）
4. 用词习惯（口语化/文绉绉？现代词/古风词？）
5. 情绪外化（直接写情绪名/用动作生理反应？）

【参考文本】
{sample}

直接输出文风指南，不要解释。"""

    return chat(messages=[{"role": "user", "content": prompt}],
                temperature=0.3, max_tokens=300, fast=True).strip()
