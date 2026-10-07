# -*- coding: utf-8 -*-
"""7道门去AI味：A禁用词→B公式句式→C展示代替告诉→D节奏变化→E自然对话→F删总结结尾→G删全知叙述"""
import re

# ===== A门：禁用词替换 =====
BAN_WORDS = [
    (re.compile(r'瞳孔(微缩|一缩|骤缩)'), ''),
    (re.compile(r'心中(一凛|暗道|一惊|一动|一沉)'), ''),
    (re.compile(r'眸光(一闪|微动|流转)'), ''),
    (re.compile(r'嘴角(勾起|上扬|抽搐|微动)'), ''),
    (re.compile(r'眼眸(深邃|低垂|微抬)'), ''),
    (re.compile(r'呼吸(一滞|急促|沉重|微顿)'), ''),
    (re.compile(r'他(停|愣|顿|沉默|犹豫|犹豫了|迟疑|怔)了一下'), ''),
    (re.compile(r'他沉默(了|片刻|不语)'), ''),
    (re.compile(r'他没有说话'), ''),
    (re.compile(r'空气(仿佛|似乎|骤然)凝固了'), ''),
    (re.compile(r'时间(仿佛|似乎|骤然)静止了'), ''),
    (re.compile(r'心跳(漏了|骤停|加速)一拍'), ''),
    (re.compile(r'四周一片死寂'), ''),
]

# ===== B门：公式化句式 =====
FORMULA_PATTERNS = [
    # 排比：三个相同结构的短句
    (re.compile(r'([^\n，。！？]{4,12})，\1{2,}'), r'\1'),
    # "首先...其次...最后"
    (re.compile(r'首先[，,].*?其次[，,].*?最后[，,]', re.DOTALL), ''),
    # "不仅...而且..." 过度使用
    (re.compile(r'不仅[，,].*?而且[，,]', re.DOTALL), ''),
]

# ===== C门：情绪标签→动作 =====
EMOTION_MAP = [
    (re.compile(r'他(感到|觉得)愤怒'), '他一拳砸在桌上'),
    (re.compile(r'他(感到|觉得)恐惧'), '他后退了一步'),
    (re.compile(r'他(感到|觉得)惊讶'), '他张大了嘴'),
    (re.compile(r'他(感到|觉得)悲伤'), '他低着头'),
    (re.compile(r'他(感到|觉得)高兴'), '他嘴角咧开'),
    (re.compile(r'他(感到|觉得)紧张'), '他手心冒汗'),
    (re.compile(r'她(感到|觉得)愤怒'), '她一巴掌甩过去'),
    (re.compile(r'她(感到|觉得)恐惧'), '她抱紧了胳膊'),
    (re.compile(r'她(感到|觉得)悲伤'), '她别过头去'),
]

# ===== E门：对话标签 =====
DIALOGUE_TAGS = [
    (re.compile(r'他(平静地|淡淡地|冷冷地|缓缓地|缓缓地)说'), '他说'),
    (re.compile(r'他(平静地|淡淡地|冷冷地|缓缓地)道'), '他道'),
    (re.compile(r'她(平静地|淡淡地|冷冷地|缓缓地)说'), '她说'),
    (re.compile(r'他笑了笑说'), '他说'),
    (re.compile(r'他叹了口气说'), '他说'),
]

# ===== F门：总结/升华结尾 =====
SUMMARY_ENDINGS = [
    re.compile(r'综上所述[，,].*$', re.DOTALL),
    re.compile(r'这一切(都|都将).*$', re.DOTALL),
    re.compile(r'命运的齿轮.*$', re.DOTALL),
]


def deslop(draft: str) -> str:
    """7道门依次过"""
    # A门：禁用词
    for pat, repl in BAN_WORDS:
        draft = pat.sub(repl, draft)
    
    # B门：公式句式
    for pat, repl in FORMULA_PATTERNS:
        draft = pat.sub(repl, draft)
    
    # C门：情绪标签→动作
    for pat, repl in EMOTION_MAP:
        draft = pat.sub(repl, draft)
    
    # E门：对话标签
    for pat, repl in DIALOGUE_TAGS:
        draft = pat.sub(repl, draft)
    
    # F门：删总结结尾（只删最后一段）
    lines = draft.split('\n')
    if lines:
        last = lines[-1]
        for pat in SUMMARY_ENDINGS:
            if pat.search(last):
                lines.pop()
                break
        draft = '\n'.join(lines)
    
    # G门：删全知叙述者插入（"话说""众所周知""众所周知"）
    draft = re.sub(r'话说[，,].*?。', '', draft)
    draft = re.sub(r'众所周知[，,].*?。', '', draft)
    
    # 清理多余空行
    draft = re.sub(r'\n{3,}', '\n\n', draft)
    
    return draft.strip()


def ai_score(draft: str) -> dict:
    """6个量化指标评分，返回0-100分，越低越像AI"""
    score = 100
    
    # 1. 禁用词密度
    ban_count = 0
    for pat, _ in BAN_WORDS:
        ban_count += len(pat.findall(draft))
    if ban_count > 5:
        score -= 20
    elif ban_count > 2:
        score -= 10
    
    # 2. 连续排比（三句以上相同结构）
    lines = [l.strip() for l in draft.split('\n') if l.strip()]
    parallel = 0
    for i in range(len(lines)-2):
        if len(lines[i]) == len(lines[i+1]) == len(lines[i+2]) and len(lines[i]) < 15:
            parallel += 1
    if parallel > 2:
        score -= 15
    
    # 3. 心理描写比例
    psychology = len(re.findall(r'他(感到|觉得|知道|明白|意识到)', draft))
    if psychology > 5:
        score -= 15
    
    # 4. 对话标签密度
    tags = len(re.findall(r'他(平静地|淡淡地|冷冷地|缓缓地)说', draft))
    if tags > 3:
        score -= 10
    
    # 5. 每段平均句数
    avg_sentences = len(re.findall(r'[。！？]', draft)) / max(len(lines), 1)
    if avg_sentences > 4:
        score -= 10
    
    # 6. 重复描写密度
    repeats = len(re.findall(r'(他停了一下|他愣了一下|他顿了一下)', draft))
    if repeats > 0:
        score -= 20
    
    return {
        "score": max(score, 0),
        "ban_count": ban_count,
        "parallel": parallel,
        "psychology": psychology,
    }
