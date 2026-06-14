// 灵阵 · 种子数据：开机幂等载入内置智能体 / 团队模板 / 示例知识库
import { q, tx, db } from '../lib/db.js';
import { now } from '../lib/util.js';
import { addDoc } from './knowledge.js';
import { AGENT_TEMPLATES, TEAM_TEMPLATES, SAMPLE_KB } from './catalog.js';

// 轻量迁移：给较早创建的库补齐新列（schema.sql 的 CREATE IF NOT EXISTS 不会改动已存在的表）
export function runAgentMigrations() {
  for (const sql of [
    "ALTER TABLE agent_runs ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'",
    'ALTER TABLE teams ADD COLUMN api_key TEXT'
  ]) { try { db.exec(sql); } catch { /* 列已存在，忽略 */ } }
}

// 增量幂等：按名字补齐缺失的内置模板（这样后续新增的模板在老库里也会自动出现）
export function seedLingArray() {
  let added = 0;
  tx(() => {
    // 示例知识库
    let kbId = q.get('SELECT id FROM knowledge_bases WHERE is_template = 1 AND owner_id = 0 AND name = ?', SAMPLE_KB.name)?.id;
    if (!kbId) {
      const kb = q.run('INSERT INTO knowledge_bases (owner_id, name, description, is_template, created_at, updated_at) VALUES (0,?,?,1,?,?)',
        SAMPLE_KB.name, SAMPLE_KB.description, now(), now());
      kbId = Number(kb.lastInsertRowid);
      for (const d of SAMPLE_KB.docs) addDoc(kbId, d.source, d.text);
      added++;
    }
    const kbMap = { [SAMPLE_KB.key]: kbId };

    // 智能体模板（按名字补齐）
    const aMap = {};
    for (const t of AGENT_TEMPLATES) {
      let id = q.get('SELECT id FROM agents WHERE is_template = 1 AND owner_id = 0 AND name = ?', t.name)?.id;
      if (!id) {
        const r = q.run(
          `INSERT INTO agents (owner_id, name, avatar, role, persona, tier, tools, temperature, is_template, enabled, created_at, updated_at)
           VALUES (0,?,?,?,?,?,?,?,1,1,?,?)`,
          t.name, t.avatar, t.role, t.persona, t.tier, JSON.stringify(t.tools), t.temperature, now(), now()
        );
        id = Number(r.lastInsertRowid); added++;
      }
      aMap[t.key] = id;
    }

    // 团队模板（按名字补齐）
    for (const tm of TEAM_TEMPLATES) {
      if (q.get('SELECT id FROM teams WHERE is_template = 1 AND owner_id = 0 AND name = ?', tm.name)) continue;
      const memberIds = tm.members.map((k) => aMap[k]).filter(Boolean);
      const kbIds = (tm.knowledge || []).map((k) => kbMap[k]).filter(Boolean);
      q.run(
        `INSERT INTO teams (owner_id, name, avatar, goal, strategy, manager_note, member_ids, knowledge_ids, max_rounds, is_template, published, created_at, updated_at)
         VALUES (0,?,?,?,?,?,?,?,3,1,1,?,?)`,
        tm.name, tm.avatar, tm.goal, tm.strategy, tm.manager_note, JSON.stringify(memberIds), JSON.stringify(kbIds), now(), now()
      );
      added++;
    }
  });
  if (added) console.log(`  🛰  灵阵：已载入/补齐内置模板（新增 ${added} 项）`);
}
