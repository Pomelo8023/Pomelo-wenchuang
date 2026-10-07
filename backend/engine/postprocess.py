# -*- coding: utf-8 -*-
"""灵云文创 · 一体化后处理：一次 LLM 调用搞定 审稿+提取+审计+标题"""
import json, re
from engine.llm import chat_stream as chat
from engine.deslop import deslop, ai_score


def postprocess_chapter(draft: str, brief: str, beat: dict, words_min: int = 0, words_max: int = 99999, stop_check=None) -> dict:
    """一次调用输出所有需要的结构化结果，省 3 次 LLM 往返"""
    # 7道门去AI味
    draft = deslop(draft)
    # AI味评分
    ai = ai_score(draft)

    # 从brief里提取题材
    genre = ""
    for line in brief.split("\n"):
        if "题材" in line or "genre" in line.lower():
            genre = line.split("：")[-1].split(":")[-1].strip()
            break

    # 悬念事前规划：beat 里导演定的埋/收伏笔，强制后处理对齐
    hook_plan = ""
    try:
        hp = beat.get("hook_to_plant") or ""
        hr = beat.get("hook_resolve_summary") or ""
        if hp or hr:
            hook_plan = f"""【本章伏笔计划（导演已定，必须遵守）】
- 要回收：{hr or "无"}
- 要新埋：{hp or "无"}
resolved_foreshadows 必须包含要回收的伏笔摘要；new_foreshadows 必须包含要新埋的伏笔摘要。"""
    except Exception:
        pass

    prompt = f"""你是网文编辑+数据提取员+审计员。处理以下章节，一次输出全部 JSON。

【任务书】
{brief[:1500]}

{hook_plan}

【本章必须覆盖的节点（must_cover_nodes）】
{chr(10).join([f"- {node}" for node in beat.get("must_cover_nodes", [])]) or "无"}

【本章禁止出现的内容（forbidden_zones）】
{chr(10).join([f"- {zone}" for zone in beat.get("forbidden_zones", [])]) or "无"}

【正文】
{draft}

输出一个 JSON，包含 5 个部分：
{{
  "title": "4-8字章节标题，要有网文感，必须从正文内容提炼，不能用'第X章'",
  "summary": "本章100字摘要",
  "characters": [{{"name":"人名","state_change":"状态变化","is_new":false,"emotion":"当前情绪","archetype":"角色原型，只能从以下选一个：family/warrior/sage/noble/creature/divine/demon/female/mysterious/faction/npc"}}],
  "events": [{{"type":"fight|dialogue|discovery|transition","summary":"50字","location":"地点","elapsed":"本章过了多久，比如'3天'/'1小时'/'一周'","characters":["出场人物1","出场人物2"]}}],
  "new_foreshadows": [{{"summary":"伏笔","type":"悬念|情感|爽点|世界观","strength":"strong|medium|weak","lifecycle":"immediate|near-term|mid-arc|slow-burn|endgame"}}],
  "resolved_foreshadows": ["本章明确解答/回收的之前埋下的伏笔摘要，没有就空数组"],
  "critical": ["严重问题1","严重问题2"],
  "must_cover_check": {{
    "covered": ["已覆盖的节点1","已覆盖的节点2"],
    "missing": ["未覆盖的节点1","未覆盖的节点2"]
  }},
  "forbidden_check": {{
    "found": ["发现的禁写内容1","发现的禁写内容2"]
  }},
  "scores": {{
    "satisfaction": 1-10,
    "pacing": 1-10,
    "hook_strength": 1-10,
    "characterization": 1-10,
    "conflict_escalation": 1-10,
    "ai_tone": 1-10,
    "consistency": 1-10,
    "show_dont_tell": 1-10,
    "genre_consistency": 1-10,
    "dialogue_quality": 1-10,
    "scene_vividness": 1-10,
    "information_density": 1-10,
    "foreshadow_recovery": 1-10,
    "world_building": 1-10,
    "originality": 1-10,
    "sensory_richness": 1-10,
    "character_balance": 1-10,
    "dialogue_distinctiveness": 1-10,
    "tone_consistency": 1-10,
    "emotional_investment": 1-10,
    "structure_completeness": 1-10,
    "outline_alignment": 1-10
  }},
  "overall_score": 1-10,
  "next_chapter_hint": "下一章写什么"
}}

二十二维评分说明（10=最好，1=最差）：
核心维度（必须≥8分）：
- satisfaction：爽点满足度，读者看完爽不爽
- pacing：节奏，每300字有没有情绪波动，有没有拖沓
- hook_strength：章末钩子强不强，想不想看下一章
- characterization：人物立不立得住，有没有辨识度
- conflict_escalation：冲突有没有升级，剧情有没有推进
- ai_tone：AI味重不重（10=完全没有AI味，1=全是AI味）
- consistency：前后连贯性，有没有矛盾
- show_dont_tell：有没有用动作代替心理描写
- genre_consistency：题材一致性，有没有偏离{genre or '设定题材'}

辅助维度（参考）：
- dialogue_quality：对话质量，自然不自然，有没有话外音
- scene_vividness：场景描写生不生动，有没有具体细节
- information_density：信息密度合不合适，有没有注水
- foreshadow_recovery：伏笔回收好不好，有没有埋了不回收
- world_building：世界观自洽不自洽，有没有设定崩坏
- originality：创意新颖度，有没有套路化
- sensory_richness：感官描述丰富度，有没有视觉/听觉/嗅觉/味觉/触觉
- character_balance：角色平衡度，每个角色有没有戏份，不要主角独角戏
- dialogue_distinctiveness：角色对白独特性，不同角色说话方式能不能听出区别
- tone_consistency：语气一致性，全章语气统一，不要一会冷峻一会搞笑
- emotional_investment：情感投入，读者能不能共情，看完心里有没有波动
- structure_completeness：结构完整性，本章有没有开头/发展/高潮/结尾，不要半截
- outline_alignment：大纲一致性，本章和大纲一致吗，有没有跑偏

标题要求：
- 必须从正文内容提炼，不能用"第X章"
- 4-8个字，要有网文感
- 要包含本章核心事件或悬念

没有的字段给空数组。直接输出 JSON。"""

    text = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=2000, fast=True,
        stop_check=stop_check,
    )
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"title": "", "summary": "", "characters": [], "events": [],
                "new_foreshadows": [], "resolved_foreshadows": [],
                "critical": [], "scores": {},
                "must_cover_check": {"covered": [], "missing": []},
                "forbidden_check": {"found": []},
                "overall_score": 5, "next_chapter_hint": ""}

    # 标题兜底：如果标题是空的或者是"第X章"，重新生成
    title = (result.get("title") or "").strip()
    if not title or re.match(r'^第\d+章$', title) or title == "第4章":
        try:
            title_prompt = f"""根据以下章节内容，生成一个4-8字的网文标题，要有网文感，必须包含核心事件或悬念，不能用"第X章"。

【章节内容】
{draft[:1000]}

直接输出标题，不要解释。"""
            new_title = chat(messages=[{"role": "user", "content": title_prompt}],
                           temperature=0.5, max_tokens=50, fast=True).strip()
            if new_title and not re.match(r'^第\d+章$', new_title):
                result["title"] = new_title
        except Exception:
            pass

    # 兜底：如果events是空的！就用章节标题作为event！
    if not result.get("events"):
        result["events"] = [{
            "type": "transition",
            "summary": result.get("summary", "")[:50],
            "location": ""
        }]
    
    # 题材一致性检查：如果分数低，加入critical
    genre_score = result.get("scores", {}).get("genre_consistency", 10)
    if genre_score < 6:
        result["critical"].append(f"题材一致性低（{genre_score}/10），可能偏离设定题材")
    
    # must_cover_nodes检查：未覆盖的节点加入critical
    must_cover_check = result.get("must_cover_check", {})
    missing_nodes = must_cover_check.get("missing", [])
    if missing_nodes:
        result["critical"].append(f"未覆盖必须节点：{', '.join(missing_nodes[:3])}")
    
    # forbidden_zones检查：发现的禁写内容加入critical
    forbidden_check = result.get("forbidden_check", {})
    found_forbidden = forbidden_check.get("found", [])
    if found_forbidden:
        result["critical"].append(f"出现禁写内容：{', '.join(found_forbidden[:3])}")

    # 量化检查：自动计算，不用LLM
    quant_check = quantitative_check(draft, words_min, words_max)
    result["quantitative"] = quant_check
    if quant_check["issues"]:
        result["critical"].extend(quant_check["issues"])

    # Post-generation verification：对比事实库，标记矛盾
    try:
        from engine.llm import chat_stream as chat2
        verify_prompt = f"""检查以下章节是否与已有事实矛盾：

【本章内容】
{draft[:1000]}

【已有事实（从项目设定提取）】
{brief[:500]}

如果有矛盾，列出矛盾点；如果没有，返回"无矛盾"。
直接输出矛盾列表，不要解释。"""
        contradictions = chat2(messages=[{"role": "user", "content": verify_prompt}], temperature=0.2, max_tokens=200, fast=True)
        if "无矛盾" not in contradictions:
            result["critical"].append(f"矛盾：{contradictions[:100]}")
    except Exception:
        pass

    # 打印审查结果
    if result.get("critical"):
        print(f"[postprocess] 发现问题：{len(result['critical'])}个，分数{result.get('overall_score', 5)}/10")
        for issue in result["critical"][:5]:
            print(f"  - {issue}")

    return result


def quantitative_check(draft: str, words_min: int = 0, words_max: int = 99999) -> dict:
    """量化检查：自动计算冲突密度、爽点密度、情绪波动、高频词、段落长度、开篇检查、字数检查"""
    issues = []
    
    # 0. 字数检查：必须在words_min-words_max范围内
    char_count = len(draft)
    if char_count < words_min:
        issues.append(f"字数不足：{char_count}字（要求{words_min}+）")
    elif char_count > words_max:
        issues.append(f"字数超标：{char_count}字（要求{words_max}-）")

    # 1. 段落长度检查：平均≤3行
    paragraphs = [p for p in draft.split("\n") if p.strip()]
    avg_para_len = sum(len(p) for p in paragraphs) / max(len(paragraphs), 1)
    if avg_para_len > 100:  # 超过100字算长段落
        issues.append(f"段落过长（平均{avg_para_len:.0f}字），建议拆短")

    # 2. 高频词检查：同一个词出现≤3次/章
    words = re.findall(r'[\u4e00-\u9fa5]{2,4}', draft)
    word_count = {}
    for w in words:
        word_count[w] = word_count.get(w, 0) + 1
    high_freq = {w: c for w, c in word_count.items() if c > 5 and len(w) >= 2}
    if high_freq:
        top3 = sorted(high_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        issues.append(f"高频词过多：{', '.join([f'{w}({c}次)' for w, c in top3])}")

    # 3. 开篇检查：前100字必须有冲突/悬念/动作
    first_100 = draft[:100]
    conflict_words = ["杀", "死", "打", "骂", "逼", "威胁", "危机", "危险", "秘密", "竟然", "居然", "突然", "猛地", "一把", "狠狠", "冷笑", "怒吼", "惨叫"]
    has_conflict = any(w in first_100 for w in conflict_words)
    if not has_conflict:
        issues.append("开篇100字内没有冲突/动作，建议加强开头")

    # 4. 情绪波动检查：每500字至少1个情绪变化（通过动作词判断）
    emotion_words = ["愤怒", "恐惧", "悲伤", "喜悦", "惊讶", "紧张", "焦虑", "绝望", "希望", "激动", "冷静", "犹豫", "坚定", "咬牙", "握拳", "颤抖", "皱眉", "冷笑"]
    emotion_count = sum(draft.count(w) for w in emotion_words)
    emotion_density = emotion_count / max(len(draft) / 500, 1)
    if emotion_density < 0.5:
        issues.append(f"情绪波动不足（每500字{emotion_density:.1f}次），建议增加情绪变化")

    # 5. 对话占比检查：20-50%（支持中文引号）
    dialogue_chars = len(re.findall(r'[“"][^”"]*[”"]', draft))
    dialogue_ratio = dialogue_chars / max(len(draft), 1)
    if dialogue_ratio < 0.15:
        issues.append(f"对话过少（{dialogue_ratio:.0%}），建议增加对话")
    elif dialogue_ratio > 0.6:
        issues.append(f"对话过多（{dialogue_ratio:.0%}），建议减少对话")

    # 6. AI味词汇检查（只检查典型AI味句式）
    ai_words = ["愣了一下", "停了一下", "顿了一下", "深吸一口气", "瞳孔微缩", "心中一凛", "不由得", "不禁", "仿佛", "似乎", "好像"]
    ai_count = sum(draft.count(w) for w in ai_words)
    if ai_count > 8:
        issues.append(f"AI味词汇过多（{ai_count}次），建议替换")

    return {
        "avg_para_len": avg_para_len,
        "high_freq_words": top3 if high_freq else [],
        "has_opening_conflict": has_conflict,
        "emotion_density": emotion_density,
        "dialogue_ratio": dialogue_ratio,
        "ai_word_count": ai_count,
        "issues": issues
    }
