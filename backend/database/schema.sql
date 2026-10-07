-- 灵云文创 · 数据库 Schema（产品级）
-- 8 张核心表 + 2 张关系表

-- 项目元信息
CREATE TABLE IF NOT EXISTS project_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- 进度追踪
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_chapter INTEGER DEFAULT 0,
    total_chapters INTEGER DEFAULT 100,
    status TEXT DEFAULT 'idle',
    current_step TEXT DEFAULT '',
    retry_count INTEGER DEFAULT 0,
    last_error TEXT DEFAULT ''
);

-- 章节
CREATE TABLE IF NOT EXISTS chapters (
    chapter INTEGER PRIMARY KEY,
    title TEXT,
    content TEXT,
    summary TEXT,
    word_count INTEGER,
    review_score REAL,
    commit_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 人物（实体）
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    aliases TEXT DEFAULT '[]',
    role_type TEXT DEFAULT 'support',  -- protagonist/antagonist/support
    realm TEXT DEFAULT '',
    personality TEXT DEFAULT '',
    abilities TEXT DEFAULT '[]',
    state TEXT DEFAULT '',
    arc_state TEXT DEFAULT 'starting',  -- starting/tension/approaching/climax/resolution
    first_chapter INTEGER DEFAULT 0,
    last_chapter INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    archetype TEXT DEFAULT 'npc'   -- family/warrior/sage/noble/creature/divine/demon/female/mysterious/faction/npc/protagonist/antagonist
);

-- 人物状态变化（每章记录）
CREATE TABLE IF NOT EXISTS state_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT,
    chapter INTEGER,
    change_type TEXT,  -- location/emotion/relationship/power
    old_value TEXT,
    new_value TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 人物关系
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity1_id TEXT,
    entity2_id TEXT,
    relation_type TEXT,  -- friend/enemy/lover/family
    strength INTEGER DEFAULT 0,  -- -100 到 100
    first_chapter INTEGER,
    last_chapter INTEGER
);

-- 伏笔契约
CREATE TABLE IF NOT EXISTS foreshadow_contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plant_chapter INTEGER NOT NULL,
    plant_summary TEXT NOT NULL,
    type TEXT DEFAULT '悬念',
    strength TEXT DEFAULT 'medium',
    lifecycle TEXT DEFAULT 'near-term',  -- immediate/near-term/mid-arc/slow-burn/endgame
    resolve_chapter INTEGER,
    resolve_summary TEXT,
    status TEXT DEFAULT 'active',  -- active/resolved/overdue/superseded
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 事件（每章的关键事件）
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter INTEGER NOT NULL,
    event_type TEXT,  -- plot/climax/transition
    summary TEXT,
    importance INTEGER DEFAULT 5  -- 1-10
);

-- 日志
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter INTEGER,
    stage TEXT,
    status TEXT DEFAULT 'info',
    latency_ms INTEGER,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_state_changes_entity ON state_changes(entity_id);
CREATE INDEX IF NOT EXISTS idx_state_changes_chapter ON state_changes(chapter);
CREATE INDEX IF NOT EXISTS idx_relationships ON relationships(entity1_id, entity2_id);
CREATE INDEX IF NOT EXISTS idx_foreshadows_status ON foreshadow_contracts(status);
CREATE INDEX IF NOT EXISTS idx_events_chapter ON events(chapter);
CREATE INDEX IF NOT EXISTS idx_logs_chapter ON logs(chapter);
