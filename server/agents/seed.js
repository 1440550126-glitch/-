// 灵阵 · 种子数据：开机幂等载入内置智能体 / 团队模板 / 示例知识库
import { q, tx, db } from '../lib/db.js';
import { now } from '../lib/util.js';
import { addDoc } from './knowledge.js';
import { AGENT_TEMPLATES, TEAM_TEMPLATES, SAMPLE_KB } from './catalog.js';

// 轻量迁移：给较早创建的库补齐新列（schema.sql 的 CREATE IF NOT EXISTS 不会改动已存在的表）
export function runAgentMigrations() {
  for (const sql of [
    "ALTER TABLE agent_runs ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'"
  ]) { try { db.exec(sql); } catch { /* 列已存在，忽略 */ } }
}

export function seedLingArray() {
  const has = q.get('SELECT COUNT(*) c FROM agents WHERE is_template = 1 AND owner_id = 0')?.c || 0;
  if (has) return;
  tx(() => {
    // 示例知识库
    const kb = q.run('INSERT INTO knowledge_bases (owner_id, name, description, is_template, created_at, updated_at) VALUES (0,?,?,1,?,?)',
      SAMPLE_KB.name, SAMPLE_KB.description, now(), now());
    const kbId = Number(kb.lastInsertRowid);
    for (const d of SAMPLE_KB.docs) addDoc(kbId, d.source, d.text);
    const kbMap = { [SAMPLE_KB.key]: kbId };

    // 智能体模板
    const aMap = {};
    for (const t of AGENT_TEMPLATES) {
      const r = q.run(
        `INSERT INTO agents (owner_id, name, avatar, role, persona, tier, tools, temperature, is_template, enabled, created_at, updated_at)
         VALUES (0,?,?,?,?,?,?,?,1,1,?,?)`,
        t.name, t.avatar, t.role, t.persona, t.tier, JSON.stringify(t.tools), t.temperature, now(), now()
      );
      aMap[t.key] = Number(r.lastInsertRowid);
    }

    // 团队模板
    for (const tm of TEAM_TEMPLATES) {
      const memberIds = tm.members.map((k) => aMap[k]).filter(Boolean);
      const kbIds = (tm.knowledge || []).map((k) => kbMap[k]).filter(Boolean);
      q.run(
        `INSERT INTO teams (owner_id, name, avatar, goal, strategy, manager_note, member_ids, knowledge_ids, max_rounds, is_template, published, created_at, updated_at)
         VALUES (0,?,?,?,?,?,?,?,3,1,1,?,?)`,
        tm.name, tm.avatar, tm.goal, tm.strategy, tm.manager_note, JSON.stringify(memberIds), JSON.stringify(kbIds), now(), now()
      );
    }
  });
  console.log('  🛰  灵阵：已载入内置智能体 / 团队 / 知识库模板');
}
