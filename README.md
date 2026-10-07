# Pomelo文创

AI 全自动网文生成引擎。FastAPI + 原生 HTML，单文件部署。

## 快速开始

```bash
cd backend
pip install fastapi uvicorn requests
python main.py
```

打开 http://127.0.0.1:8000

## 访问密码

默认密码：`pomelo2026`

改密码：编辑 `main.py` 里的 `ACCESS_TOKEN`。

## 手机访问

手机连同一个 WiFi，访问 `http://你的电脑IP:8000`（电脑IP用 `ipconfig` 查）。

第一次会跳登录页，输密码后自动记住。

## Agnes API 配置

编辑 `api_keys.json`，填入你的 Agnes key：

```json
{
  "AGNES_KEYS": ["sk-xxx", "sk-yyy"]
}
```

3 个 key 自动轮换，熔断 10 分钟。

## 功能

- 38 个题材模板
- 黄金三章特化
- 对标书拆解
- 文风学习
- 封面生成（Agnes Image 免费）
- 市场雷达
- 导入已有小说
- 深度去AI味
- 深度审稿
- 对话改稿（流式）
- 5 道写入门
- L6 实体档案记忆
- FTS5 全文检索
- 伏笔老化预警
- 手机适配

## 技术栈

- 后端：FastAPI + SQLite
- 前端：单文件 HTML（无 build）
- LLM：Agnes 3.0 Flash（免费）
- 图片：Agnes Image 2.1 Flash（免费）
