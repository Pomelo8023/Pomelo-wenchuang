# -*- coding: utf-8 -*-
"""灵云文创 · 写稿（writer）"""
from engine.llm import chat, chat_stream


def write_chapter(task_brief: str, on_delta=None, words_per=2000, words_min="", words_max="", chapter=1, stop_check=None, scenes=None, roleplay_text="") -> str:
    # 从task_brief里提取平台信息
    platform = "番茄"
    if "起点" in task_brief or "qidian" in task_brief.lower():
        platform = "起点"
    
    # 场景大纲（DOC）：如果有场景规划，注入并强制按场景写
    import json as _json
    scenes_block = ""
    if scenes:
        try:
            scenes_block = "\n\n【本章场景大纲·必须按此结构写】\n" + _json.dumps(scenes, ensure_ascii=False, indent=1)
        except Exception:
            scenes_block = ""
    # 角色扮演实录（Character Simulation）：已排演的对话必须融入正文
    rp_block = ""
    if roleplay_text:
        rp_block = f"""\n\n【本章角色对话实录（编剧已排演，必须融入正文）】
这是本场戏的"台词底稿"。写正文时必须：
1. 把这些对话原汁原味写进正文，可以加动作、神态、心理、环境描写来包裹
2. 保持台词本身的话锋和潜台词，不要改写成更"完整得体"的句子
3. 台词分布到对应场景中，不要堆在一处

{roleplay_text}"""
    
    # 字数范围：优先用words_min和words_max，否则用words_per的±10%
    try:
        if words_min and words_max:
            words_min_int = int(words_min)
            words_max_int = int(words_max)
            words_range_text = f"本章必须写{words_min_int}-{words_max_int}字，不能少于{words_min_int}字，不能多于{words_max_int}字"
        else:
            raise ValueError("empty")
    except (ValueError, TypeError):
        words_min_int = int(words_per * 0.9)
        words_max_int = int(words_per * 1.1)
        words_range_text = f"本章目标{words_per}字，不能少于{words_min_int}字，不能多于{words_max_int}字"

    # 平台差异化规则
    if platform == "番茄":
        platform_rules = """【番茄平台规则·必须遵守】
- 段落短：每段不超过3行，平均50-80字
- 节奏快：每300字一个情绪波动，每500字一个小爽点
- 前100字定生死：开头必须有冲突/悬念/身份反差
- 爽点密：每章至少1个小爽点，每3-5章一个大爽点
- 对话多：对话占30-40%
- 不要慢热：前300字必须有冲突"""
    else:
        platform_rules = """【起点平台规则·必须遵守】
- 段落稍长：每段3-5行，平均80-120字
- 设定深：世界观完整，力量体系清晰
- 节奏稳：每500字一个情绪波动，每1000字一个小爽点
- 伏笔多：每章至少埋1个伏笔，后续回收
- 对话适中：对话占25-35%
- 可以慢热：前500字可以铺垫，但必须有悬念"""

    opening_hint = ""
    if chapter == 1:
        opening_hint = """
【第1章特别要求·黄金三章】
- 第一句话就要抓住人：用冲突/悬念/反差开场，不要写景
- 前300字内必须出现主角+核心矛盾
- 不要大段背景介绍，设定藏在动作和对话里
- 章末必须留钩子：让读者想点"下一章"
- 节奏要快：每500字一个小爽点或小转折"""
    sys_prompt = f"""你是一个网文写手。根据任务书直接输出正文，不要写任何解释、不要加标题、不要用 markdown。直接从正文第一句开始。

【字数硬要求·绝对不能违反】
{words_range_text}
- 写完后自己数一下字数，超了就删，少了就补

设定只放出10%，剩下90%藏在剧情里，不要大段科普。{opening_hint}

{platform_rules}

【写作铁律·真人风格】
1. 长短句交替：长句拆成3-7字短句，制造呼吸感。不要连续三句一样长。
2. 抽象改具象：不要写"他很伤心"，写"他低着头，手指抠着桌角"。
3. 加生活毛边：每章至少3个具体细节（气味/声音/触感/物品），不要空泛。
4. 打破对称：不要排比句、不要对偶句、不要"首先其次最后"。
5. 砍形容词：90%的形容词删掉，用精准动词代替。
6. 对话有话外音：人物说话不要念说明书，要藏着话。
7. 不要总结句：结尾不要总结本章发生了什么。
8. 口语化：对话里加"靠""哎""真是的"这种口语词。
9. 每句话必须推进剧情。删了它读者会错过什么？nothing就删。
10. 不要写心理活动、气氛描写、人物反应（停/愣/顿/沉默/皱眉/眯眼/深吸一口气）。
11. 同一个动作/反应/比喻，整章最多出现2次。超过2次就是注水，必须换写法。
12. 不要用破折号开头、不要用"他XX了一下"这种句式，直接写动作。
13. 不要评书腔：不要"只见""却说""话说""且说""列位看官"。
14. 每500字一个小转折或小爽点，不要平铺直叙。
15. 场景切换要硬切，不要"与此同时""另一边"这种过渡。

【爆款硬指标】
- 每章结尾必须留钩子：让读者想点"下一章"
- 每3-5章一个小高潮：打脸/反转/爽点
- 不要慢热铺垫：前300字必须有冲突或悬念
- 不要虐主压抑：主角要立刻反击
- 不要日常情感戏：每章必须有事件推进

【节奏控制·张弛有度】
- 连续紧张3-4章后，第5章安排一个"喘息章节"：节奏放缓，让读者放松
- 喘息章节可以是：收获战利品、休整队伍、和配角聊天、发现新线索
- 但喘息章节也不能完全没有冲突，要埋一个小钩子
{scenes_block}
{rp_block}

【爽点类型·多样化】
不要只用一种爽点，交替使用：
1. 智斗爽点：算计对手、反杀、预判
2. 打脸爽点：看不起主角的人被打脸
3. 装逼爽点：主角露一手，旁人震惊
4. 武力爽点：主角展示实力
5. 收获爽点：拿到好东西、升级、变强
每章至少有1种爽点，不要连续两章用同一种。

【人物关系·扩展】
- 不要只有主角和反派两个人，要有配角：兄弟、姐妹、邻居、下属、敌人
- 每个配角要有自己的性格和动机，不是工具人
- 配角之间也要有互动，不要都围着主角转
- 每章至少有1个配角出场或被提到

【世界观·慢慢展开】
- 不要一次性把世界观全说出来，每次只放出一小片
- 通过主角的眼睛、对话、行动，让读者慢慢了解这个世界
- 每章只引入1个新概念（新地名/新势力/新规则），不要贪多
- 前面埋的设定，后面要用到，不要浪费"""
    # 物理卡 max_tokens：按目标 max 字数 × 2.2 token/字 + 余量，从生成层面防超标
    hard_max_tokens = int(words_max_int * 2.2) + 300
    if on_delta:
        return chat_stream(
            messages=[{"role": "system", "content": sys_prompt},
                      {"role": "user", "content": task_brief}],
            temperature=0.85, max_tokens=hard_max_tokens, on_delta=on_delta,
            stop_check=stop_check,
        )
    return chat(
        messages=[{"role": "system", "content": sys_prompt},
                  {"role": "user", "content": task_brief}],
        temperature=0.85, max_tokens=hard_max_tokens,
    )


def rewrite_chapter(draft: str, issues: str) -> str:
    """针对性修正：把问题列表和整章给LLM，让LLM只改有问题的部分"""
    prompt = f"""你是一个网文编辑。以下是小说章节，以及需要修正的问题。

【需要修正的问题】
{issues}

【章节原文】
{draft}

【修正要求】
1. 只改有问题的部分，不要改其他内容
2. 保持原来的风格、剧情、人物性格
3. 不要加新的剧情，不要删原来的剧情
4. 直接输出修正后的完整章节，不要解释"""
    try:
        fixed = chat(
            messages=[
                {"role": "system", "content": "你是网文编辑，直接输出修正后的章节，不要解释。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=6000,
        )
        if fixed and len(fixed) > 500:
            return fixed
    except Exception:
        pass
    # 兜底：如果修正失败，返回原文
    return draft


def polish_chapter(draft: str) -> str:
    """润色：去 AI 味、调节奏、修病句"""
    prompt = f"""润色以下网文段落，只改文字不改剧情：

【润色要求】
1. 删掉"缓缓/淡淡/微微/轻轻"等副词，用具体动作替代
2. 删掉"他感到XX"式情绪标签，改写生理反应+微动作
3. 删掉每段末尾的总结/感悟句
4. 对话加潜台词、打断、省略
5. 调节奏：有的段落只有一句话，有的十几句
6. 修病句，但不要改剧情走向

【原文】
{draft}

直接输出润色后的正文，不要解释。"""
    return chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000,
    )


def gen_title(draft: str) -> str:
    """根据正文生成章节标题"""
    prompt = f"""根据以下章节内容，生成一个 4-8 字的章节标题，要有网文感（悬念/爽点/冲突）。

【内容】
{draft[:500]}

只输出标题，不要解释，不要加引号。"""
    return chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=50,
        fast=True,
    )
