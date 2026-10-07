# -*- coding: utf-8 -*-
"""灵云文创 · Humanizer（规则版+语义清理+匿名化，不调 LLM，零耗时）"""
import re

_BANNED_ADVERBS = ["缓缓地", "缓缓", "淡淡地", "淡淡", "微微地", "微微",
                   "轻轻地", "轻轻", "默默地", "默默", "静静地", "静静"]
_BANNED_TAILS = ["他终于明白", "从那以后", "这一刻他才知道", "他深吸一口气"]
# 匿名化：真实地名/政治引用改成虚构
_ANON_MAP = {
    "北京": "北原市",
    "上海": "东海市",
    "广州": "南州市",
    "深圳": "深圳市",  # 深圳可以保留
    "中国": "华夏国",
    "美国": "鹰国",
    "日本": "倭国",
    "俄罗斯": "北极熊国",
    "政府": "官方",
    "党": "势力",
    "警察": "巡捕",
    "派出所": "巡捕房",
}


def anonymize(draft: str) -> str:
    """匿名化：把真实地名/政治引用改成虚构"""
    for real, fake in _ANON_MAP.items():
        draft = draft.replace(real, fake)
    return draft


# 语义层面删除（InkOS deslop）
_EMPTY_CONCLUSIONS = [
    r"这让他意识到[^\n]*",
    r"他终于明白[^\n]*",
    r"这一刻他才知道[^\n]*",
    r"他深知[^\n]*",
    r"他清楚地知道[^\n]*",
    r"这意味着[^\n]*",
    r"显然[，,][^\n]*",
    r"毫无疑问[，,][^\n]*",
]
_GENERIC_TRANSITIONS = [
    r"与此同时[，,]",
    r"就在这时[，,]",
    r"话说回来[，,]",
    r"时间过得很快[，,]?[^\n]*",
    r"转眼间[，,]?[^\n]*",
]
_SYMMETRIC_PHRASES = [
    r"一方面[^\n]*另一方面[^\n]*",
    r"不仅如此[，,]?[^\n]*",
    r"与此同时[，,]?[^\n]*",
]

# 删形容词（AI爱用）
_BANNED_ADJECTIVES = ["心情沉重地", "心情复杂地", "若有所思地", "意味深长地",
                      "不动声色地", "下意识地", "不由自主地", "情不自禁地"]

# 书面语换口语
_FORMAL_TO_COLLOQUIAL = {
    "感到一阵强烈的饥饿感袭来": "他饿了",
    "感到一丝不安": "他有点慌",
    "嘴角微微上扬": "他笑了",
    "眼中闪过一丝不易察觉的光芒": "他眼睛亮了",
    "深吸一口气": "他吸了口气",
    "缓缓睁开双眼": "他睁开眼",
    "淡淡的说道": "他说",
    "冷冷的开口": "他说",
}


def humanize(draft: str) -> str:
    """规则去 AI 味：零 LLM 调用，毫秒级"""
    # 1. 删除禁用副词
    for adv in _BANNED_ADVERBS:
        draft = draft.replace(adv, "")
    # 2. 删除禁用尾巴
    for tail in _BANNED_TAILS:
        draft = draft.replace(tail, "")
    # 3. 语义层面：删除空泛结论
    for pattern in _EMPTY_CONCLUSIONS:
        draft = re.sub(pattern, "", draft)
    # 4. 语义层面：删除通用过渡
    for pattern in _GENERIC_TRANSITIONS:
        draft = re.sub(pattern, "", draft)
    # 5. 语义层面：删除对称套话
    for pattern in _SYMMETRIC_PHRASES:
        draft = re.sub(pattern, "", draft)
    # 6. 删形容词
    for adj in _BANNED_ADJECTIVES:
        draft = draft.replace(adj, "")
    # 7. 书面语换口语
    for formal, colloquial in _FORMAL_TO_COLLOQUIAL.items():
        draft = draft.replace(formal, colloquial)
    # 8. 多余空行压成一行
    draft = re.sub(r"\n{3,}", "\n\n", draft)
    # 9. 删除连续两个句号
    draft = re.sub(r"。。+", "。", draft)
    # 10. 句子长度变化：把太长的句子拆开
    sentences = re.split(r'([。！？])', draft)
    new_sentences = []
    for i in range(0, len(sentences)-1, 2):
        s = sentences[i] + sentences[i+1]
        if len(s) > 80:  # 太长的句子拆开
            mid = len(s) // 2
            # 找中间的逗号
            comma_pos = s.find('，', mid-20, mid+20)
            if comma_pos > 0:
                s = s[:comma_pos+1] + '。\n' + s[comma_pos+1:]
        new_sentences.append(s)
    draft = ''.join(new_sentences)
    # 11. 段落长度变化：如果连续3段都差不多长，把中间那段拆短
    paragraphs = draft.split('\n\n')
    for i in range(2, len(paragraphs)):
        if abs(len(paragraphs[i]) - len(paragraphs[i-1])) < 20 and abs(len(paragraphs[i-1]) - len(paragraphs[i-2])) < 20:
            # 三段差不多长，把中间那段加个短句子
            paragraphs[i-1] = paragraphs[i-1] + '\n\n他停了一下。'
    draft = '\n\n'.join(paragraphs)
    # 12. 匿名化：真实地名/政治引用改成虚构
    draft = anonymize(draft)
    return draft.strip()
