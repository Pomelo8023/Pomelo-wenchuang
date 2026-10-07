# -*- coding: utf-8 -*-
"""灵云文创 · Truth File 结构化真相档案"""
"""借鉴 InkOS：人物矩阵 / 资源台账 / 待回收伏笔 / 情绪曲线"""
import json
from pathlib import Path
from datetime import datetime


class TruthFile:
    def __init__(self, project_dir: str | Path):
        self.dir = Path(project_dir) / "story" / "state"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _load(self, name: str) -> dict:
        f = self.dir / f"{name}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        return {}

    def _save(self, name: str, data: dict):
        f = self.dir / f"{name}.json"
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ===== Character Matrix 人物矩阵 =====
    def get_characters(self) -> dict:
        return self._load("characters")

    def upsert_character(self, cid: str, data: dict):
        chars = self.get_characters()
        chars[cid] = {**chars.get(cid, {}), **data, "updated": datetime.now().isoformat()}
        self._save("characters", chars)

    def get_character(self, cid: str) -> dict:
        return self.get_characters().get(cid, {})

    # ===== Resource Ledger 资源台账 =====
    def get_resources(self) -> dict:
        return self._load("resources")

    def update_resource(self, rid: str, delta: dict):
        resources = self.get_resources()
        if rid not in resources:
            resources[rid] = {"history": []}
        resources[rid].update(delta)
        resources[rid]["history"].append({"ts": datetime.now().isoformat(), **delta})
        self._save("resources", resources)

    # ===== Pending Hooks 待回收伏笔 =====
    def get_hooks(self) -> dict:
        return self._load("hooks")

    def add_hook(self, hid: str, data: dict):
        hooks = self.get_hooks()
        hooks[hid] = {**data, "status": "active", "created": datetime.now().isoformat()}
        self._save("hooks", hooks)

    def resolve_hook(self, hid: str, resolve_chapter: int, resolve_summary: str):
        hooks = self.get_hooks()
        if hid in hooks:
            hooks[hid]["status"] = "resolved"
            hooks[hid]["resolve_chapter"] = resolve_chapter
            hooks[hid]["resolve_summary"] = resolve_summary
            self._save("hooks", hooks)

    def get_active_hooks(self) -> dict:
        return {k: v for k, v in self.get_hooks().items() if v.get("status") == "active"}

    # ===== Emotional Arc 情绪曲线 =====
    def get_emotional_arc(self) -> list:
        return self._load("emotional_arc").get("chapters", [])

    def add_emotional_chapter(self, chapter: int, emotion: str, intensity: int, climax: bool):
        arc = self._load("emotional_arc")
        if "chapters" not in arc:
            arc["chapters"] = []
        arc["chapters"].append({
            "chapter": chapter,
            "emotion": emotion,
            "intensity": intensity,  # 1-10
            "climax": climax,
            "ts": datetime.now().isoformat(),
        })
        self._save("emotional_arc", arc)

    def get_climax_history(self) -> list:
        return [c for c in self.get_emotional_arc() if c.get("climax")]

    # ===== Observer 反思存档 =====
    def add_reflection(self, chapter: int, reflection: dict):
        data = self._load("reflections")
        if "chapters" not in data:
            data["chapters"] = []
        data["chapters"].append({"chapter": chapter, **reflection, "ts": datetime.now().isoformat()})
        self._save("reflections", data)

    def get_last_reflection(self) -> dict:
        chs = self._load("reflections").get("chapters", [])
        return chs[-1] if chs else {}

    # ===== Resource Ledger 资源台账（钱/法宝/能力变化） =====
    def get_resource_history(self, rid: str) -> list:
        return self.get_resources().get(rid, {}).get("history", [])

    # ===== Canon 设定正典（不可变事实） =====
    def get_canon(self) -> dict:
        return self._load("canon")

    def set_canon(self, data: dict):
        self._save("canon", data)

    # ===== 导出 markdown 供人类阅读 =====
    def export_markdown(self) -> str:
        chars = self.get_characters()
        hooks = self.get_hooks()
        resources = self.get_resources()
        arc = self.get_emotional_arc()

        md = ["# 故事真相档案\n"]
        md.append("## 人物矩阵\n")
        for cid, c in chars.items():
            md.append(f"- **{c.get('name', cid)}** ({c.get('role', 'support')})：{c.get('state', '')}\n")
        md.append("\n## 待回收伏笔\n")
        for hid, h in hooks.items():
            status = "✅" if h.get("status") == "resolved" else "⏳"
            md.append(f"- {status} 第{h.get('plant_chapter', '?')}章：{h.get('summary', '')}\n")
        md.append("\n## 情绪曲线\n")
        for c in arc[-10:]:
            md.append(f"- 第{c['chapter']}章：{c['emotion']}（强度{c['intensity']}）{'🔥高潮' if c.get('climax') else ''}\n")
        return "".join(md)
