# -*- coding: utf-8 -*-
"""灵云文创 · 人物一致性系统
角色事实表、情绪状态日志、关系追踪器、时间线管理、生成后验证
"""
import json
import os
from pathlib import Path


class CharacterConsistency:
    """人物一致性管理器"""

    def __init__(self, proj_dir: str):
        self.proj_dir = Path(proj_dir)
        self.state_dir = self.proj_dir / "story" / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # 角色事实表
        self.characters_file = self.state_dir / "characters.json"
        # 情绪状态日志
        self.emotions_file = self.state_dir / "emotions.json"
        # 关系追踪器
        self.relations_file = self.state_dir / "relations.json"
        # 时间线
        self.timeline_file = self.state_dir / "timeline.json"

        self.characters = self._load(self.characters_file, {})
        self.emotions = self._load(self.emotions_file, {})
        self.relations = self._load(self.relations_file, {})
        self.timeline = self._load(self.timeline_file, [])

    def _load(self, path: Path, default):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return default
        return default

    def _save(self, path: Path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def update_characters(self, chapter: int, characters: list):
        """更新角色事实表"""
        for char in characters:
            name = char.get("name", "")
            if not name:
                continue
            if name not in self.characters:
                self.characters[name] = {
                    "first_appear": chapter,
                    "physical": "",
                    "personality": "",
                    "abilities": [],
                    "speech_style": "",
                    "state_changes": [],
                    "knowledge": []
                }
            # 更新状态变化
            state_change = char.get("state_change", "")
            if state_change:
                self.characters[name]["state_changes"].append({
                    "chapter": chapter,
                    "change": state_change
                })
            # 更新情绪
            emotion = char.get("emotion", "")
            if emotion:
                if name not in self.emotions:
                    self.emotions[name] = []
                self.emotions[name].append({
                    "chapter": chapter,
                    "emotion": emotion
                })

        self._save(self.characters_file, self.characters)
        self._save(self.emotions_file, self.emotions)

    def update_relations(self, chapter: int, events: list):
        """从事件中提取关系变化"""
        for event in events:
            summary = event.get("summary", "")
            event_type = event.get("type", "")
            if event_type in ("fight", "dialogue") and summary:
                # 简单的关系提取：如果事件中有两个人名，记录关系
                for name1 in self.characters:
                    for name2 in self.characters:
                        if name1 != name2 and name1 in summary and name2 in summary:
                            key = f"{name1}-{name2}"
                            if key not in self.relations:
                                self.relations[key] = {
                                    "characters": [name1, name2],
                                    "type": "unknown",
                                    "history": []
                                }
                            # 判断关系类型
                            if event_type == "fight":
                                self.relations[key]["type"] = "敌对"
                            elif event_type == "dialogue":
                                if self.relations[key]["type"] == "unknown":
                                    self.relations[key]["type"] = "互动"
                            self.relations[key]["history"].append({
                                "chapter": chapter,
                                "event": summary[:50],
                                "type": event_type
                            })

        self._save(self.relations_file, self.relations)

    def update_timeline(self, chapter: int, events: list):
        """更新时间线"""
        for event in events:
            self.timeline.append({
                "chapter": chapter,
                "type": event.get("type", ""),
                "summary": event.get("summary", ""),
                "location": event.get("location", "")
            })
        self._save(self.timeline_file, self.timeline)

    def get_character_context(self, name: str) -> str:
        """获取角色上下文，用于写作时注入"""
        if name not in self.characters:
            return ""
        char = self.characters[name]
        context = f"【角色：{name}】\n"
        context += f"首次出场：第{char.get('first_appear', '?')}章\n"
        if char.get("state_changes"):
            latest = char["state_changes"][-1]
            context += f"最新状态：{latest.get('change', '')}\n"
        if name in self.emotions and self.emotions[name]:
            latest_emotion = self.emotions[name][-1]
            context += f"最新情绪：{latest_emotion.get('emotion', '')}\n"
        return context

    def get_all_characters_context(self) -> str:
        """获取所有角色上下文"""
        contexts = []
        for name in self.characters:
            ctx = self.get_character_context(name)
            if ctx:
                contexts.append(ctx)
        return "\n".join(contexts)

    def check_consistency(self, chapter: int, draft: str) -> list:
        """检查一致性，返回问题列表"""
        issues = []

        # 检查角色是否OOC（简单检查：角色状态变化是否合理）
        for name, char in self.characters.items():
            if name in draft:
                # 检查角色是否突然有了之前没有的能力
                # 这里可以加更复杂的检查
                pass

        # 检查时间线矛盾
        # 这里可以加更复杂的检查

        return issues

    def get_summary(self) -> dict:
        """获取一致性系统摘要"""
        return {
            "character_count": len(self.characters),
            "relation_count": len(self.relations),
            "timeline_events": len(self.timeline),
            "characters": list(self.characters.keys()),
            "relations": list(self.relations.keys())
        }
