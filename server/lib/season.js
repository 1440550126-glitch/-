// ============================================================
// 句灵 · 凶夜赛季通行证（Season Pass）
// ------------------------------------------------------------
// 「收益在多人游戏里」的合规落地：玩多人对局攒「凶夜印记」→ 升级 →
// 解锁纯外观奖励（卡框/头像框/气泡/房间主题）。免费档人人可拿，
// 高级档一次性解锁全套高级外观。公平铁律：奖励全为外观，绝不影响玩法。
// ============================================================
import { q } from './db.js';
import { now, dayCN, jparse } from './util.js';

export const SEASON = {
  id: 'jvling-s1',
  name: '凶夜·初雪赛季',
  maxLevel: 10,
  pointsPerLevel: 100,        // 每级所需印记
  premiumPriceFen: 1490,      // 高级通行证 ¥14.9
  perGame: 50,                // 每完成一局多人对局
  firstGameBonus: 70,         // 当日首局额外奖励
  dailyCap: 300,              // 每日印记上限（防刷）
  endsAt: Date.parse('2026-09-01T00:00:00+08:00')
};

// 奖励轨道：免费档（人人可领）+ 高级档（解锁通行证后可领）。全部映射到皮肤 id（纯外观）
const REWARDS = {
  1: { free: 'cf_sakura', premium: 'cf_frost' },
  2: { free: null, premium: 'bb_whisper' },
  3: { free: 'bb_cloud', premium: 'af_phantom' },
  4: { free: null, premium: 'cf_cloud' },
  5: { free: 'af_catears', premium: 'bb_peach' },
  6: { free: null, premium: 'af_meteor' },
  7: { free: 'cf_soda', premium: 'cf_galaxy' },
  8: { free: null, premium: 'fx_firefly' },
  9: { free: 'rt_cafe', premium: 'rt_bookshop' },
  10: { free: null, premium: 'rt_manor' }
};

export const levelOf = (points) => Math.max(0, Math.min(SEASON.maxLevel, Math.floor((points || 0) / SEASON.pointsPerLevel)));

function rowFor(userId) {
  return q.get('SELECT * FROM user_season WHERE user_id = ? AND season_id = ?', userId, SEASON.id)
    || { user_id: userId, season_id: SEASON.id, points: 0, premium: 0, claimed: '[]' };
}

/** 完成一局多人对局 → 发放印记（当日首局有加成，含每日上限防刷） */
export function awardSeasonPoints(userId) {
  if (!userId || userId <= 0) return 0;
  const today = dayCN();
  const used = q.get('SELECT used FROM quota_usage WHERE user_id = ? AND day = ? AND kind = ?', userId, today, 'season_pts')?.used || 0;
  if (used >= SEASON.dailyCap) return 0;
  let amount = SEASON.perGame + (used === 0 ? SEASON.firstGameBonus : 0);
  amount = Math.min(amount, SEASON.dailyCap - used);
  q.run(
    `INSERT INTO quota_usage (user_id, day, kind, used) VALUES (?,?,?,?)
     ON CONFLICT(user_id, day, kind) DO UPDATE SET used = used + ?`,
    userId, today, 'season_pts', amount, amount
  );
  q.run(
    `INSERT INTO user_season (user_id, season_id, points, premium, claimed, created_at) VALUES (?,?,?,0,'[]',?)
     ON CONFLICT(user_id, season_id) DO UPDATE SET points = points + ?`,
    userId, SEASON.id, amount, now(), amount
  );
  return amount;
}

export const premiumOwned = (userId) => rowFor(userId).premium === 1;

export function grantPremium(userId) {
  q.run(
    `INSERT INTO user_season (user_id, season_id, points, premium, claimed, created_at) VALUES (?,?,0,1,'[]',?)
     ON CONFLICT(user_id, season_id) DO UPDATE SET premium = 1`,
    userId, SEASON.id, now()
  );
}

function skinView(id) {
  if (!id) return null;
  const s = q.get('SELECT id, name, type, rarity, payload FROM skins WHERE id = ?', id);
  return s ? { ...s, payload: jparse(s.payload, {}) } : { id, name: id, type: 'unknown', rarity: 'normal', payload: {} };
}

/** 我的赛季全貌：进度 + 奖励轨道（含领取/解锁状态） */
export function seasonStateFor(userId) {
  const row = rowFor(userId);
  const points = row.points || 0;
  const level = levelOf(points);
  const claimed = new Set(jparse(row.claimed, []));
  const premium = row.premium === 1;
  const today = dayCN();
  const todayPts = q.get('SELECT used FROM quota_usage WHERE user_id = ? AND day = ? AND kind = ?', userId, today, 'season_pts')?.used || 0;

  const track = [];
  for (let lv = 1; lv <= SEASON.maxLevel; lv++) {
    const r = REWARDS[lv] || {};
    track.push({
      level: lv,
      points_at: lv * SEASON.pointsPerLevel,
      reached: level >= lv,
      free: skinView(r.free),
      premium: skinView(r.premium),
      free_claimed: claimed.has(`free:${lv}`),
      premium_claimed: claimed.has(`premium:${lv}`)
    });
  }
  return {
    season: { id: SEASON.id, name: SEASON.name, max_level: SEASON.maxLevel, points_per_level: SEASON.pointsPerLevel, premium_price_fen: SEASON.premiumPriceFen, ends_at: SEASON.endsAt },
    progress: {
      points, level, premium,
      next_level_at: level < SEASON.maxLevel ? (level + 1) * SEASON.pointsPerLevel : null,
      today_points: todayPts, daily_cap: SEASON.dailyCap, per_game: SEASON.perGame, first_game_bonus: SEASON.firstGameBonus
    },
    track
  };
}

/** 领取某级奖励（免费/高级档）→ 发放皮肤到 user_skins */
export function claimReward(userId, level, track) {
  const lv = Number(level);
  if (!REWARDS[lv]) return { ok: false, error: '奖励等级不存在' };
  if (track !== 'free' && track !== 'premium') return { ok: false, error: '轨道无效' };
  const row = rowFor(userId);
  if (levelOf(row.points) < lv) return { ok: false, error: `还没达到 ${lv} 级，多玩几局攒印记吧～` };
  if (track === 'premium' && row.premium !== 1) return { ok: false, error: '需要先解锁高级通行证', need_premium: true };
  const skinId = REWARDS[lv][track];
  if (!skinId) return { ok: false, error: '该档位本级没有奖励' };
  const claimed = jparse(row.claimed, []);
  const key = `${track}:${lv}`;
  if (claimed.includes(key)) return { ok: false, error: '这个奖励已经领过啦' };
  claimed.push(key);
  q.run('INSERT OR IGNORE INTO user_skins (user_id, skin_id, created_at) VALUES (?,?,?)', userId, skinId, now());
  q.run(
    `INSERT INTO user_season (user_id, season_id, points, premium, claimed, created_at) VALUES (?,?,?,?,?,?)
     ON CONFLICT(user_id, season_id) DO UPDATE SET claimed = ?`,
    userId, SEASON.id, row.points || 0, row.premium || 0, JSON.stringify(claimed), now(), JSON.stringify(claimed)
  );
  return { ok: true, skin: skinView(skinId) };
}
