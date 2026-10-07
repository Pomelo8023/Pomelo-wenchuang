"""快速检查项目健康状况"""
import sqlite3, re, sys, json, os, requests
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://127.0.0.1:8000'
PROJ = '2'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'projects', PROJ, 'story.db')
CANON = os.path.join(ROOT, 'projects', PROJ, 'story', 'state', 'canon.json')

issues = []

print("=" * 50)
print("快速健康检查")
print("=" * 50)

# 1. 后端健康
try:
    r = requests.get(f'{BASE}/api/health', timeout=3)
    print(f"[1] 后端: {r.json().get('status')} ✓")
except Exception as e:
    issues.append(f"后端无响应: {e}")
    print(f"[1] 后端: ✗ {e}")

# 2. 数据库
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# 章节数
cnt = conn.execute('SELECT COUNT(*) c FROM chapters').fetchone()['c']
p = conn.execute('SELECT * FROM progress').fetchone()
print(f"[2] 进度: 第{p['current_chapter']}章 / 共{p['total_chapters']}章 (状态: {p['status']})")

# 人物数
cnt = conn.execute('SELECT COUNT(*) c FROM entities').fetchone()['c']
print(f"[3] 人物: {cnt} 个")

# 伏笔数
rows = conn.execute('SELECT status, COUNT(*) c FROM foreshadow_contracts GROUP BY status').fetchall()
fs = {r['status']: r['c'] for r in rows}
print(f"[4] 伏笔: 未回收{fs.get('active',0)} / 已回收{fs.get('resolved',0)}")

# 事件数
cnt = conn.execute('SELECT COUNT(*) c FROM events').fetchone()['c']
print(f"[5] 事件: {cnt} 条")

# canon.json
with open(CANON, 'r', encoding='utf-8') as f:
    canon = json.load(f)
print(f"[6] 书名: {canon.get('title', '?')}")
print(f"[7] 总章数: {canon.get('total_ch_min','?')}-{canon.get('total_ch_max','?')}")
print(f"[8] 每章字数: {canon.get('words_min','?')}-{canon.get('words_max','?')}")

# API 接口
apis = ['progress', 'chapters', 'characters', 'foreshadows', 'events', 'settings']
ok_count = 0
for api in apis:
    try:
        r = requests.get(f'{BASE}/api/projects/{PROJ}/{api}', timeout=3)
        if r.status_code == 200: ok_count += 1
    except: pass
print(f"[9] API 接口: {ok_count}/{len(apis)} 正常")

conn.close()

# 汇总
print("=" * 50)
if issues:
    print(f"发现 {len(issues)} 个问题:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
else:
    print("一切正常 ✓")
print("=" * 50)
