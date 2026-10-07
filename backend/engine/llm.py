# -*- coding: utf-8 -*-
"""灵云文创 · LLM 客户端（Agnes 3.0 Flash 为主，多服务商容灾 + 熔断）"""
import json
import time
import threading
from pathlib import Path

import requests

KEYS_FILE = Path(__file__).parent.parent / "api_keys.json"

# ===== 全局 RPM 限流（Agnes 免费版 10 RPM，留余量到 8 RPM） =====
_call_times: list[float] = []
_rate_lock = threading.Lock()
MIN_INTERVAL = 6.0

# ===== 已移除熔断：服务商自己有限流，本地不熔断 =====
FAIL_THRESHOLD = 999
COOLDOWN_SEC = 0


def _load_state():
    pass


def _save_state():
    pass


def _rate_limit():
    global _call_times
    with _rate_lock:
        now = time.time()
        _call_times = [t for t in _call_times if now - t < 60]
        if len(_call_times) >= 8:
            wait = 60 - (now - _call_times[0]) + 0.5
            time.sleep(wait)
            now = time.time()
            _call_times = [t for t in _call_times if now - t < 60]
        _call_times.append(now)


def _provider_ok(name: str) -> bool:
    """已移除熔断：永远返回True"""
    return True


def _record_success(name: str):
    pass


def _record_failure(name: str):
    pass


def _load_keys() -> dict:
    if KEYS_FILE.exists():
        return json.loads(KEYS_FILE.read_text(encoding="utf-8"))
    return {}


AGNES_BASE = "https://apihub.agnes-ai.com/v1"


def _build_providers(keys: dict) -> tuple[list, list]:
    # Agnes 多 key 轮换（每个 key 一个独立 provider，独立熔断）
    agnes_keys = keys.get("AGNES_KEYS") or ([keys["AGNES_KEY"]] if keys.get("AGNES_KEY") else [])
    agnes_writer = []
    for i, k in enumerate(agnes_keys):
        agnes_writer.append({"name": f"agnes-{i+1}", "base_url": AGNES_BASE,
                             "model": "agnes-3.0-flash", "key": k, "rpm_limited": True})
    writer = agnes_writer + [
        {"name": "zhipu", "base_url": "https://open.bigmodel.cn/api/paas/v4",
         "model": "glm-4-plus", "key": keys.get("ZHIPU_KEY", ""), "rpm_limited": False},
        {"name": "siliconflow", "base_url": "https://api.siliconflow.cn/v1",
         "model": "Qwen/Qwen2.5-72B-Instruct", "key": keys.get("SILICONFLOW_KEY", ""), "rpm_limited": False},
        {"name": "deepseek", "base_url": "https://api.deepseek.com/v1",
         "model": "deepseek-chat", "key": keys.get("DEEPSEEK_KEY", ""), "rpm_limited": False},
    ]
    fast = agnes_writer + [
        {"name": "zhipu-fast", "base_url": "https://open.bigmodel.cn/api/paas/v4",
         "model": "glm-4-flash", "key": keys.get("ZHIPU_KEY", ""), "rpm_limited": False},
    ]
    return writer, fast


def chat(messages: list, temperature: float = 0.85, max_tokens: int = 4000, fast: bool = False) -> str:
    """自动容灾：熔断 + 多 key 轮换 + 429 退避"""
    keys = _load_keys()
    writer_providers, fast_providers = _build_providers(keys)
    providers = fast_providers if fast else writer_providers
    errors = []

    for p in providers:
        if not p["key"]:
            continue
        if not _provider_ok(p["name"]):
            errors.append(f"{p['name']}: 冷却中")
            continue
        # 每个 provider 最多重试 2 次
        for attempt in range(2):
            try:
                if p.get("rpm_limited"):
                    _rate_limit()
                resp = requests.post(
                    f"{p['base_url']}/chat/completions",
                    headers={"Authorization": f"Bearer {p['key']}"},
                    json={"model": p["model"], "messages": messages,
                          "temperature": temperature, "max_tokens": max_tokens},
                    timeout=(10, 30),
                )
                if resp.status_code == 429:
                    time.sleep(8 * (attempt + 1))
                    continue
                if resp.status_code in (500, 502, 503, 504):
                    time.sleep(3)
                    continue
                resp.raise_for_status()
                _record_success(p["name"])
                return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                errors.append(f"{p['name']}: {str(e)[:80]}")
                time.sleep(2)
                continue
        _record_failure(p["name"])
    raise RuntimeError(f"所有服务商都失败: {'; '.join(errors) or '未配置 key'}")


def chat_stream(messages: list, temperature: float = 0.85, max_tokens: int = 4000,
                on_delta=None, fast: bool = False, stop_check=None) -> str:
    """流式版本：on_delta(str) 每收到一段文本回调一次，返回完整文本
    stop_check: callable, 返回True则立马中断"""
    keys = _load_keys()
    writer_providers, fast_providers = _build_providers(keys)
    providers = fast_providers if fast else writer_providers
    errors = []

    for p in providers:
        if not p["key"]:
            continue
        if not _provider_ok(p["name"]):
            errors.append(f"{p['name']}: 冷却中")
            continue
        try:
            if p.get("rpm_limited"):
                _rate_limit()
            resp = requests.post(
                f"{p['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {p['key']}"},
                json={"model": p["model"], "messages": messages,
                      "temperature": temperature, "max_tokens": max_tokens, "stream": True},
                timeout=(10, 30), stream=True,
            )
            if resp.status_code != 200:
                errors.append(f"{p['name']}: HTTP {resp.status_code}")
                _record_failure(p["name"])
                continue
            full = []
            last_recv = time.time()
            for line in resp.iter_lines():
                if not line:
                    continue
                # 立马暂停检查
                if stop_check and stop_check():
                    raise InterruptedError("用户暂停")
                # 读超时：60秒没收到数据就断开
                if time.time() - last_recv > 60:
                    raise Exception("流式读超时：60秒没收到数据")
                line = line.decode("utf-8")
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    break
                try:
                    delta = json.loads(data)["choices"][0]["delta"].get("content", "")
                except Exception:
                    continue
                if delta:
                    full.append(delta)
                    last_recv = time.time()
                    if on_delta:
                        on_delta(delta)
            _record_success(p["name"])
            return "".join(full)
        except Exception as e:
            errors.append(f"{p['name']}: {str(e)[:80]}")
            _record_failure(p["name"])
            continue
    raise RuntimeError(f"所有服务商都失败: {'; '.join(errors) or '未配置 key'}")
